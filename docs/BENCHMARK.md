# Known-defect corpus

The versioned [catalog](../src/autotest_skill/assets/benchmark/catalog.json) pairs five seeded defects with clean controls. Each pair runs an identical declared oracle against the healthy and broken fixture. Browser cases use actual Chromium, API cases use real HTTP, and Telegram isolation uses genuine aiogram handlers with a recording transport.

Detection is failed oracle / all catalogued measured defects. Misses, tool errors and blocked defect checks remain in the denominator. Critical detection is also reported separately. False positives are failed clean controls / all measured clean controls; blocked controls are incomplete, never clean passes. Release gate requires all critical seeded cases found and zero confirmed critical/high clean-control findings.

The sample does not measure overall project bug recall. Native and live Telegram checks remain outside these measured cases and visibly unverified. UX observations and source scanner warnings are not silently counted as confirmed bugs. Runs retain case IDs, statuses, elapsed times, revision/fixture fingerprint and current artifacts.
