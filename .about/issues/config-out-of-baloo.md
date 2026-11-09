# baloo works without a Config, one Release per step

2026-11-09

## Symptom

Phase 3 of the move to three plugins (ADR plugin): baloo stops reading and writing a Config and
stops writing Claude Code's settings into a project, while it is still one plugin. Now, because
splitting baloo is cheaper once nothing in it needs a switch: about 1,300 lines exist only to read
the Config and write settings.

## Evidence

- `plugins/baloo/scripts/baloo/config.py` (559 lines), `yaml.py` (440), `settings.py` (320).
- ADR config, ADR checks, ADR guidelines, ADR output-styles and ADR status-line describe the
  switches and the settings session start writes today.
- Guidelines waiting to be read were read 5 times in 79; given by a Hook on the task's signal,
  before the first edit 15 times in 22 (ADR measurement).

## Acceptance criteria

- A PRD for baloo without a Config exists and has no Status line.
- The Checks in Hooks run with no Config key; a key left for them does nothing, and `doctor`
  names it for the person to remove.
- Session start writes no `statusLine` and no `outputStyle` into a project's
  `.claude/settings.local.json`, and says once per clone how to set them in
  `~/.claude/settings.json`.
- Session start puts baloo's always-on Guideline in the context; the other Guidelines are skills,
  and an eval compares how often they reach Claude with 5 in 79 and 15 in 22.
- `config.py` and `yaml.py` are gone; a leftover `.claude/baloo.yml` is named by `doctor` for the
  person to remove, and session start writes nothing into `.claude/`.

## Comments

### 2026-11-09 · order

One Release per criterion after the PRD, in the order above; each leaves baloo working.
