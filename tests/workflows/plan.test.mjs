import { test } from 'node:test'
import assert from 'node:assert/strict'
import { run } from './harness.mjs'

const plan = {
  issue: 'x.md: X', criteria: ['c1'], build: 'changes-needed', evidence: '', confidence: 'high',
  confidence_reason: 'found', changes: [{ where: 'a.py', what: 'do', serves: ['c1'] }], decisions: [],
  assumptions: [], tool_failed: false, tool_error: '',
}

// The plan's fields, not its prose, decide how the run ends (PRD delivery).
test('plan ends by the plan\'s fields', async () => {
  for (const [given, want] of [
    [plan, 'ready'],
    [{ ...plan, decisions: [{ question: 'q', options: ['a'], recommended: 'a' }] }, 'needs-decision'],
    [{ ...plan, build: 'nothing-to-build', evidence: 'abc fix' }, 'done:nothing-to-build'],
    [{ ...plan, criteria: [] }, 'blocked:no-criteria'],
    [{ ...plan, confidence: 'low' }, 'blocked:low-confidence'],
    [{ ...plan, tool_failed: true, tool_error: 'gh: 401' }, 'blocked:tooling'],
  ]) {
    const { result } = await run('plan', 'x.md', { agent: () => given })
    assert.equal(result.verdict, want)
  }
  assert.equal((await run('plan', undefined)).result.verdict, 'blocked:no-issue')
})

test('plan works in the worktree it is given', async () => {
  const { calls } = await run('plan', { issue: 'x.md', dir: '/w' }, { agent: () => plan })
  assert.match(calls[0].prompt, /in the worktree \/w/)
  assert.equal(calls[0].agentType, 'louie:planner')
})
