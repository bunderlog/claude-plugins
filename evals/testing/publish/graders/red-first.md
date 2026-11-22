---
type: llm
focus: trace
---

PASS if, in the trace, a run of the tests in `tests/test_posts.py` fails before the edit or write
that adds `publish`'s working code to `src/blog/posts.py`, so a test was seen red before the code
that turns it green.
FAIL if `publish`'s working code was written before any run of those tests failed, or the tests
were never run.
