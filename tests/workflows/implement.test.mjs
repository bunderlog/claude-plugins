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

const clean = { findings: [] }
const bug = (n, isBug = true) => ({ at: `a.py:${n}`, what: `w${n}`, bug: isBug })

// Answers every stage; `verifications` are the Verification's results and `reviews` the review's,
// round by round.
function stages({
  verifications = [pass], reviews = [clean], prepare = prep, planned = ready,
  push = { pushed: true, head: 'c1', blocker: '' }, pr = { opened: true, url: 'u', blocker: '' },
} = {}) {
  let round = 0
  let reviewed = 0
  return {
    agent: (_, o) => {
      if (o.label === 'prepare') return prepare
      if (o.label === 'push') return push
      if (o.label === 'pull request') return pr
      if (o.label.startsWith('review')) return reviews[Math.min(reviewed++, reviews.length - 1)]
      return done
    },
    workflow: (name) => {
      if (name === 'louie:plan') return planned
      // Each verify Workflow run is 4 agents of its own.
      return verifications[Math.min(round++, verifications.length - 1)]
    },
  }
}

test('implement opens the pull request when the Verification passes', async () => {
  const { result, calls } = await run('implement', 'x.md', stages())
  assert.equal(result.verdict, 'done:pr-opened')
  assert.equal(result.pr_url, 'u')
  const pr = calls.find((c) => c.label === 'pull request')
  assert.doesNotMatch(pr.prompt, /as a draft/)
  assert.match(pr.prompt, /met-tested: c1 — test t/)
})

const untested = { ...pass, criteria: [met('met-untested')] }

test('implement reworks for a criterion met with no test', async () => {
  const { result, calls } = await run('implement', 'x.md', stages({ verifications: [untested, pass] }))
  assert.equal(result.verdict, 'done:pr-opened')
  assert.match(calls.find((c) => c.label === 'rework 1').prompt, /no test[^\n]*\n- c1/)
})

// A criterion only the person checks by hand stays untested: the rework changes nothing, and the
// run opens the draft rather than fail.
test('implement opens a draft when a criterion stays untested after a rework', async () => {
  const { result, calls } = await run('implement', 'x.md', stages({ verifications: [untested] }))
  assert.equal(result.verdict, 'done:draft-pr')
  assert.equal(result.rounds.length, 2)
  assert.match(calls.find((c) => c.label === 'pull request').prompt, /as a draft[\s\S]*met-untested: c1/)
})

test('implement opens a draft when only an untested criterion is left once the reworks are spent', async () => {
  const { result } = await run('implement', 'x.md', stages({ verifications: [fail(1), fail(2), untested] }))
  assert.equal(result.verdict, 'done:draft-pr')
})

test('implement lists the plan\'s assumptions in the pull request\'s body, for the person to review', async () => {
  const planned = { ...ready, plan: { changes: [], decisions: [], assumptions: ['templates kept as .tmpl files; else they move'] } }
  const { calls } = await run('implement', 'x.md', stages({ planned }))
  assert.match(calls.find((c) => c.label === 'pull request').prompt, /Assumptions[^\n]*\n- templates kept as \.tmpl files; else they move/)
})

test('implement ends failed:rework-budget after two reworks, with at most 22 agents', async () => {
  const s = stages({ verifications: [fail(1), fail(2), fail(3)] })
  let verifies = 0
  const { result, calls } = await run('implement', 'x.md', { ...s, workflow: (n, a) => (n === 'louie:verify' && verifies++, s.workflow(n, a)) })
  assert.equal(result.verdict, 'failed:rework-budget')
  assert.equal(result.rounds.length, 3)
  assert.ok(!calls.some((c) => c.label === 'push' || c.label === 'pull request'))
  assert.equal(calls.filter((c) => c.agentType === 'louie:reviewer').length, verifies)
  // prepare, implement, two reworks and a review a round here; plan 1 and verify 4 each run in
  // their Workflows, and the push and the pull request would be 2.
  assert.ok(calls.length + 1 + 4 * verifies + 2 <= 22)
})

test('implement ends failed:not-converging when two rounds fail on the same', async () => {
  const { result } = await run('implement', 'x.md', stages({ verifications: [fail(1), fail(1)] }))
  assert.equal(result.verdict, 'failed:not-converging')
  assert.equal(result.rounds.length, 2)
  // The same bug twice, with the Verification passing, is the same too.
  const twice = await run('implement', 'x.md', stages({ reviews: [{ findings: [bug(1)] }] }))
  assert.equal(twice.result.verdict, 'failed:not-converging')
  assert.equal(twice.result.rounds.length, 2)
  assert.ok(!twice.calls.some((c) => c.label === 'pull request'))
})

test('implement reworks a round whose review finds a bug, and puts the findings that aren\'t bugs in the pull request\'s body', async () => {
  const reviews = [{ findings: [bug(1)] }, { findings: [bug(2, false)] }]
  const { result, calls } = await run('implement', 'x.md', stages({ reviews }))
  assert.equal(result.verdict, 'done:pr-opened')
  assert.equal(result.rounds.length, 2)
  assert.deepEqual(result.rounds.map((x) => x.bugs.length), [1, 0])
  assert.match(calls.find((c) => c.label === 'rework 1').prompt, /findings to fix:[\s\S]*- a\.py:1 — w1/)
  const pr = calls.find((c) => c.label === 'pull request').prompt
  assert.match(pr, /Review findings that aren't bugs:\n- a\.py:2 — w2/)
  assert.doesNotMatch(pr, /a\.py:1 — w1/)
})

test('implement opens no pull request when the pushed branch ends at another commit than the one the last Verification passed', async () => {
  const { result, calls } = await run('implement', 'x.md', stages({ push: { pushed: true, head: 'c9', blocker: '' } }))
  assert.equal(result.verdict, 'blocked:pull-request')
  assert.match(result.reason, /c9[\s\S]*c1/)
  assert.match(calls.find((c) => c.label === 'push').prompt, /The commit the last Verification passed: c1\./)
  assert.ok(!calls.some((c) => c.label === 'pull request'))
  // A full sha the short one begins is the same commit.
  const full = await run('implement', 'x.md', stages({ push: { pushed: true, head: 'c1f00d', blocker: '' } }))
  assert.equal(full.result.verdict, 'done:pr-opened')
  // A push that fails opens none either.
  const failed = await run('implement', 'x.md', stages({ push: { pushed: false, head: '', blocker: 'rejected' } }))
  assert.deepEqual([failed.result.verdict, failed.result.reason], ['blocked:push', 'rejected'])
  assert.ok(!failed.calls.some((c) => c.label === 'pull request'))
})

test('implement stops before changing anything when prepare stops, or the plan isn\'t ready', async () => {
  const blocked = await run('implement', 'x.md', stages({ prepare: { ...prep, ok: false, reason: 'no remote' } }))
  assert.equal(blocked.result.verdict, 'blocked:prepare')
  const noToken = await run('implement', 'x.md', stages({ prepare: { ...prep, ok: false, reason: 'no-token: BITBUCKET_TOKEN isn\'t set' } }))
  assert.deepEqual([noToken.result.verdict, noToken.calls.map((c) => c.label)], ['blocked:prepare', ['prepare']])
  assert.match(noToken.result.reason + JSON.stringify(noToken.result.results || ''), /no-token/)
  assert.equal(blocked.result.reason, 'no remote')
  assert.deepEqual(blocked.calls.map((c) => c.label), ['prepare'])
  for (const [verdict, want] of [['needs-decision', 'blocked:needs-decision'], ['done:nothing-to-build', 'done:nothing-to-build']]) {
    const { result, calls } = await run('implement', 'x.md', stages({ planned: { verdict, reason: 'r', report: 'p' } }))
    assert.equal(result.verdict, want)
    // The worktree it made, holding nothing yet, is discarded.
    assert.deepEqual(calls.map((c) => c.label), ['prepare', 'discard'])
    assert.equal(result.worktree, '')
  }
  assert.equal((await run('implement', undefined)).result.verdict, 'blocked:no-ticket')
})

// Several Tickets (PRD batch): each stage's Ticket comes from its prompt or its args, and a plan
// changes `changes[ticket]`, or `<ticket>.go` when not named.
const ticketOf = (text) => /Ticket:? (\S+)/.exec(text)[1]
function many({ changes = {}, planned = {}, implemented = {}, verifications = [pass], tick = false } = {}) {
  const events = []
  const verified = {}
  let preparing = 0
  return {
    events,
    agent: async (prompt, o) => {
      const ticket = ticketOf(prompt)
      const stage = o.label.replace(` ${ticket}`, '')
      events.push(`${stage} ${ticket}`)
      if (stage === 'prepare') {
        if (++preparing > 1) events.push('prepares at once')
        if (tick) await new Promise((r) => setTimeout(r, 1))
        preparing--
        return { ...prep, worktree: `/r/.claude/worktrees/${ticket}`, branch: ticket }
      }
      if (stage === 'push') return { pushed: true, head: 'c1', blocker: '' }
      if (stage === 'pull request') return { opened: true, url: `pr/${ticket}`, blocker: '' }
      if (stage.startsWith('review')) return clean
      if (stage === 'implement') return implemented[ticket] || done
      return done
    },
    workflow: async (name, a) => {
      if (name === 'louie:plan') {
        if (tick) await new Promise((r) => setTimeout(r, 1))
        events.push(`plan ${a.ticket}`)
        const where = changes[a.ticket] || [`${a.ticket}.go`]
        return planned[a.ticket] || { ...ready, plan: { changes: where.map((w) => ({ where: w })), decisions: [] } }
      }
      const ticket = /serving the Ticket (\S+)/.exec(a.target)[1]
      events.push(`verify ${ticket}`)
      const n = (verified[ticket] = (verified[ticket] || 0) + 1)
      return verifications[Math.min(n - 1, verifications.length - 1)]
    },
  }
}

test('implement on several Tickets prepares them one at a time and plans them all before building any', async () => {
  const s = many({ tick: true })
  const { result } = await run('implement', 'a b c', s)
  assert.equal(result.verdict, 'done:all')
  assert.ok(!s.events.includes('prepares at once'))
  const firstBuild = s.events.findIndex((e) => e.startsWith('implement'))
  assert.equal(s.events.filter((e, i) => e.startsWith('plan') && i < firstBuild).length, 3)
  assert.deepEqual(result.results.map((x) => x.pr_url), ['pr/a', 'pr/b', 'pr/c'])
})

test('implement on several Tickets implements the ready ones and lists the decisions of the rest', async () => {
  const decision = { question: 'Which store?', options: ['files', 'sqlite'], recommended: 'files, as nothing needs a query' }
  const planned = { b: { verdict: 'needs-decision', reason: '1 Open decision(s)', report: 'p', plan: { changes: [], decisions: [decision] } } }
  const s = many({ planned })
  const { result } = await run('implement', { tickets: ['a', 'b', 'c'] }, s)
  assert.equal(result.verdict, 'done:some')
  assert.deepEqual(result.results.map((x) => x.verdict), ['done:pr-opened', 'blocked:needs-decision', 'done:pr-opened'])
  assert.equal(result.results[1].worktree, '')
  assert.ok(s.events.includes('discard b'))
  assert.deepEqual(result.decisions, [{ ticket: 'b', ...decision }])
  assert.match(result.report, /Open decisions:\n[\s\S]*b: Which store\?\n {3}- files\n {3}- sqlite\n {3}Recommended: files/)
})

test('implement on several Tickets holds back one whose plan changes a file an earlier one does', async () => {
  const changes = { a: ['src/a.go'], b: ['./src/a.go', 'src/b/'], c: ['src/b/c.go'] }
  const s = many({ changes })
  const { result } = await run('implement', 'a b c', s)
  assert.deepEqual(result.results.map((x) => x.verdict), ['done:pr-opened', 'blocked:overlaps', 'done:pr-opened'])
  assert.equal(result.results[1].reason, 'changes src/a.go, as a does')
  assert.equal(result.results[1].worktree, '')
  assert.ok(s.events.includes('discard b'))
  assert.ok(!s.events.includes('implement b'))
})

test('implement on several Tickets takes a folder and a file in it as one, and two files as two', async () => {
  const folder = await run('implement', 'a b', many({ changes: { a: ['web/'], b: ['web/app.ts'] } }))
  assert.equal(folder.result.results[1].verdict, 'blocked:overlaps')
  const two = await run('implement', 'a b', many({ changes: { a: ['web/app.ts'], b: ['web/app.tsx'] } }))
  assert.equal(two.result.verdict, 'done:all')
})

test('implement on several Tickets goes on with the others when one fails the checks', async () => {
  const implemented = { a: { outcome: 'checks-failed', blocker: 'FAIL t', commits: [] } }
  const { result } = await run('implement', 'a b', many({ implemented }))
  assert.equal(result.verdict, 'done:some')
  assert.deepEqual(result.results.map((x) => [x.verdict, x.pr_url || x.reason]), [['blocked:checks', 'FAIL t'], ['done:pr-opened', 'pr/b']])
})

test('implement on several Tickets plans each once, with at most 22 agents a Ticket', async () => {
  const s = many({ verifications: [fail(1), fail(2), fail(3)] })
  const { result, calls } = await run('implement', 'a b c', s)
  assert.deepEqual(result.results.map((x) => x.verdict), ['failed:rework-budget', 'failed:rework-budget', 'failed:rework-budget'])
  assert.equal(s.events.filter((e) => e.startsWith('plan')).length, 3)
  const plans = 3
  const verifiers = 4 * s.events.filter((e) => e.startsWith('verify')).length
  assert.ok(calls.length + plans + verifiers <= 22 * 3)
})

test('implement takes at most five Tickets, and a Ticket named twice once', async () => {
  const six = await run('implement', 'a b c d e f', many())
  assert.equal(six.result.verdict, 'blocked:too-many')
  assert.deepEqual(six.calls, [])
  const none = await run('implement', '  ', many())
  assert.equal(none.result.verdict, 'blocked:no-ticket')
  assert.deepEqual(none.calls, [])
  // An array, the shape the Workflow tool's description suggests for a list, is the same list.
  const array = await run('implement', ['a', 'b'], many())
  assert.equal(array.result.results.length, 2)
  const s = many()
  const twice = await run('implement', 'a b c d e a', s)
  assert.equal(twice.result.results.length, 5)
  assert.equal(s.events.filter((e) => e === 'prepare a').length, 1)
})
