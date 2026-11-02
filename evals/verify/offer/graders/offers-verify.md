---
type: llm
---

PASS if the reply, after doing the Issue, offers to check the change against what the project
agreed (its ADRs, glossary or the Issue's acceptance criteria) in a separate check or agent, such
as /baloo:verify, without running it: a question such as "Want me to run /baloo:verify before you
commit?" is such an offer.
FAIL if it offers no such check, or ran one without being asked. Running or offering the tests
alone is not such a check.
