export const meta = {
  name: 'merge',
  description: 'Merge pull requests /louie:implement opened, one at a time in the order named: each rebased onto the default branch as it is then, with its duplicates and contradictions with what merged since resolved or put to the person, the project\'s checks, a Verification against its Ticket and a review for bugs run again, with up to two reworks, then pushed with a lease, merged by the project\'s method once the code host\'s checks pass.',
  whenToUse: 'When the user asks to merge, land or ship pull requests /louie:implement opened, once they have read them: naming a pull request here is their consent to merge it. Takes one to five pull requests of the current repo, each its number, #number or URL. A pull request that stops, a draft, a red CI run or a conflict only the person can settle, leaves the others to go on, and the run reports why for each. Leaves the person\'s checkout as it is.',
  phases: [
    { title: 'Prepare' },
    { title: 'Rebase' },
    { title: '▸ louie:verify' },
    { title: 'Merge' },
  ],
}

// args: the pull requests, as text split on whitespace (a number, #number or URL each), or
// { prs }.
//
// The script decides the order of the stages and every way out of them; the agents do the work
// (PRD merge). The pull requests run strictly one after another, each from the default branch the
// one before left: every stage of one starts only once the one before has merged or stopped. At
// most 22 agents a pull request: prepare 1, rebase 1, verify 4 and review 1, two reworks of
// 1 + 4 + 1, push 1, ci 1 and merge 1 (1 + 1 + 5 + 2 × 6 + 3). The helpers below repeat
// implement.js's, as a script can't import.

const MAX_PRS = 5
const MAX_REWORK = 2
// How long the ci stage waits for the code host's checks; its instructions take it from the prompt.
const CI_MINUTES = 60
const named = typeof args === 'string' ? args.split(/\s+/) : args && Array.isArray(args.prs) ? args.prs : []
const tokens = named.map((i) => String(i).trim()).filter(Boolean)

// 42, #42 or …/pull/42; anything else is no pull request.
const numberOf = (t) => {
  const m = /^#?(\d+)$/.exec(t) || /\/pull\/(\d+)\/?(?:[?#].*)?$/.exec(t)
  return m ? Number(m[1]) : null
}
const unknown = tokens.filter((t) => numberOf(t) === null)

// Counted by number: the forms named for one number go to its prepare, which tells another repo's
// URL apart.
const runs = []
for (const t of tokens.filter((x) => numberOf(x) !== null)) {
  const n = numberOf(t)
  const r = runs.find((x) => x.number === n)
  if (r) {
    if (!r.forms.includes(t)) r.forms.push(t)
  } else runs.push({ number: n, forms: [t], prep: null, rebased: null, rounds: [], decisions: [] })
}

const PREPARE_SCHEMA = {
  type: 'object',
  properties: {
    status: {
      type: 'string',
      enum: ['ok', 'closed', 'draft', 'not-default', 'no-ticket', 'merge-method', 'other-repo'],
      description: 'ok, or why prepare stopped, changing nothing',
    },
    reason: { type: 'string', description: 'when not ok: why, with what you found; else empty' },
    number: { type: 'integer', description: 'the pull request\'s number' },
    branch: { type: 'string', description: 'the pull request\'s head branch' },
    head: { type: 'string', description: 'the full sha of the pull request\'s head commit, recorded now; empty when not ok' },
    default_branch: { type: 'string', description: 'the remote\'s default branch' },
    ticket: { type: 'string', description: 'the Ticket: its tracker key or URL, or its file in .about/tickets/; empty when not found' },
    method: { type: 'string', enum: ['merge', 'squash', 'rebase', ''], description: 'the merge method; empty when not ok' },
    worktree: { type: 'string', description: 'the detached worktree\'s absolute path; empty when not ok' },
  },
  required: ['status', 'reason', 'number', 'branch', 'head', 'default_branch', 'ticket', 'method', 'worktree'],
}

const REBASE_SCHEMA = {
  type: 'object',
  properties: {
    outcome: {
      type: 'string',
      enum: ['done', 'needs-decision', 'checks-failed'],
      description: 'done: rebased, and the project\'s checks pass on the last commit; needs-decision: keeping one Ticket\'s intent drops another\'s; checks-failed: they could not pass',
    },
    blocker: { type: 'string', description: 'when not done: why, with the checks\' output; else empty' },
    decisions: {
      type: 'array',
      description: 'needs-decision only: each choice for the person; else empty',
      items: {
        type: 'object',
        properties: {
          question: { type: 'string' },
          files: { type: 'array', items: { type: 'string' } },
          options: { type: 'array', items: { type: 'string' } },
          recommended: { type: 'string', description: 'the option you recommend, and why' },
        },
        required: ['question', 'files', 'options', 'recommended'],
      },
    },
    base: { type: 'string', description: 'the full sha of the default branch\'s tip you rebased onto' },
    head: { type: 'string', description: 'the full sha of the rebased head; empty when not done' },
  },
  required: ['outcome', 'blocker', 'decisions', 'base', 'head'],
}

const REWORK_SCHEMA = {
  type: 'object',
  properties: {
    outcome: {
      type: 'string',
      enum: ['done', 'checks-failed', 'unimplementable'],
      description: 'done: committed, and the project\'s checks pass on the last commit; checks-failed: they could not pass; unimplementable: the findings contradict the Ticket or the code',
    },
    blocker: { type: 'string', description: 'when not done: why, with the checks\' output; else empty' },
    commits: {
      type: 'array',
      items: { type: 'string' },
      description: 'the commits beyond the base after your fixes, `<full sha> <subject>` each, HEAD last',
    },
  },
  required: ['outcome', 'blocker', 'commits'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          at: { type: 'string' },
          what: { type: 'string' },
          // What each field holds is the reviewer's instructions' alone, so the two don't drift.
          bug: { type: 'boolean' },
        },
        required: ['at', 'what', 'bug'],
      },
    },
  },
  required: ['findings'],
}

const PUSH_SCHEMA = {
  type: 'object',
  properties: {
    pushed: { type: 'boolean' },
    head: {
      type: 'string',
      description: 'the full sha of the commit the pull request\'s branch ends at on the remote, after the push; empty when nothing was pushed',
    },
    blocker: { type: 'string', description: 'when not pushed: why, with the error; else empty' },
  },
  required: ['pushed', 'head', 'blocker'],
}

const CI_SCHEMA = {
  type: 'object',
  properties: {
    status: {
      type: 'string',
      enum: ['passed', 'none', 'failed', 'timeout'],
      description: 'passed: every check passed, skipped or neutral; none: the code host reports no check; failed: one failed; timeout: still running when the time your prompt gives ran out',
    },
    check: { type: 'string', description: 'failed or timeout: the check\'s name; else empty' },
    link: { type: 'string', description: 'failed or timeout: the check\'s link; else empty' },
    reason: { type: 'string', description: 'what the code host reported, in a line' },
  },
  required: ['status', 'check', 'link', 'reason'],
}

const MERGE_SCHEMA = {
  type: 'object',
  properties: {
    status: {
      type: 'string',
      enum: ['merged', 'base-moved', 'refused'],
      description: 'merged; base-moved: the default branch\'s tip is no longer the base; refused: the code host refused the merge',
    },
    reason: { type: 'string', description: 'when not merged: why, with the code host\'s message; else empty' },
  },
  required: ['status', 'reason'],
}

const label = (r, stage) => (runs.length > 1 ? `${stage} #${r.number}` : stage)
const end = (r, verdict, reason, extra) => ({
  pr: r.number,
  verdict,
  reason: reason || '',
  ticket: r.prep ? r.prep.ticket : '',
  branch: r.prep ? r.prep.branch : '',
  worktree: r.prep ? r.prep.worktree : '',
  rounds: r.rounds,
  ...extra,
})

// What a failed round failed on, its Verification's and its review's, so two rounds can be told
// the same or not.
const failedOn = (v, bugs) =>
  JSON.stringify([
    ...v.criteria.filter((c) => c.verdict === 'not-met').map((c) => `criterion: ${c.criterion}`),
    ...v.departures.filter((d) => d.blocks).map((d) => `${d.source}: ${d.at} ${d.from}`),
    ...bugs.map((b) => `bug: ${b.at} ${b.what}`),
  ].sort())
const listed = (findings) => findings.map((f) => `- ${f.at} — ${f.what}`)

// A commit the stages name, a full sha or a short one, is another's when either begins the other.
const sameCommit = (a, b) => !!a && !!b && (a.startsWith(b) || b.startsWith(a))

async function prepare(r) {
  r.prep = await agent(
    `Stage: merge-prepare\nPull request: #${r.number}, named as ${r.forms.join(', ')}\n` +
      'Prepare the merge, as your instructions say.',
    { agentType: 'louie:implementer', schema: PREPARE_SCHEMA, label: label(r, 'prepare'), phase: 'Prepare' },
  )
  if (!r.prep) return end(r, 'blocked:tooling', 'the prepare stage returned nothing')
  if (r.prep.status !== 'ok') {
    const why = r.prep.reason
    const status = r.prep.status
    r.prep = null
    return end(r, `blocked:${status}`, why)
  }
  r.where = `the worktree ${r.prep.worktree}, detached; the pull request's branch is ${r.prep.branch}`
  return null
}

async function rebase(r) {
  const p = r.prep
  r.rebased = await agent(
    `Stage: rebase\nPull request: #${r.number}\nTicket: ${p.ticket}\nWork in ${r.where}, its head ${p.head}.\n` +
      `Rebase it onto origin/${p.default_branch} as it is now, as your instructions say.`,
    { agentType: 'louie:implementer', schema: REBASE_SCHEMA, label: label(r, 'rebase'), phase: 'Rebase' },
  )
  const b = r.rebased
  if (!b) return end(r, 'blocked:tooling', 'the rebase stage returned nothing')
  if (b.outcome === 'needs-decision') {
    r.decisions = b.decisions || []
    return end(r, 'blocked:needs-decision', b.blocker || `${r.decisions.length} Open decision(s)`, { decisions: r.decisions })
  }
  if (b.outcome === 'checks-failed') return end(r, 'blocked:checks', b.blocker)
  if (b.outcome !== 'done' || !b.head || !b.base) return end(r, 'blocked:tooling', 'the rebase stage named no base or head')
  // Every change the pull request made is on the default branch already: the person closes it.
  if (sameCommit(b.head, b.base)) return end(r, 'blocked:nothing-to-merge', `nothing is left beyond ${p.default_branch} after the rebase`)
  return null
}

// The Verification and the review, round after round, with up to two reworks; the commit the last
// round passed, or how the pull request ended.
async function verify(r) {
  const p = r.prep
  const base = r.rebased.base
  let head = r.rebased.head
  let findings = ''
  let last = ''
  // A pull request's own commits delete its Ticket's file, so its criteria are read where it is
  // still kept, the default branch (ADR tickets).
  const serving = /^\.about\/(tickets|issues)\//.test(p.ticket)
    ? `serving the Ticket ${p.ticket}, read from the default branch (git show origin/${p.default_branch}:${p.ticket}), as the pull request's commits delete it`
    : `serving the Ticket ${p.ticket}`
  for (let round = 0; ; round++) {
    if (round > 0) {
      const impl = await agent(
        `Stage: rework\nPull request: #${r.number}\nTicket: ${p.ticket}\nWork in ${r.where}, its head ${head}, its base ${base}.\n\n` +
          `The Verification's and the review's findings to fix:\n${findings}`,
        { agentType: 'louie:implementer', schema: REWORK_SCHEMA, label: label(r, `rework ${round}`), phase: 'Rebase' },
      )
      if (!impl) return { stopped: end(r, 'blocked:tooling', 'the rework stage returned nothing') }
      if (impl.outcome === 'checks-failed') return { stopped: end(r, 'blocked:checks', impl.blocker) }
      if (impl.outcome !== 'done') return { stopped: end(r, 'blocked:unimplementable', impl.blocker) }
      if (impl.commits.length) head = String(impl.commits[impl.commits.length - 1]).trim().split(/\s+/)[0]
    }
    const commits = `the commits ${base}..${head} in ${p.worktree} (run git and read files there)`

    // The verify Workflow's error is kept here, as parallel() would drop it.
    const [verified, reviewed] = await parallel([
      async () => {
        try {
          return { value: await workflow('louie:verify', { target: `${commits}, ${serving}` }) }
        } catch (e) {
          return { error: e && e.message ? e.message : String(e) }
        }
      },
      () =>
        agent(`Pull request: #${r.number}\nTicket: ${p.ticket}\nLook for bugs in ${commits}, as your instructions say.`, {
          agentType: 'louie:reviewer',
          schema: REVIEW_SCHEMA,
          label: label(r, round ? `review ${round}` : 'review'),
          phase: 'Rebase',
        }),
    ])
    if (verified && verified.error) return { stopped: end(r, 'blocked:tooling', `the verify Workflow failed: ${verified.error}`) }
    const verification = verified && verified.value
    if (!verification || !verification.verdict) return { stopped: end(r, 'blocked:tooling', 'the verify Workflow returned nothing') }
    if (!reviewed || !Array.isArray(reviewed.findings)) return { stopped: end(r, 'blocked:tooling', 'the review returned nothing') }
    const bugs = reviewed.findings.filter((f) => f.bug)
    r.rounds.push({ mode: round ? 'rework' : 'rebase', head, verdict: verification.verdict, bugs })
    if (verification.verdict === 'pass' && !bugs.length) {
      // The verify Workflow passes a change some verifier returned nothing on, with a criterion it
      // couldn't tell, or with no criterion found (verify.js's words for the first), where
      // implement opens a draft: nothing merges on a Verification that checked less than all of
      // it, and no rework fixes that. A criterion met but untested, or one only the person checks
      // by hand (a not_checked line), doesn't stop it: the person accepted those in marking the
      // pull request ready.
      const missing = (verification.not_checked || []).filter((n) => n.endsWith(': the verifier returned nothing'))
      const criteria = verification.criteria || []
      const untold = criteria.filter((c) => c.verdict === 'not-checked').map((c) => `the criterion "${c.criterion}" not checked: ${c.why}`)
      if (missing.length || untold.length || !criteria.length) {
        const what = [...missing, ...untold, ...(criteria.length ? [] : ['no acceptance criterion found for the Ticket'])]
        return { stopped: end(r, 'blocked:unverified', `the Verification passed with ${what.join('; ')}; not merged`) }
      }
      return { head }
    }

    const report = [verification.report, ...(bugs.length ? ['', 'Bugs the review found:', ...listed(bugs)] : [])].join('\n')
    const now = failedOn(verification, bugs)
    if (round >= MAX_REWORK) return { stopped: end(r, 'failed:rework-budget', report) }
    if (now === last) return { stopped: end(r, 'failed:not-converging', report) }
    last = now
    findings = report
  }
}

async function land(r, head) {
  const p = r.prep
  const base = r.rebased.base
  const pushed = await agent(
    `Stage: force-push\nPull request: #${r.number}\nWork in ${r.where}.\n` +
      `Push its HEAD to the branch ${p.branch} with --force-with-lease=${p.branch}:${p.head}. ` +
      `The commit the last Verification passed: ${head}.`,
    { agentType: 'louie:implementer', schema: PUSH_SCHEMA, label: label(r, 'push'), phase: 'Merge' },
  )
  if (!pushed) return end(r, 'blocked:tooling', 'the push stage returned nothing')
  if (!pushed.pushed) return end(r, 'blocked:push', pushed.blocker)
  // What merges is what was checked: the script doesn't take the stage's word for it.
  if (!sameCommit(pushed.head, head)) {
    return end(r, 'blocked:push-mismatch', `the pushed branch ends at ${pushed.head || 'a commit the push stage didn\'t name'}, not at ${head}, the commit the last Verification passed; not merged`)
  }

  // From here on the full sha the remote reports, which the code host matches the merge against.
  const at = pushed.head
  const ci = await agent(
    `Stage: ci\nPull request: #${r.number}\nWork in ${r.where}.\nIts head: ${at}.\n` +
      `Wait up to ${CI_MINUTES} minutes for its checks on the code host, as your instructions say.`,
    { agentType: 'louie:implementer', schema: CI_SCHEMA, label: label(r, 'ci'), phase: 'Merge' },
  )
  if (!ci) return end(r, 'blocked:tooling', 'the ci stage returned nothing')
  if (ci.status === 'failed') return end(r, 'blocked:ci', `the check ${ci.check} failed: ${ci.link}${ci.reason ? ` — ${ci.reason}` : ''}`)
  if (ci.status === 'timeout') return end(r, 'blocked:ci-timeout', `still running after ${CI_MINUTES} minutes${ci.check ? `: ${ci.check} ${ci.link}` : ''}`)
  if (ci.status !== 'passed' && ci.status !== 'none') return end(r, 'blocked:tooling', `the ci stage reported ${ci.status}`)

  const merged = await agent(
    `Stage: merge\nPull request: #${r.number}\nWork in ${r.where}.\n` +
      `Merge it into ${p.default_branch} by the method ${p.method}, its head ${at}, its base ${base}, as your instructions say.`,
    { agentType: 'louie:implementer', schema: MERGE_SCHEMA, label: label(r, 'merge'), phase: 'Merge' },
  )
  if (!merged) return end(r, 'blocked:tooling', 'the merge stage returned nothing')
  if (merged.status === 'base-moved') return end(r, 'blocked:base-moved', merged.reason || `${p.default_branch} moved since the rebase onto ${base}`)
  if (merged.status !== 'merged') return end(r, 'blocked:merge', merged.reason)
  return end(r, 'done:merged', '', { head: at })
}

async function one(r) {
  const prepared = await prepare(r)
  if (prepared) return prepared
  const rebased = await rebase(r)
  if (rebased) return rebased
  const verified = await verify(r)
  if (verified.stopped) return verified.stopped
  return land(r, verified.head)
}

const nothing = (verdict, reason) => ({ verdict, reason, results: [], decisions: [], report: reason })
if (unknown.length) return nothing('blocked:no-pr', `not a pull request: ${unknown.join(', ')}; name each by its number, #number or URL`)
if (!runs.length) return nothing('blocked:no-pr', 'no pull request named')
if (runs.length > MAX_PRS) return nothing('blocked:too-many', `${runs.length} pull requests named; at most ${MAX_PRS} at once`)

// Strictly one after another: the next starts from the default branch the one before left.
const results = []
for (const r of runs) results.push(await one(r))

const decisions = runs.flatMap((r) => r.decisions.map((d) => ({ pr: r.number, ...d })))
const done = results.filter((x) => x.verdict.startsWith('done:')).length
const verdict = done === results.length ? 'done:all' : done ? 'done:some' : 'blocked:none'

const lines = ['Pull requests:']
results.forEach((x) => lines.push(`- #${x.pr}: ${x.verdict}${x.reason ? ` — ${x.reason}` : ''}`))
if (decisions.length) {
  // The session that gets the report would otherwise file these in the Inbox, as principles.md
  // says of a decision left open (ADR inbox).
  lines.push('', 'Open decisions, to settle before running the pull request again, not for the Inbox:')
  decisions.forEach((d, i) => {
    const files = d.files || []
    const options = d.options || []
    lines.push(`${i + 1}. #${d.pr}: ${d.question}${files.length ? ` (${files.join(', ')})` : ''}`)
    options.forEach((o) => lines.push(`   - ${o}`))
    lines.push(`   Recommended: ${d.recommended}`)
  })
}

return { verdict, reason: '', results, decisions, report: lines.join('\n') }
