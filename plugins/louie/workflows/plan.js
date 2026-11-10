export const meta = {
  name: 'plan',
  description: 'Plan an agreed Issue before it is built: what changes where, which acceptance criterion each change serves, how sure the plan is, and the decisions only the person can make; or nothing to build. Changes nothing.',
  whenToUse: 'When the user asks to plan an Issue, or before /louie:deliver. Takes the Issue: its key or URL in the tracker the project names, or its file in .about/issues/. Not for work with no agreed acceptance criteria, which goes to the interview or prd skill first.',
  phases: [{ title: 'Plan' }],
}

// args: the Issue, as text (a tracker's key or URL, or a file in .about/issues/), or { issue }.
//
// The planner reads and plans; the script decides how the run ends, from the plan's fields, never
// from its prose (PRD delivery). The agent's name repeats louie's names.PLUGIN, as a script can't
// import it.

const issue = typeof args === 'string' ? args : (args && args.issue) || ''

const SCHEMA = {
  type: 'object',
  properties: {
    issue: { type: 'string', description: 'the Issue as you read it: its key or path, and its title' },
    criteria: {
      type: 'array',
      items: { type: 'string' },
      description: 'the Issue\'s acceptance criteria as written, one each; empty when it has none',
    },
    build: {
      type: 'string',
      enum: ['changes-needed', 'nothing-to-build'],
      description: 'nothing-to-build: a commit on the default branch already meets the criteria',
    },
    evidence: { type: 'string', description: 'nothing-to-build: that commit as `<sha> <subject>`; else empty' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    confidence_reason: { type: 'string', description: 'why, in one sentence' },
    changes: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          where: { type: 'string', description: 'the file, or the module for a new one' },
          what: { type: 'string', description: 'what changes there, one or two sentences' },
          serves: { type: 'array', items: { type: 'string' }, description: 'the criteria it serves, each quoted in a line' },
        },
        required: ['where', 'what', 'serves'],
      },
    },
    decisions: {
      type: 'array',
      description: 'the choices only the person can make; empty when the Issue, the ADRs and the code settle every one',
      items: {
        type: 'object',
        properties: {
          question: { type: 'string', description: 'the choice, in one sentence, and why it matters' },
          options: { type: 'array', items: { type: 'string' } },
          recommended: { type: 'string', description: 'the option you recommend, and why, in one sentence' },
        },
        required: ['question', 'options', 'recommended'],
      },
    },
    assumptions: {
      type: 'array',
      items: { type: 'string' },
      description: 'what you assumed and what would change if it is wrong, one sentence each',
    },
    tool_failed: {
      type: 'boolean',
      description: 'true only when a tool you needed (the tracker\'s client, git) still failed after a retry, so the plan lacks what it would have given',
    },
    tool_error: { type: 'string', description: 'tool_failed: the tool and its last error, verbatim; else empty' },
  },
  required: ['issue', 'criteria', 'build', 'evidence', 'confidence', 'confidence_reason', 'changes', 'decisions', 'assumptions', 'tool_failed', 'tool_error'],
}

if (!issue) return { verdict: 'blocked:no-issue', reason: 'no Issue named', report: 'Name the Issue to plan.' }

phase('Plan')
const plan = await agent(
  `Issue: ${issue}\nPlan it, as your instructions say.`,
  { agentType: 'louie:planner', schema: SCHEMA, label: 'plan' },
)
if (!plan) return { verdict: 'blocked:tooling', reason: 'the planner returned nothing', report: '' }

// Only the booleans and enums decide; the text beside them is the reason.
let verdict = 'ready'
let reason = ''
if (plan.tool_failed) [verdict, reason] = ['blocked:tooling', plan.tool_error || 'a tool failed']
else if (plan.build === 'nothing-to-build') [verdict, reason] = ['done:nothing-to-build', plan.evidence]
else if (!plan.criteria.length) [verdict, reason] = ['blocked:no-criteria', 'the Issue has no acceptance criteria']
else if (plan.confidence === 'low') [verdict, reason] = ['blocked:low-confidence', plan.confidence_reason]
else if (plan.decisions.length) [verdict, reason] = ['needs-decision', `${plan.decisions.length} decision(s) for the person`]

const lines = [`Issue: ${plan.issue}`, `Verdict: ${verdict}${reason ? ` — ${reason}` : ''}`]
lines.push(`Confidence: ${plan.confidence} — ${plan.confidence_reason}`)
if (plan.decisions.length) {
  lines.push('', 'Decisions for the person:')
  plan.decisions.forEach((d, i) => {
    lines.push(`${i + 1}. ${d.question}`)
    d.options.forEach((o) => lines.push(`   - ${o}`))
    lines.push(`   Recommended: ${d.recommended}`)
  })
}
if (plan.changes.length) {
  lines.push('', 'Changes:')
  plan.changes.forEach((c) => lines.push(`- ${c.where}: ${c.what} (serves: ${c.serves.join('; ') || 'none'})`))
}
lines.push('', 'Acceptance criteria:')
if (!plan.criteria.length) lines.push('- none')
plan.criteria.forEach((c) => {
  const by = plan.changes.filter((ch) => ch.serves.some((s) => s.includes(c) || c.includes(s)))
  lines.push(`- ${c}${by.length ? '' : ' — no change serves it'}`)
})
if (plan.assumptions.length) {
  lines.push('', 'Assumptions:')
  plan.assumptions.forEach((a) => lines.push(`- ${a}`))
}

return { verdict, reason, plan, report: lines.join('\n') }
