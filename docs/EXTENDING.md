# Add a trusted adapter

An adapter is ordinary reviewed Python code with `run(Check, Context) -> CheckResult`. [Example](../examples/adapters/status_file.py) consumes a typed status artifact produced in the same run. It blocks stale files and zero evaluated checks; it preserves producer failure/error. Source has no dynamic commands or network destinations.

To integrate a new kind, add its strict spec to config.py, add its literal to Check.kind and the SPECS mapping, copy the reviewed module into `src/autotest_skill/adapters`, and add its name to registry.ADAPTERS. These explicit code changes keep configuration and target page content from importing arbitrary modules. The planner/controller need no new kind-specific branches. Add resource/mutation validation where the operation requires it, not in target-rendered content.

Use Context.remaining/consume for deadlines and actions/requests; redact before storing evidence. Each network destination must satisfy the origin policy, paths stay under the declared project or run root, and commands are fixed argv with explicit authorization. Missing tools/permissions raise Blocked. Evaluated oracle mismatches return failed, unknown tool defects remain error. Preserve actual status and executed counts. Do not convert empty/partial work into success.

Contract verification must include a real healthy control, deliberate mismatch, absent prerequisite, budget exhaustion, stale evidence, zero tests and secret propagation where relevant. Review platform/transport scope independently of package installation. Current native scope is Android API26 reference; iOS needs macOS/XCUITest/device access, and desktop apps need platform-specific automation. Neither is advertised as implemented.
