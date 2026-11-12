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

test('deliver lists the plan\'s assumptions in the pull request\'s body, for the person to review', async () => {
  const planned = { ...ready, plan: { changes: [], decisions: [], assumptions: ['templates kept as .tmpl files; else they move'] } }
  const { calls } = await run('deliver', 'x.md', stages({ planned }))
  assert.match(calls.find((c) => c.label === 'pull request').prompt, /Assumptions[^\n]*\n- templates kept as \.tmpl files; else they move/)
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

// Several Issues (PRD batch): each stage's Issue comes from its prompt or its args, and a plan
// changes `changes[issue]`, or `<issue>.go` when not named.
const issueOf = (text) => /Issue:? (\S+)/.exec(text)[1]
function many({ changes = {}, planned = {}, implemented = {}, verifications = [pass], tick = false } = {}) {
  const events = []
  const verified = {}
  let preparing = 0
  return {
    events,
    agent: async (prompt, o) => {
      const issue = issueOf(prompt)
      const stage = o.label.replace(` ${issue}`, '')
      events.push(`${stage} ${issue}`)
      if (stage === 'prepare') {
        if (++preparing > 1) events.push('prepares at once')
        if (tick) await new Promise((r) => setTimeout(r, 1))
        preparing--
        return { ...prep, worktree: `/r/.claude/worktrees/${issue}`, branch: issue }
      }
      if (stage === 'pull request') return { opened: true, url: `pr/${issue}`, blocker: '' }
      if (stage === 'implement') return implemented[issue] || done
      return done
    },
    workflow: async (name, a) => {
      if (name === 'louie:plan') {
        if (tick) await new Promise((r) => setTimeout(r, 1))
        events.push(`plan ${a.issue}`)
        const where = changes[a.issue] || [`${a.issue}.go`]
        return planned[a.issue] || { ...ready, plan: { changes: where.map((w) => ({ where: w })), decisions: [] } }
      }
      const issue = /serving the Issue (\S+)/.exec(a.target)[1]
      events.push(`verify ${issue}`)
      const n = (verified[issue] = (verified[issue] || 0) + 1)
      return verifications[Math.min(n - 1, verifications.length - 1)]
    },
  }
}

test('deliver on several Issues prepares them one at a time and plans them all before building any', async () => {
  const s = many({ tick: true })
  const { result } = await run('deliver', 'a b c', s)
  assert.equal(result.verdict, 'done:all')
  assert.ok(!s.events.includes('prepares at once'))
  const firstBuild = s.events.findIndex((e) => e.startsWith('implement'))
  assert.equal(s.events.filter((e, i) => e.startsWith('plan') && i < firstBuild).length, 3)
  assert.deepEqual(result.results.map((x) => x.pr_url), ['pr/a', 'pr/b', 'pr/c'])
})

test('deliver on several Issues delivers the ready ones and lists the decisions of the rest', async () => {
  const decision = { question: 'Which store?', options: ['files', 'sqlite'], recommended: 'files, as nothing needs a query' }
  const planned = { b: { verdict: 'needs-decision', reason: '1 decision(s) for the person', report: 'p', plan: { changes: [], decisions: [decision] } } }
  const s = many({ planned })
  const { result } = await run('deliver', { issues: ['a', 'b', 'c'] }, s)
  assert.equal(result.verdict, 'done:some')
  assert.deepEqual(result.results.map((x) => x.verdict), ['done:pr-opened', 'blocked:needs-decision', 'done:pr-opened'])
  assert.equal(result.results[1].worktree, '')
  assert.ok(s.events.includes('discard b'))
  assert.deepEqual(result.decisions, [{ issue: 'b', ...decision }])
  assert.match(result.report, /b: Which store\?\n {3}- files\n {3}- sqlite\n {3}Recommended: files/)
})

test('deliver on several Issues holds back one whose plan changes a file an earlier one does', async () => {
  const changes = { a: ['src/a.go'], b: ['./src/a.go', 'src/b/'], c: ['src/b/c.go'] }
  const s = many({ changes })
  const { result } = await run('deliver', 'a b c', s)
  assert.deepEqual(result.results.map((x) => x.verdict), ['done:pr-opened', 'blocked:overlaps', 'done:pr-opened'])
  assert.equal(result.results[1].reason, 'changes src/a.go, as a does')
  assert.equal(result.results[1].worktree, '')
  assert.ok(s.events.includes('discard b'))
  assert.ok(!s.events.includes('implement b'))
})

test('deliver on several Issues takes a folder and a file in it as one, and two files as two', async () => {
  const folder = await run('deliver', 'a b', many({ changes: { a: ['web/'], b: ['web/app.ts'] } }))
  assert.equal(folder.result.results[1].verdict, 'blocked:overlaps')
  const two = await run('deliver', 'a b', many({ changes: { a: ['web/app.ts'], b: ['web/app.tsx'] } }))
  assert.equal(two.result.verdict, 'done:all')
})

test('deliver on several Issues goes on with the others when one fails the checks', async () => {
  const implemented = { a: { outcome: 'checks-failed', blocker: 'FAIL t', commits: [] } }
  const { result } = await run('deliver', 'a b', many({ implemented }))
  assert.equal(result.verdict, 'done:some')
  assert.deepEqual(result.results.map((x) => [x.verdict, x.pr_url || x.reason]), [['blocked:checks', 'FAIL t'], ['done:pr-opened', 'pr/b']])
})

test('deliver on several Issues plans each once, with at most 23 agents an Issue', async () => {
  const s = many({ verifications: [fail(1), fail(2), fail(3), fail(4)] })
  const { result, calls } = await run('deliver', 'a b c', s)
  assert.deepEqual(result.results.map((x) => x.verdict), ['failed:rework-budget', 'failed:rework-budget', 'failed:rework-budget'])
  assert.equal(s.events.filter((e) => e.startsWith('plan')).length, 3)
  const plans = 3
  const verifiers = 4 * s.events.filter((e) => e.startsWith('verify')).length
  assert.ok(calls.length + plans + verifiers <= 23 * 3)
})

test('deliver takes at most five Issues, and an Issue named twice once', async () => {
  const six = await run('deliver', 'a b c d e f', many())
  assert.equal(six.result.verdict, 'blocked:too-many')
  assert.deepEqual(six.calls, [])
  const none = await run('deliver', '  ', many())
  assert.equal(none.result.verdict, 'blocked:no-issue')
  assert.deepEqual(none.calls, [])
  const s = many()
  const twice = await run('deliver', 'a b c d e a', s)
  assert.equal(twice.result.results.length, 5)
  assert.equal(s.events.filter((e) => e === 'prepare a').length, 1)
})
