# Browser QA

The live FastAPI service was exercised in headless Chrome at desktop and mobile viewports against a
fresh SQLite database.

## Journey

1. Loaded the product at 1440 × 1050 and verified exactly three fictional seeded scenarios.
2. Submitted a whitespace-only region and verified the safe validation state for the expected 422.
3. Corrected the input, created a fictional vision-inference scenario, and verified accelerator,
   monthly-cost, confidence, bottleneck, and missing-evidence rendering from the real engine.
4. Selected two scenarios, sent numeric identifiers to the comparison API, and verified dynamic
   scenario headers and result rows.
5. Downloaded deterministic JSON and Markdown exports for the created scenario.
6. Reloaded at 390 × 844, verified the skip link, and measured document width equal to viewport
   width with no horizontal page overflow.

## Result

- Initial scenarios: 3
- Scenarios after creation: 4
- Expected validation responses: 1
- Unexpected failed responses: 0
- Page exceptions: 0
- Mobile viewport/document width: 390/390 pixels
- Workspace screenshot: `docs/assets/capacity-planner-workspace.png`
- Comparison screenshot: `docs/assets/capacity-planner-comparison.png`

The expected 422 produces Chrome's normal failed-resource console entry; no other console error was
observed in the final run.
