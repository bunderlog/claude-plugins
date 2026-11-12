export const meta = {
  name: 'deliver',
  description: 'Take agreed Issues to pull requests: for each a new branch and worktree and the plan, then, for those whose plans are ready and change different files, commits the project\'s checks pass, a Verification against what the project agreed with up to three reworks, and the pull request.',
  whenToUse: 'When the user asks to deliver, build or implement agreed Issues up to pull requests, usually after /louie:plan and once their decisions are written into the Issues. Takes one to five Issues: each its key or URL in the tracker the project names, or its file in .about/issues/. Several are all planned before any is built, and every decision for the person comes in one report. Leaves the person\'s checkout as it is.',
  phases: [
    { title: 'Prepare' },
    { title: 'Plan' },
    { title: 'Implement' },
    { title: 'Pull request' },
  ],
}

// args: the Issues, as text split on whitespace (a tracker's key or URL, or a file in
// .about/issues/), or { issues } or { issue }.
//
// The script decides the order of the stages and every way out of them; the agents do the work
// (PRD delivery, PRD batch). Each Issue is prepared in turn, as git locks a repo's worktrees, then
// all are planned before any is built. Plan and Verify are louie's own Workflows, run as stages.
// At most 23 agents an Issue: prepare 1, plan 1, implement 1, verify 4, three reworks of 1 + 4,
// pull request 1; an Issue that stops before it is built spends one more, to discard the worktree
// it made. The agent's name repeats louie's names.PLUGIN, as a script can't import it.

const MAX_ISSUES = 5
const MAX_REWORK = 3
const named =
  typeof args === 'string' ? args.split(/\s+/) : (args && (args.issues || (args.issue ? [args.issue] : []))) || []
const issues = [...new Set(named.map((i) => String(i).trim()).filter(Boolean))]

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

// One Issue's run: its stages fill it in, and end() makes what the run returns for it.
const runs = issues.map((issue) => ({ issue, prep: null, planned: null, where: '', rounds: [] }))
const label = (r, stage) => (issues.length > 1 ? `${stage} ${r.issue}` : stage)
const end = (r, verdict, reason, extra) => ({
  verdict,
  reason: reason || '',
  issue: r.issue,
  branch: r.prep ? r.prep.branch : '',
  worktree: r.prep ? r.prep.worktree : '',
  rounds: r.rounds,
  ...extra,
})

// What a failed Verification failed on, so two rounds can be told the same or not.
const failedOn = (v) =>
  JSON.stringify([
    ...v.criteria.filter((c) => c.verdict === 'not-met').map((c) => `criterion: ${c.criterion}`),
    ...v.departures.filter((d) => d.blocks).map((d) => `${d.source}: ${d.at} ${d.from}`),
  ].sort())

// The files a ready plan changes, and whether two of them are one: the same path, or a folder
// holding the other.
const files = (r) => ((r.planned.plan && r.planned.plan.changes) || []).map((c) => c.where.replace(/^\.\//, '').replace(/\/+$/, ''))
const same = (a, b) => a === b || a.startsWith(`${b}/`) || b.startsWith(`${a}/`)

async function prepare(r) {
  r.prep = await agent(
    `Stage: prepare\nIssue: ${r.issue}\nPrepare the run, as your instructions say.`,
    { agentType: 'louie:implementer', schema: PREPARE_SCHEMA, label: label(r, 'prepare'), phase: 'Prepare' },
  )
  if (!r.prep) return end(r, 'blocked:tooling', 'the prepare stage returned nothing')
  if (!r.prep.ok) {
    const why = r.prep.reason
    r.prep = null
    return end(r, 'blocked:prepare', why)
  }
  r.where = `the worktree ${r.prep.worktree}, branch ${r.prep.branch}`
  return null
}

// The worktree holds nothing yet: a rerun once the decisions are in starts a new one.
async function discard(r, verdict, reason, extra) {
  await agent(
    `Stage: discard\nIssue: ${r.issue}\nDiscard ${r.where}, as your instructions say.`,
    { agentType: 'louie:implementer', label: label(r, 'discard'), phase: 'Plan' },
  )
  const result = end(r, verdict, reason, extra)
  r.prep = null
  return { ...result, branch: '', worktree: '' }
}

async function plan(r) {
  try {
    r.planned = await workflow('louie:plan', { issue: r.issue, dir: r.prep.worktree })
  } catch (e) {
    return end(r, 'blocked:tooling', `the plan Workflow failed: ${e && e.message ? e.message : e}`)
  }
  if (!r.planned || !r.planned.verdict) return end(r, 'blocked:tooling', 'the plan Workflow returned nothing')
  if (r.planned.verdict !== 'ready') {
    const verdict = r.planned.verdict === 'needs-decision' ? 'blocked:needs-decision' : r.planned.verdict
    return discard(r, verdict, r.planned.reason, { plan: r.planned.report })
  }
  return null
}

async function build(r) {
  let findings = ''
  let last = ''
  let verification = null
  for (let round = 0; ; round++) {
    const mode = round === 0 ? 'implement' : 'rework'
    const impl = await agent(
      `Stage: ${mode}\nIssue: ${r.issue}\nWork in ${r.where}.\n\nThe plan:\n${r.planned.report}` +
        (findings ? `\n\nThe Verification's findings to fix:\n${findings}` : ''),
      {
        agentType: 'louie:implementer',
        schema: IMPLEMENT_SCHEMA,
        label: label(r, round ? `rework ${round}` : 'implement'),
        phase: 'Implement',
      },
    )
    if (!impl) return end(r, 'blocked:tooling', `the ${mode} stage returned nothing`)
    if (impl.outcome === 'checks-failed') return end(r, 'blocked:checks', impl.blocker)
    if (impl.outcome !== 'done') return end(r, 'blocked:unimplementable', impl.blocker)
    if (!impl.commits.length && round === 0) return end(r, 'blocked:tooling', 'nothing was committed')

    try {
      verification = await workflow('louie:verify', {
        target: `the commits ${r.prep.base}..${r.prep.branch} in ${r.prep.worktree} (run git and read files there), serving the Issue ${r.issue}`,
      })
    } catch (e) {
      return end(r, 'blocked:tooling', `the verify Workflow failed: ${e && e.message ? e.message : e}`)
    }
    if (!verification || !verification.verdict) return end(r, 'blocked:tooling', 'the verify Workflow returned nothing')
    r.rounds.push({ mode, commits: impl.commits, verdict: verification.verdict })
    if (verification.verdict === 'pass') break

    const now = failedOn(verification)
    if (round >= MAX_REWORK) return end(r, 'failed:rework-budget', verification.report)
    if (now === last) return end(r, 'failed:not-converging', verification.report)
    last = now
    findings = verification.report
  }

  // Ready to merge only when every criterion is met and tested and nothing was left unchecked.
  const draft =
    verification.criteria.some((c) => c.verdict !== 'met-tested') ||
    verification.departures.length > 0 ||
    verification.not_checked.length > 0 ||
    !verification.criteria.length

  // The plan builds on its assumptions rather than stop for them: the person reviews them here.
  const assumptions = (r.planned.plan && r.planned.plan.assumptions) || []
  const body = [
    `Delivers ${r.issue}.`,
    '',
    'Acceptance criteria:',
    ...(verification.criteria.length
      ? verification.criteria.map((c) => `- ${c.verdict}: ${c.criterion} — ${c.why}`)
      : ['- none found by the Verification']),
    '',
    ...(assumptions.length ? ['Assumptions the plan made, to review:', ...assumptions.map((a) => `- ${a}`), ''] : []),
    'The app was not run; check its behavior by hand or with Claude Code\'s /verify.',
    '',
    'Verification:',
    verification.report,
  ].join('\n')

  const pr = await agent(
    `Stage: pull-request\nIssue: ${r.issue}\nWork in ${r.where}, against ${r.prep.default_branch}.\n` +
      `Open the pull request${draft ? ' as a draft' : ''}, its body this text, as it is:\n\n${body}`,
    { agentType: 'louie:implementer', schema: PR_SCHEMA, label: label(r, 'pull request'), phase: 'Pull request' },
  )
  if (!pr) return end(r, 'blocked:tooling', 'the pull-request stage returned nothing')
  if (!pr.opened || !pr.url) return end(r, 'blocked:pull-request', pr.blocker)

  return end(r, draft ? 'done:draft-pr' : 'done:pr-opened', '', { pr_url: pr.url })
}

if (!issues.length) return { verdict: 'blocked:no-issue', reason: 'no Issue named', results: [], decisions: [], report: '' }
if (issues.length > MAX_ISSUES) {
  const reason = `${issues.length} Issues named; at most ${MAX_ISSUES} at once`
  return { verdict: 'blocked:too-many', reason, results: [], decisions: [], report: '' }
}

const results = new Map()
phase('Prepare')
for (const r of runs) {
  const stopped = await prepare(r)
  if (stopped) results.set(r, stopped)
}

phase('Plan')
const prepared = runs.filter((r) => !results.has(r))
const plans = await parallel(prepared.map((r) => () => plan(r)))
prepared.forEach((r, i) => plans[i] && results.set(r, plans[i]))

// Of the ready plans, in the order named, one changing a file an earlier one that goes on changes
// waits for that one's pull request.
const going = []
for (const r of runs.filter((x) => !results.has(x))) {
  const mine = files(r)
  const other = going.find((g) => files(g).some((f) => mine.some((m) => same(f, m))))
  if (!other) {
    going.push(r)
    continue
  }
  const shared = mine.filter((m) => files(other).some((f) => same(f, m)))
  results.set(r, await discard(r, 'blocked:overlaps', `changes ${shared.join(', ')}, as ${other.issue} does`, { plan: r.planned.report }))
}

const built = await parallel(going.map((r) => () => build(r)))
going.forEach((r, i) => results.set(r, built[i] || end(r, 'blocked:tooling', 'the run stopped')))

if (issues.length === 1) return results.get(runs[0])

const each = runs.map((r) => results.get(r))
const decisions = runs.flatMap((r) =>
  ((r.planned && r.planned.plan && r.planned.plan.decisions) || []).map((d) => ({ issue: r.issue, ...d })),
)
const delivered = each.filter((x) => x.verdict.startsWith('done:')).length
const verdict = delivered === each.length ? 'done:all' : delivered ? 'done:some' : 'blocked:none'

const lines = ['Issues:']
each.forEach((x) => lines.push(`- ${x.issue}: ${x.verdict}${x.pr_url ? ` ${x.pr_url}` : x.reason ? ` — ${x.reason}` : ''}`))
if (decisions.length) {
  lines.push('', 'Decisions for the person:')
  decisions.forEach((d, i) => {
    lines.push(`${i + 1}. ${d.issue}: ${d.question}`)
    d.options.forEach((o) => lines.push(`   - ${o}`))
    lines.push(`   Recommended: ${d.recommended}`)
  })
}

return { verdict, reason: '', results: each, decisions, report: lines.join('\n') }
