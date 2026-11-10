// Runs one of louie's Workflow scripts as Claude Code does, with its agent() and workflow() calls
// answered by the test (PRD delivery): the script's body in an async function, its meta a plain
// constant.
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const WORKFLOWS = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'plugins', 'louie', 'workflows')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

// run('deliver', args, { agent(prompt, opts), workflow(name, args) }) → the script's return value
// and every agent() call it made, as { label, agentType, prompt }.
export async function run(name, args, { agent = () => null, workflow = () => null } = {}) {
  const source = readFileSync(join(WORKFLOWS, `${name}.js`), 'utf8').replace('export const meta', 'const meta')
  const calls = []
  const body = new AsyncFunction('args', 'agent', 'parallel', 'pipeline', 'phase', 'log', 'workflow', source)
  const result = await body(
    args,
    async (prompt, opts = {}) => {
      calls.push({ label: opts.label, agentType: opts.agentType, prompt })
      return agent(prompt, opts)
    },
    async (thunks) => Promise.all(thunks.map((t) => t().catch(() => null))),
    async () => { throw new Error('pipeline is not stubbed') },
    () => {},
    () => {},
    async (wf, wfArgs) => workflow(wf, wfArgs),
  )
  return { result, calls }
}
