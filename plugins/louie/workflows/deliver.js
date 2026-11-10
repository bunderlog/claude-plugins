export const meta = {
  name: 'deliver',
  description: 'Take an agreed Issue to a pull request: a new branch and worktree, the plan, commits the project\'s checks pass, a Verification against what the project agreed with up to three reworks, and the pull request.',
  whenToUse: 'When the user asks to deliver, build or implement an agreed Issue up to a pull request, usually after /louie:plan and once its decisions are written into the Issue. Takes the Issue: its key or URL in the tracker the project names, or its file in .about/issues/. Leaves the person\'s checkout as it is.',
  phases: [
    { title: 'Prepare' },
    { title: 'Plan' },
    { title: 'Implement' },
    { title: 'Verify' },
    { title: 'Pull request' },
  ],
}

// args: the Issue, as text (a tracker's key or URL, or a file in .about/issues/), or { issue }.
//
// The script decides the order of the stages and every way out of them; the agents do the work
// (PRD delivery). Plan and Verify are louie's own Workflows, run as stages. At most 23 agents:
// prepare 1, plan 1, implement 1, verify 4, three reworks of 1 + 4, pull request 1. The agent's
// name repeats louie's names.PLUGIN, as a script can't import it.

const MAX_REWORK = 3
const issue = typeof args === 'string' ? args : (args && args.issue) || ''

const PREPARE_SCHEMA = {
  type: 'object',
  properties: {
    ok: { type: 'boolean', description: 'false when the prepare stage stopped, changing nothing' },
    reason: { type: 'string', description: 'ok false: why, with the error; else empty' },
    worktree: { type: 'string', description: 'the worktree\'s absolute path; empty when not ok' },
    branch: { type: 'string', description: 'the new branch; empty when not ok' },
    base: { type: 'string', description: 'the commit the branch starts from, its full sha; empty when not ok' },
    default_branch: { type: 'string', description: 'the remote\'s default branch' },
  },
  required: ['ok', 'reason', 'worktree', 'branch', 'base', 'default_branch'],
}

const IMPLEMENT_SCHEMA = {
  type: 'object',
  properties: {
    outcome: {
      type: 'string',
      enum: ['done', 'checks-failed', 'unimplementable'],
      description: 'done: committed, and the project\'s checks pass on the last commit; checks-failed: they could not pass; unimplementable: the plan contradicts the code',
    },
    blocker: { type: 'string', description: 'when not done: why, with the checks\' output; else empty' },
    commits: { type: 'array', items: { type: 'string' }, description: 'the commits made, `<sha> <subject>` each' },
  },
  required: ['outcome', 'blocker', 'commits'],
}

const PR_SCHEMA = {
  type: 'object',
  properties: {
    opened: { type: 'boolean' },
    url: { type: 'string', description: 'the pull request\'s URL; empty when not opened' },
    blocker: { type: 'string', description: 'when not opened: why, with the error; else empty' },
  },
  required: ['opened', 'url', 'blocker'],
}

const rounds = []
let prep = null
const end = (verdict, reason, extra) => ({
  verdict,
  reason: reason || '',
  issue,
  branch: prep ? prep.branch : '',
  worktree: prep ? prep.worktree : '',
  rounds,
  ...extra,
})

// What a failed Verification failed on, so two rounds can be told the same or not.
const failedOn = (v) =>
  JSON.stringify([
    ...v.criteria.filter((c) => c.verdict === 'not-met').map((c) => `criterion: ${c.criterion}`),
    ...v.departures.filter((d) => d.blocks).map((d) => `${d.source}: ${d.at} ${d.from}`),
  ].sort())

if (!issue) return end('blocked:no-issue', 'no Issue named')

phase('Prepare')
prep = await agent(
  `Stage: prepare\nIssue: ${issue}\nPrepare the run, as your instructions say.`,
  { agentType: 'louie:implementer', schema: PREPARE_SCHEMA, label: 'prepare' },
)
if (!prep) return end('blocked:tooling', 'the prepare stage returned nothing')
if (!prep.ok) {
  const why = prep.reason
  prep = null
  return end('blocked:prepare', why)
}
const where = `the worktree ${prep.worktree}, branch ${prep.branch}`

phase('Plan')
let planned
try {
  planned = await workflow('louie:plan', { issue, dir: prep.worktree })
} catch (e) {
  return end('blocked:tooling', `the plan Workflow failed: ${e && e.message ? e.message : e}`)
}
if (!planned || !planned.verdict) return end('blocked:tooling', 'the plan Workflow returned nothing')
if (planned.verdict !== 'ready') {
  const verdict = planned.verdict === 'needs-decision' ? 'blocked:needs-decision' : planned.verdict
  return end(verdict, planned.reason, { plan: planned.report })
}

let findings = ''
let last = ''
let verification = null
for (let round = 0; ; round++) {
  const mode = round === 0 ? 'implement' : 'rework'
  phase('Implement')
  const impl = await agent(
    `Stage: ${mode}\nIssue: ${issue}\nWork in ${where}.\n\nThe plan:\n${planned.report}` +
      (findings ? `\n\nThe Verification's findings to fix:\n${findings}` : ''),
    { agentType: 'louie:implementer', schema: IMPLEMENT_SCHEMA, label: round ? `rework ${round}` : 'implement' },
  )
  if (!impl) return end('blocked:tooling', `the ${mode} stage returned nothing`)
  if (impl.outcome === 'checks-failed') return end('blocked:checks', impl.blocker)
  if (impl.outcome !== 'done') return end('blocked:unimplementable', impl.blocker)
  if (!impl.commits.length && round === 0) return end('blocked:tooling', 'nothing was committed')

  phase('Verify')
  try {
    verification = await workflow('louie:verify', {
      target: `the commits ${prep.base}..${prep.branch} in ${prep.worktree} (run git and read files there), serving the Issue ${issue}`,
    })
  } catch (e) {
    return end('blocked:tooling', `the verify Workflow failed: ${e && e.message ? e.message : e}`)
  }
  if (!verification || !verification.verdict) return end('blocked:tooling', 'the verify Workflow returned nothing')
  rounds.push({ mode, commits: impl.commits, verdict: verification.verdict })
  if (verification.verdict === 'pass') break

  const now = failedOn(verification)
  if (round >= MAX_REWORK) return end('failed:rework-budget', verification.report)
  if (now === last) return end('failed:not-converging', verification.report)
  last = now
  findings = verification.report
}

// Ready to merge only when every criterion is met and tested and nothing was left unchecked.
const draft =
  verification.criteria.some((c) => c.verdict !== 'met-tested') ||
  verification.departures.length > 0 ||
  verification.not_checked.length > 0 ||
  !verification.criteria.length

const body = [
  `Delivers ${issue}.`,
  '',
  'Acceptance criteria:',
  ...(verification.criteria.length
    ? verification.criteria.map((c) => `- ${c.verdict}: ${c.criterion} — ${c.why}`)
    : ['- none found by the Verification']),
  '',
  'The app was not run; check its behavior by hand or with Claude Code\'s /verify.',
  '',
  'Verification:',
  verification.report,
].join('\n')

phase('Pull request')
const pr = await agent(
  `Stage: pull-request\nIssue: ${issue}\nWork in ${where}, against ${prep.default_branch}.\n` +
    `Open the pull request${draft ? ' as a draft' : ''}, its body this text, as it is:\n\n${body}`,
  { agentType: 'louie:implementer', schema: PR_SCHEMA, label: 'pull request' },
)
if (!pr) return end('blocked:tooling', 'the pull-request stage returned nothing')
if (!pr.opened || !pr.url) return end('blocked:pull-request', pr.blocker)

return end(draft ? 'done:draft-pr' : 'done:pr-opened', '', { pr_url: pr.url })
