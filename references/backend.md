# Backend checks

Start with existing repository tests and explicit HTTP scenarios. Use requirements for input validation, roles, ownership, persisted state and repeated/concurrent requests. A declared response schema can be checked with a local OpenAPI file; remote references are blocked.

Use environment bindings or ephemeral captures for authentication. Request bodies in examples contain synthetic fixture credentials only. Never reuse them for a production target.

Prepare independent data and define cleanup through supported test APIs or isolated fixture lifecycles. The bundled demo runs in memory, supports admin-only reset and starts fresh per context. Arbitrary applications need their own authorized reset/seed commands; this adapter does not invent them.

Mutating methods require `allow_mutations: true` and `mutating: true`. Redirects are not followed. Test oracles and actual responses are written to redacted private artifacts. Dependencies propagate blocks and the run continues independent checks.
