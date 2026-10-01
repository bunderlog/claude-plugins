# Testing

For writing tests and building test-first: tests that pin what the code does, not how. In an
existing codebase, its documented test conventions (where tests live, what they may mock) win.

## 1. Red first

- Write one failing test, run it, and see it fail for the reason you expect. A test you never
  saw fail proves nothing.
- Write only the code that turns it green, then the next test.
- Grow one behavior at a time, the first one end to end. Tests written in bulk ahead of the
  code guess at behavior and freeze a design you don't have yet.
- Tidy the code once it's green, as a step of its own.

**Test:** every test has been seen red.

## 2. Test what callers see

- Go through the public interface. Name the interfaces you'll test at before the first test;
  for new behavior, agree them with the user.
- Name a test after the behavior ("rejects an expired token"), not the function.
- Check results through the interface: read the user back rather than query its table.
- Spend tests where bugs are likely and costly: the main path and the tricky logic.

**Test:** reworking the implementation breaks no test.

## 3. Take expected values from outside the code

- Write the expected value as a literal, a worked example or a line of the spec:
  `toBe("hello-world")`, not the code's own formula again, which passes whatever the code does.
- Where nothing independent exists to check against (config, wiring, glue), run it instead of
  testing it.

**Test:** each test fails when the behavior it names breaks.

## 4. Fake only what you don't own

- Fake the network, the clock, randomness, and a database or filesystem with no local stand-in.
  The project's own code runs for real.
- Assert on outcomes, not on which calls were made or in what order.
- Wrap an external service in one function per operation, so each fake returns one shape.

**Test:** no test fakes a module of the project.
