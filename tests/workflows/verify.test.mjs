import { test } from 'node:test'
import assert from 'node:assert/strict'
import { run } from './harness.mjs'

const empty = { departures: [], criteria: [], not_checked: [], change: 'main..HEAD: a.py' }

// One verifier per source; a blocking departure or an unmet criterion fails the change, and the
// report names each finding's source and file:line (PRD delivery).
test('verify fails on an ADR departure and an unmet criterion', async () => {
  const { result, calls } = await run('verify', 'main..HEAD', {
    agent: (_, o) =>
      o.label === 'adr'
        ? { ...empty, departures: [{ at: 'a.py:3', what: 'calls B', from: 'ADR ordering', blocks: true }] }
        : o.label === 'criteria'
          ? { ...empty, criteria: [{ criterion: 'c1', at: 'a.py:1', verdict: 'not-met', why: 'no code' }] }
          : empty,
  })
  assert.deepEqual(calls.map((c) => c.label), ['adr', 'glossary', 'guidelines', 'criteria'])
  assert.ok(calls.every((c) => c.agentType === 'louie:verifier'))
  assert.equal(result.verdict, 'fail')
  assert.match(result.report, /\[adr\] a\.py:3 — calls B — ADR ordering \(blocks\)/)
  assert.match(result.report, /not-met: c1 — a\.py:1 — no code/)
})

test('verify passes with nothing found, and names a verifier that returned nothing', async () => {
  const { result } = await run('verify', undefined, { agent: (_, o) => (o.label === 'glossary' ? null : empty) })
  assert.equal(result.verdict, 'pass')
  assert.deepEqual(result.not_checked, ['Glossary: the verifier returned nothing'])
})
