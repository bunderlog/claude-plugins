import { test } from 'node:test'
import assert from 'node:assert/strict'
import { run } from './harness.mjs'

const met = (verdict = 'met-tested') => ({ criterion: 'c1', at: 'a.py:1', verdict, why: 'test t' })
const pass = { verdict: 'pass', departures: [], criteria: [met()], not_checked: [], report: 'ok' }
const fail = (n) => ({
  verdict: 'fail', departures: [], criteria: [{ ...met('not-met'), criterion: `c${n}` }], not_checked: [], report: `f${n}`,
})
const clean = { findings: [] }

// Answers every stage of pull request n, its stage named by its label less ` #n`; `by[n]` replaces
// a stage's answer for pull request n, and `verifications` are each one's Verifications, round by
// round. `events` logs each stage as `<stage> <n>` when it starts, and `merged <n>` once merged.
function stages({ by = {}, verifications = [pass], tick = false } = {}) {
  const events = []
  const heads = {}
  const verified = {}
  const answer = (n, stage, fallback) => (by[n] && by[n][stage] !== undefined ? by[n][stage] : fallback)
  return {
    events,
    agent: async (prompt, o) => {
      const m = /Pull request: #(\d+)/.exec(prompt) || / #(\d+)$/.exec(o.label)
      const n = m ? Number(m[1]) : 1
      const stage = o.label.replace(/ #\d+$/, '')
      events.push(`${stage} ${n}`)
      if (tick) await new Promise((r) => setTimeout(r, 1))
      if (stage === 'prepare') {
        return answer(n, 'prepare', {
          status: 'ok', reason: '', number: n, branch: `b${n}`, head: `h${n}`, default_branch: 'main',
          ticket: `.about/tickets/t${n}.md`, method: 'rebase', worktree: `/r/.claude/worktrees/pr-${n}`,
        })
      }
      if (stage === 'rebase') {
        heads[n] = `c${n}`
        return answer(n, 'rebase', { outcome: 'done', blocker: '', decisions: [], base: 'm0', head: `c${n}` })
      }
      if (stage.startsWith('rework')) {
        heads[n] = `c${n}r${stage.split(' ')[1]}`
        return { outcome: 'done', blocker: '', commits: [`${heads[n]} fix: x`] }
      }
      if (stage.startsWith('review')) return clean
      // A full sha the short one begins is the same commit.
      if (stage === 'push') return answer(n, 'push', { pushed: true, head: `${heads[n]}f00d`, blocker: '' })
      if (stage === 'ci') return answer(n, 'ci', { status: 'passed', check: '', link: '', reason: '' })
      if (stage === 'merge') {
        const merged = answer(n, 'merge', { status: 'merged', reason: '' })
        if (merged.status === 'merged') events.push(`merged ${n}`)
        return merged
      }
      return null
    },
    // Each verify Workflow run is 4 agents of its own.
    workflow: async (name, a) => {
      const n = Number(/pr-(\d+)/.exec(a.target)[1])
      events.push(`verify ${n}`)
      if (tick) await new Promise((r) => setTimeout(r, 1))
      const round = (verified[n] = (verified[n] || 0) + 1)
      const mine = answer(n, 'verifications', verifications)
      return mine[Math.min(round - 1, mine.length - 1)]
    },
  }
}

const prOf = (event) => Number(event.split(' ').pop())
const labels = (calls) => calls.map((c) => c.label)

test('merge takes the pull requests one at a time, each starting once the one before has merged or stopped', async () => {
  const s = stages({ tick: true })
  const { result } = await run('merge', '1 2 3', s)
  assert.equal(result.verdict, 'done:all')
  assert.ok(s.events.indexOf('prepare 2') > s.events.indexOf('merged 1'))
  assert.ok(s.events.indexOf('prepare 3') > s.events.indexOf('merged 2'))
  // No stage of one runs among another's.
  const order = s.events.map(prOf)
  assert.deepEqual(order, [...order].sort())

  const stopped = stages({ tick: true, by: { 2: { ci: { status: 'failed', check: 'test', link: 'l', reason: '' } } } })
  const second = await run('merge', '1 2 3', stopped)
  assert.deepEqual(second.result.results.map((x) => x.verdict), ['done:merged', 'blocked:ci', 'done:merged'])
  assert.ok(stopped.events.indexOf('prepare 3') > stopped.events.indexOf('ci 2'))
  const after = stopped.events.map(prOf)
  assert.deepEqual(after, [...after].sort())
})

test('merge goes on with the others when a rebase needs an Open decision, and reports it under its pull request', async () => {
  const decision = { question: 'Which link stays?', files: ['README.md'], options: ['both', 'the first'], recommended: 'both, as each Ticket needs one' }
  const s = stages({ by: { 2: { rebase: { outcome: 'needs-decision', blocker: '', decisions: [decision], base: 'm0', head: '' } } } })
  const { result, calls } = await run('merge', { prs: ['1', '#2', '3'] }, s)
  assert.equal(result.verdict, 'done:some')
  assert.deepEqual(result.results.map((x) => [x.pr, x.verdict]), [[1, 'done:merged'], [2, 'blocked:needs-decision'], [3, 'done:merged']])
  assert.deepEqual(result.decisions, [{ pr: 2, ...decision }])
  assert.ok(!labels(calls).includes('push #2'))
  assert.ok(!s.events.includes('verify 2'))
  assert.match(result.report, /#2: blocked:needs-decision[\s\S]*1\. #2: Which link stays\? \(README\.md\)\n {3}- both\n {3}- the first\n {3}Recommended: both/)
})

test('merge verifies and reviews a pull request whose rebase had no conflict before its push', async () => {
  const s = stages()
  let target = ''
  const { result, calls } = await run('merge', '7', { ...s, workflow: (n, a) => ((target = a.target), s.workflow(n, a)) })
  assert.equal(result.verdict, 'done:all')
  assert.deepEqual(result.results.map((x) => x.verdict), ['done:merged'])
  // The Verification and the review run together, in either order, both before the push.
  const at = (e) => s.events.indexOf(e)
  assert.deepEqual(s.events.filter((e) => e !== 'verify 7' && e !== 'review 7'), ['prepare 7', 'rebase 7', 'push 7', 'ci 7', 'merge 7', 'merged 7'])
  assert.ok(at('verify 7') > at('rebase 7') && at('verify 7') < at('push 7'))
  assert.ok(at('review 7') > at('rebase 7') && at('review 7') < at('push 7'))
  assert.equal(calls.find((c) => c.label === 'review').agentType, 'louie:reviewer')
  // On the rebased commits, its Ticket read from the default branch, as the pull request deletes it.
  assert.match(target, /m0\.\.c7 in \/r\/\.claude\/worktrees\/pr-7/)
  assert.match(target, /git show origin\/main:\.about\/tickets\/t7\.md/)
  assert.match(calls.find((c) => c.label === 'push').prompt, /--force-with-lease=b7:h7[\s\S]*passed: c7\./)
  assert.match(calls.find((c) => c.label === 'merge').prompt, /method rebase, its head c7f00d, its base m0/)
})

test('merge merges a reworked pull request at the full sha the remote reports, not the rework\'s short one', async () => {
  const s = stages({ verifications: [fail(1), pass] })
  const { result, calls } = await run('merge', '1', s)
  assert.equal(result.results[0].verdict, 'done:merged')
  assert.equal(result.results[0].head, 'c1r1f00d')
  assert.match(calls.find((c) => c.label === 'push').prompt, /passed: c1r1\./)
  assert.match(calls.find((c) => c.label === 'ci').prompt, /Its head: c1r1f00d\./)
  assert.match(calls.find((c) => c.label === 'merge').prompt, /its head c1r1f00d,/)
  assert.match(calls.find((c) => c.label === 'rework 1').prompt, /its head c1, its base m0\./)
})

test('merge merges nothing on a Verification that passed with a verifier returning nothing, a criterion not checked or none found', async () => {
  const silent = { ...pass, not_checked: ['Glossary: the verifier returned nothing'] }
  const none = { ...pass, criteria: [] }
  const untold = { ...pass, criteria: [met(), { ...met('not-checked'), criterion: 'c2' }] }
  for (const v of [silent, none, untold]) {
    const { result, calls } = await run('merge', '1', stages({ verifications: [v] }))
    assert.equal(result.results[0].verdict, 'blocked:unverified')
    assert.ok(!labels(calls).some((l) => ['rework 1', 'push', 'ci', 'merge'].includes(l)))
  }
  const missing = await run('merge', '1', stages({ verifications: [silent] }))
  assert.match(missing.result.results[0].reason, /Glossary: the verifier returned nothing/)
  // What a verifier read and left for a person to check doesn't stop it.
  const read = await run('merge', '1', stages({ verifications: [{ ...pass, not_checked: ['ADRs: a real run, for /verify'] }] }))
  assert.equal(read.result.results[0].verdict, 'done:merged')
  // Nor does a criterion met but untested: the person accepted it in marking the pull request ready.
  const untested = await run('merge', '1', stages({ verifications: [{ ...pass, criteria: [met('met-untested')] }] }))
  assert.equal(untested.result.results[0].verdict, 'done:merged')
})

test('merge runs no Verification, push or merge after a rebase whose checks fail', async () => {
  const s = stages({ by: { 1: { rebase: { outcome: 'checks-failed', blocker: 'FAIL t', decisions: [], base: 'm0', head: '' } } } })
  const { result, calls } = await run('merge', '1', s)
  assert.equal(result.verdict, 'blocked:none')
  assert.deepEqual([result.results[0].verdict, result.results[0].reason], ['blocked:checks', 'FAIL t'])
  assert.deepEqual(labels(calls), ['prepare', 'rebase'])
  assert.ok(!s.events.includes('verify 1'))
})

test('merge ends failed:rework-budget after two reworks when every Verification fails on new criteria', async () => {
  const s = stages({ verifications: [fail(1), fail(2), fail(3)] })
  const { result, calls } = await run('merge', '1', s)
  assert.equal(result.results[0].verdict, 'failed:rework-budget')
  assert.equal(result.results[0].rounds.length, 3)
  assert.deepEqual(labels(calls).filter((l) => l.startsWith('rework')), ['rework 1', 'rework 2'])
  assert.ok(!labels(calls).some((l) => ['push', 'ci', 'merge'].includes(l)))
  // A rework gets the Ticket and the findings, not a plan.
  const rework = calls.find((c) => c.label === 'rework 1').prompt
  assert.match(rework, /Ticket: \.about\/tickets\/t1\.md[\s\S]*findings to fix:\nf1/)
  assert.doesNotMatch(rework, /plan/)
  // The same failure twice ends sooner.
  const same = await run('merge', '1', stages({ verifications: [fail(1), fail(1)] }))
  assert.equal(same.result.results[0].verdict, 'failed:not-converging')
})

test('merge merges nothing when the pushed branch isn\'t the commit the Verification passed, or a check fails', async () => {
  const moved = await run('merge', '1', stages({ by: { 1: { push: { pushed: true, head: 'c9', blocker: '' } } } }))
  assert.equal(moved.result.results[0].verdict, 'blocked:push-mismatch')
  assert.match(moved.result.results[0].reason, /c9[\s\S]*c1/)
  assert.ok(!labels(moved.calls).some((l) => l === 'ci' || l === 'merge'))

  const red = await run('merge', '1', stages({ by: { 1: { ci: { status: 'failed', check: 'lint', link: 'https://ci/1', reason: '' } } } }))
  assert.equal(red.result.results[0].verdict, 'blocked:ci')
  assert.match(red.result.results[0].reason, /lint[\s\S]*https:\/\/ci\/1/)
  assert.ok(!labels(red.calls).includes('merge'))

  // A push the lease refused, and a ci run still going after the hour, merge nothing either.
  const leased = await run('merge', '1', stages({ by: { 1: { push: { pushed: false, head: '', blocker: 'stale info' } } } }))
  assert.deepEqual([leased.result.results[0].verdict, leased.result.results[0].reason], ['blocked:push', 'stale info'])
  const slow = await run('merge', '1', stages({ by: { 1: { ci: { status: 'timeout', check: 'e2e', link: 'l', reason: '' } } } }))
  assert.equal(slow.result.results[0].verdict, 'blocked:ci-timeout')
  assert.ok(!labels(slow.calls).includes('merge'))
})

test('merge stops a pull request at prepare when it is a draft, closed, not on the default branch, in another repo, or has no Ticket or no merge method it can tell', async () => {
  for (const status of ['draft', 'closed', 'no-ticket', 'merge-method', 'not-default', 'other-repo']) {
    const prepare = { status, reason: 'r', number: 1, branch: '', head: '', default_branch: 'main', ticket: '', method: '', worktree: '' }
    const { result, calls } = await run('merge', '1', stages({ by: { 1: { prepare } } }))
    assert.equal(result.verdict, 'blocked:none')
    assert.deepEqual([result.results[0].verdict, result.results[0].reason], [`blocked:${status}`, 'r'])
    assert.deepEqual(labels(calls), ['prepare'])
  }
})

test('merge stops a pull request when the default branch moved since its rebase or the code host refuses the merge', async () => {
  const moved = await run('merge', '1', stages({ by: { 1: { merge: { status: 'base-moved', reason: 'main is at m1' } } } }))
  assert.equal(moved.result.results[0].verdict, 'blocked:base-moved')
  const refused = await run('merge', '1', stages({ by: { 1: { merge: { status: 'refused', reason: 'review required' } } } }))
  assert.deepEqual([refused.result.results[0].verdict, refused.result.results[0].reason], ['blocked:merge', 'review required'])
})

test('merge takes one to five pull requests, each counted once by its number', async () => {
  const six = await run('merge', '1 2 3 4 5 6', stages())
  assert.equal(six.result.verdict, 'blocked:too-many')
  assert.deepEqual(six.calls, [])
  for (const none of [undefined, '  ', { prs: [] }]) {
    const r = await run('merge', none, stages())
    assert.equal(r.result.verdict, 'blocked:no-pr')
    assert.deepEqual(r.calls, [])
  }
  const odd = await run('merge', '1 main', stages())
  assert.deepEqual([odd.result.verdict, odd.calls], ['blocked:no-pr', []])
  assert.match(odd.result.reason, /main/)

  const s = stages()
  const once = await run('merge', '42 #42 https://github.com/o/r/pull/42', s)
  assert.equal(once.result.verdict, 'done:all')
  assert.equal(once.result.results.length, 1)
  assert.equal(s.events.filter((e) => e === 'prepare 42').length, 1)
  assert.match(once.calls[0].prompt, /#42, named as 42, #42, https:\/\/github\.com\/o\/r\/pull\/42/)
})

test('merge schedules at most 22 agents a pull request', async () => {
  const s = stages({ verifications: [fail(1), fail(2), pass] })
  const { result, calls } = await run('merge', '1 2 3', s)
  assert.deepEqual(result.results.map((x) => x.verdict), ['done:merged', 'done:merged', 'done:merged'])
  const verifies = s.events.filter((e) => e.startsWith('verify')).length
  assert.equal(verifies, 9)
  assert.ok(calls.length + 4 * verifies <= 22 * 3)
})

test('merge stops a pull request the rebase leaves with nothing beyond the default branch, for the person to close', async () => {
  const s = stages({ by: { 1: { rebase: { outcome: 'done', blocker: '', decisions: [], base: 'm0f00d', head: 'm0' } } } })
  const { result, calls } = await run('merge', '1', s)
  assert.equal(result.results[0].verdict, 'blocked:nothing-to-merge')
  assert.deepEqual(labels(calls), ['prepare', 'rebase'])
})
