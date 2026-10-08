# Expected outcomes

Use requirements, API contracts, existing assertions or accepted user scenarios. Record both `requirement` and a concrete `oracle` in every check. Prefer observable persisted state and access boundaries over successful transport alone.

For a save flow: submit, reopen, and compare the stored value. For ownership: test two accounts, a denied foreign read and an allowed own read. For a bot: validate dialogue state and side effects, not just reply existence.

For an authenticated interface, assert the relationship between state and guidance: disabled saving before login, enabled saving and updated help after login, and disabled saving with stale private content cleared after logout/expiry. Specify the actual expected copy or state from the product requirement. A generic scan for placeholders cannot establish these transitions. Preserve the failing scenario when proposing a regression; do not replace the expectation with the observed broken behavior.

Inferred UX and visual concerns are observations until reviewed. Compare screenshots only with approved baselines under matching conditions. A generated expectation cannot silently replace a documented product rule.

If the expected behavior is genuinely missing, execute independent checks and explain the missing requirement. Do not invent a passing assertion just to complete a plan.
