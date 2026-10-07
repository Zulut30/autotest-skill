# Adapter contract

An adapter implements `run(check: Check, context: Context) -> CheckResult`. The context owns deadlines, shared counters, in-memory variables, redaction and the private artifact directory. Every network request and interactive action consumes its budget. The adapter preserves the oracle and requirement.

A missing prerequisite raises Blocked. An evaluated mismatch returns failed. A runner implementation error stays error. Results are validated against the versioned contract before persistence. Only trusted code changes extend the registry; configuration and page content cannot name arbitrary modules.
