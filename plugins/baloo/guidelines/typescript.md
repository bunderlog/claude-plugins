# TypeScript

For writing TypeScript: the choices where more than one would be reasonable.

## 1. Types at the edge, not casts inside

- Input from outside (JSON, stdin, env, a file) arrives as `unknown` and is narrowed once, at
  the boundary, into a typed value; the code behind it trusts the type.
- No `any`. An `as` sits right after the check that proves it.
- A type-only import says so: `import type { Config }` or `import { type Block, readConfig }`.
- A union of string literals, not an `enum`: `"pre-commit" | "commit-msg"`, or `as const` on
  the list it comes from.
- `null` means "looked, found nothing" (`repoRoot(): string | null`); `?` means "may be left
  out".

**Test:** every `as` sits next to the check that justifies it.

## 2. Functions and data, not classes

- A module exports functions, types and constants. A class only where the language or a library
  wants one: an `Error` subclass, a framework's base class.
- Return an expected failure as data (`string | null` for a reason, a list of problems) and let
  the caller decide; throw only what the caller can't handle. Catch at the entry point, not in
  every function.
- Fixed module-level values in UPPER_CASE (`THRESHOLDS`, `MARKER`), types in PascalCase,
  everything else in camelCase.

**Test:** a function's return type shows every outcome the caller must handle.

## 3. Few dependencies

- Built-ins first, imported with their prefix (`node:fs`). Add a package only for what would
  take more than a page to write well.
- A script or tool with no toolchain of its own runs on `bun`: TypeScript directly, no build
  step, `bun test`. An app keeps the toolchain it has (Vite, Vitest).

**Test:** each dependency does something a page of code couldn't.

## 4. Comments and tests

- A file opens with a comment: what it does, why, and the ADR it follows, if any. A function's
  comment gives what it returns and its edge cases ("or null outside a repo"), not how.
- `<name>.test.ts` sits beside `<name>.ts` and goes through what the module exports; a folder
  or repo a test needs comes from `mkdtempSync`. Run an entry-point script as a process once to
  cover its `main`.

**Test:** every comment says something the code can't.
