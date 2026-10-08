# Security module

Only run against configured test targets and source roots. HTTP checks cover declared authentication, ownership, invalid-input and session oracles. The header scanner checks exactly `required_headers`; redirects cannot widen the origin allowlist. Do not infer vulnerability from a missing header without deployment context.

`secrets` scans bounded source text and retains rule/file/line only. `gitleaks` checks the working tree with complete redaction, then discards raw output. `dependencies` invokes pip-audit on simple pinned Python dependencies with implicit package resolution disabled. It consults an advisory service and blocks incomplete audits. `semgrep` uses bundled local Python rules, disables metrics and version queries, and withholds source snippets.

Scanner findings are potential issues with applicability notes. API ownership failures are confirmed deviations only when an explicit identity/ownership oracle and current-run response prove them. A clean scan covers its recorded scope; it does not certify security. Blocked scanners, unsupported stacks, Git history, third-party integrations and unreached routes remain unverified.
