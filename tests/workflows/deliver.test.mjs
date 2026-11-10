import { test } from 'node:test'
import assert from 'node:assert/strict'
import { run } from './harness.mjs'

const prep = { ok: true, reason: '', worktree: '/r/.claude/worktrees/x', branch: 'x', base: 'b0', default_branch: 'main' }
const done = { outcome: 'done', blocker: '', commits: ['c1 feat: x'] }
const met = (verdict = 'met-tested') => ({ criterion: 'c1', at: 'a.py:1', verdict, why: 'test t' })
const pass = { verdict: 'pass', departures: [], criteria: [met()], not_checked: [], report: 'ok' }
const fail = (n) => ({
  verdict: 'fail', departures: [], criteria: [{ ...met('not-met'), criterion: `c${n}` }], not_checked: [], report: `f${n}`,
})
const ready = { verdict: 'ready', reason: '', report: 'the plan' }

// Answers every stage; `verifications` are the Verification's results, round by round.
function stages({ verifications = [pass], prepare = prep, planned = ready, pr = { opened: true, url: 'u', blocker: '' } } = {}) {
  let round = 0
  return {
    agent: (_, o) => (o.label === 'prepare' ? prepare : o.label === 'pull request' ? pr : done),
    workflow: (name) => {
      if (name === 'louie:plan') return planned
      // Each verify Workflow run is 4 agents of its own.
      return verifications[Math.min(round++, verifications.length - 1)]
    },
  }
}

test('deliver opens the pull request when the Verification passes', async () => {
  const { result, calls } = await run('deliver', 'x.md', stages())
  assert.equal(result.verdict, 'done:pr-opened')
  assert.equal(result.pr_url, 'u')
  const pr = calls.find((c) => c.label === 'pull request')
  assert.doesNotMatch(pr.prompt, /as a draft/)
  assert.match(pr.prompt, /met-tested: c1 — test t/)
})

test('deliver opens a draft when a criterion is met with no test', async () => {
  const { result, calls } = await run('deliver', 'x.md', stages({ verifications: [{ ...pass, criteria: [met('met-untested')] }] }))
  assert.equal(result.verdict, 'done:draft-pr')
  assert.match(calls.find((c) => c.label === 'pull request').prompt, /as a draft[\s\S]*met-untested: c1/)
})

test('deliver ends failed:rework-budget after three reworks, with at most 23 agents', async () => {
  const s = stages({ verifications: [fail(1), fail(2), fail(3), fail(4)] })
  let verifies = 0
  const { result, calls } = await run('deliver', 'x.md', { ...s, workflow: (n, a) => (n === 'louie:verify' && verifies++, s.workflow(n, a)) })
  assert.equal(result.verdict, 'failed:rework-budget')
  assert.equal(result.rounds.length, 4)
  assert.ok(!calls.some((c) => c.label === 'pull request'))
  // prepare, implement and three reworks here; plan 1 and verify 4 each run in their Workflows.
  assert.ok(calls.length + 1 + 4 * verifies + 1 <= 23)
})

test('deliver ends failed:not-converging when two rounds fail on the same', async () => {
  const { result } = await run('deliver', 'x.md', stages({ verifications: [fail(1), fail(1)] }))
  assert.equal(result.verdict, 'failed:not-converging')
  assert.equal(result.rounds.length, 2)
})

test('deliver stops before changing anything when prepare stops, or the plan isn\'t ready', async () => {
  const blocked = await run('deliver', 'x.md', stages({ prepare: { ...prep, ok: false, reason: 'no remote' } }))
  assert.equal(blocked.result.verdict, 'blocked:prepare')
  assert.equal(blocked.result.reason, 'no remote')
  assert.deepEqual(blocked.calls.map((c) => c.label), ['prepare'])
  for (const [verdict, want] of [['needs-decision', 'blocked:needs-decision'], ['done:nothing-to-build', 'done:nothing-to-build']]) {
    const { result, calls } = await run('deliver', 'x.md', stages({ planned: { verdict, reason: 'r', report: 'p' } }))
    assert.equal(result.verdict, want)
    // The worktree it made, holding nothing yet, is discarded.
    assert.deepEqual(calls.map((c) => c.label), ['prepare', 'discard'])
    assert.equal(result.worktree, '')
  }
  assert.equal((await run('deliver', undefined)).result.verdict, 'blocked:no-issue')
})
