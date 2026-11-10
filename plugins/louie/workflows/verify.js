export const meta = {
  name: 'verify',
  description: 'Verify a change against what the project agreed: its ADRs, glossary, Guidelines, and the acceptance criteria of its Issue or PRD, one verifier for each, and report each departure with file:line. Changes nothing.',
  whenToUse: 'When the user asks to verify or check a change against the project\'s decisions or criteria. Offer it, in a line and once, at the end of a task that serves an Issue or a PRD with acceptance criteria, before its commit or PR, and run it only if the user agrees. Takes a commit range, a branch, a PR, an Issue or a PRD; by default the current branch and the working tree. Not for hunting bugs, which a code review does, or for whether the change works when run, which Claude Code\'s /verify checks.',
  phases: [{ title: 'Verify' }],
}

// args: what the user named, as text (a commit range, a branch, a PR, an Issue or a PRD), or
// { target }; nothing for the current branch and the working tree.
//
// One verifier for each source of what was agreed (PRD delivery), so each reads its source whole
// rather than a quarter of four; the script, not a model, joins their findings and decides.

const target = typeof args === 'string' ? args : (args && args.target) || ''

const SOURCES = [
  { key: 'adr', title: 'ADRs' },
  { key: 'glossary', title: 'Glossary' },
  { key: 'guidelines', title: 'Guidelines' },
  { key: 'criteria', title: 'Acceptance criteria' },
]

const SCHEMA = {
  type: 'object',
  properties: {
    departures: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          at: { type: 'string', description: 'file:line of the change' },
          what: { type: 'string', description: 'what the change does there, one sentence' },
          from: { type: 'string', description: 'what it departs from: ADR <subject>, the glossary\'s <term>, <guideline>.md\'s rule, or the criterion, quoted in a line, with its file:line' },
          blocks: { type: 'boolean', description: 'true when it contradicts a decision, a term\'s meaning or a criterion, so the change shouldn\'t merge as it is; false for what a later edit can fix' },
        },
        required: ['at', 'what', 'from', 'blocks'],
      },
    },
    criteria: {
      type: 'array',
      description: 'the acceptance criteria source only: each criterion the change serves; empty for the other sources',
      items: {
        type: 'object',
        properties: {
          criterion: { type: 'string', description: 'the criterion, quoted in a line' },
          verdict: { type: 'string', enum: ['met-tested', 'met-untested', 'not-met', 'not-checked'] },
          why: { type: 'string', description: 'the test that checks it, or what is missing, one sentence' },
        },
        required: ['criterion', 'verdict', 'why'],
      },
    },
    not_checked: {
      type: 'array',
      items: { type: 'string' },
      description: 'what you could not check by reading, and why, one sentence each; empty when nothing',
    },
    change: { type: 'string', description: 'the change you checked: its range or branch, and its files' },
  },
  required: ['departures', 'criteria', 'not_checked', 'change'],
}

phase('Verify')
const results = await parallel(
  SOURCES.map((s) => () =>
    agent(
      `Source: ${s.title} only. Check the change against this one source, as your instructions' ` +
        `section for it says, and leave the other sources to the other verifiers.\n` +
        `The change: ${target || 'the default, the current branch and the working tree'}.`,
      { agentType: 'louie:verifier', schema: SCHEMA, label: s.key },
    ),
  ),
)

const departures = []
const criteria = []
const notChecked = []
const lines = []
results.forEach((r, i) => {
  const s = SOURCES[i]
  if (!r) {
    notChecked.push(`${s.title}: the verifier returned nothing`)
    return
  }
  r.departures.forEach((d) => departures.push({ ...d, source: s.key }))
  if (s.key === 'criteria') criteria.push(...r.criteria)
  r.not_checked.forEach((n) => notChecked.push(`${s.title}: ${n}`))
  if (!lines.length) lines.push(`Change: ${r.change}`)
})

departures.sort((a, b) => Number(b.blocks) - Number(a.blocks))
const fails = departures.some((d) => d.blocks) || criteria.some((c) => c.verdict === 'not-met')
const verdict = fails ? 'fail' : 'pass'

lines.push('', `Verdict: ${verdict}`, '', 'Departures:')
if (!departures.length) lines.push('- none')
departures.forEach((d) => lines.push(`- ${d.at} — ${d.what} — ${d.from}${d.blocks ? ' (blocks)' : ''}`))
lines.push('', 'Acceptance criteria:')
if (!criteria.length) lines.push('- none found for this change')
criteria.forEach((c) => lines.push(`- ${c.verdict}: ${c.criterion} — ${c.why}`))
if (notChecked.length) {
  lines.push('', 'Not checked:')
  notChecked.forEach((n) => lines.push(`- ${n}`))
}

return { verdict, departures, criteria, not_checked: notChecked, report: lines.join('\n') }
