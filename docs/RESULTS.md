# Result semantics

- passed: the stated oracle was evaluated and satisfied.
- failed: the oracle was evaluated and not satisfied; reproduction evidence is attached.
- blocked: a required credential, service or runner is unavailable.
- skipped: intentionally excluded by a documented filter or prerequisite.
- error: the check itself could not execute correctly.
- observation: a reviewable UX or uncertain security concern, not a confirmed defect.

Flakiness is separate metadata: an initial failure followed by a passing retry remains visible. Expected failures and disabled checks remain explicit when imported from existing runners. A run with zero evaluated checks is not readiness evidence. Reports preserve check counts and subprocess exit codes.
