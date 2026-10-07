# Web verification

Use semantic locators, explicit actions and expected persisted state. `examples/web.yaml` covers login, save, reopen, adaptive layout and automated accessibility. A screenshot is supporting evidence; use the platform image-viewing tool when design/UX judgment matters.

`explore` inventories bounded links, buttons and forms. It follows allowed links but does not submit unknown forms. Use the inventory to identify missing user scenarios; discovered buttons are not automatically proven correct.

Scope intentionally expected HTTP failures by path and status. All unexpected HTTP failures, page exceptions and application console errors remain visible. Browser-generated resource messages are correlated with explicitly expected responses.

Visual checks require an approved PNG and adjacent `.png.json` metadata matching visual_conditions. The tool never updates an approved baseline. Dynamic UI and fonts require controlled conditions. Readable reports distinguish pixel deviations, automated WCAG findings and contextual UX observations.

Screenshots mask password fields and elements marked `data-autotest-sensitive`; use isolated test data. Full browser traces and raw DOM snapshots are not collected by default because they can expose credentials or personal data. Automated accessibility and copy checks do not establish complete accessibility or UX quality.
