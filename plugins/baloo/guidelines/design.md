# Design

For the shape of code: what a module shows, what it hides, and where its interface sits.

A **module** is anything with an interface: a function, a class, a package, a service. Its
**interface** is all a caller must know to use it: the types, and also the order of calls, the
errors, the limits and the config. A **seam** is where that interface sits: the public boundary
that callers and tests go through.

## 1. Hide more than you show

- A module earns its place by doing a lot behind a small interface: few calls, few parameters,
  few rules to learn.
- Small parts inside are fine; they stay inside. The interface grows only when a caller needs it.
- An interface nearly as big as the code behind it hides nothing: fold the module into its
  callers or its neighbors.

**Test:** a caller can use it correctly after reading only its interface.

## 2. Remove pass-throughs

- Picture the code without the module. If nothing gets harder, inline it; if every caller would
  grow the same logic, keep it.
- Shallow modules that always change together belong behind one interface.

**Test:** each module takes some complexity off its callers.

## 3. Put interfaces where things vary

- Put an interface in front of a dependency once it has two implementations; the real one and a
  test fake count. With one, call it directly.
- Pass dependencies in rather than building them inside. Return results; let the caller apply
  them.

**Test:** every interface in front of a dependency has two implementations.

## 4. Test through the interface

- Tests use the seam callers use. A test that needs private state says the module has the wrong
  shape: change the module, not the test.
- What sits behind the seam decides the test:
  - pure logic: call it;
  - a store with a local stand-in (SQLite, a temp folder): run the stand-in;
  - your own service over the network: an in-memory implementation of its interface;
  - a third party: a fake at the boundary.
- After merging modules, move their tests to the new interface and delete the old ones.

**Test:** reworking what's behind the interface breaks no test.
