# Web verification

Use semantic locators, explicit actions and expected persisted state. `examples/web.yaml` covers login, save, reopen, adaptive layout and automated accessibility. A screenshot is supporting evidence; use the platform image-viewing tool when design/UX judgment matters.

Assert transitions, not just the initial page: `expect_enabled`, `expect_disabled`, `expect_visible` and `expect_hidden` evaluate a semantic target. Hidden means hidden or absent; role locators include hidden elements for that assertion. `expect_text` with a stable `test_id` and `value` checks guidance after a state change. Each evaluated assertion records its expected and observed state and status. Sensitive target text is withheld; these are bounded target observations, not full DOM dumps.

For example, before login Save is disabled and guidance asks the user to sign in; after login Save is enabled and guidance says it is ready; after logout or an expired session Save is disabled, stale private items disappear and guidance asks for sign-in again. Use the product's actual requirements and wording rather than assuming every app has the demo's labels. Generic UX observations cannot establish these contextual rules automatically.

`explore` inventories bounded links, buttons and forms. It follows allowed links but does not submit unknown forms. Use the inventory to identify missing user scenarios; discovered buttons are not automatically proven correct.

Scope intentionally expected HTTP failures by path and status. All unexpected HTTP failures, page exceptions and application console errors remain visible. Browser-generated resource messages are correlated with explicitly expected responses.

Visual checks require an approved PNG and adjacent `.png.json` metadata matching visual_conditions. The tool never updates an approved baseline. Dynamic UI and fonts require controlled conditions. Readable reports distinguish pixel deviations, automated WCAG findings and contextual UX observations.

Screenshots mask password fields and elements marked `data-autotest-sensitive`; use isolated test data. Secret-bound UI actions withhold screenshots while preserving the functional pass/fail result and redacted assertion evidence. A declared visual baseline remains blocked when its required screenshot is withheld. Full browser traces and raw DOM snapshots are not collected by default because they can expose credentials or personal data. Automated accessibility and copy checks do not establish complete accessibility or UX quality.

Turn a reproduced failed web run into a regression proposal with `autotest regression --from-run RUN_DIRECTORY --check CHECK_ID --output tests/test_regression.py`. It retains the saved scenario, oracle, provenance, explicit origins and reliably passed web/HTTP prerequisites; unrelated checks and automatic retries are excluded. Start/reset the target separately. Keep credentials in environment bindings; redacted literal inputs and sensitive inline UI values cannot be exported. See docs/CLI.md for replay and supported scope.
