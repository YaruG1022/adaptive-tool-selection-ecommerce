# Browser implementation

The [research record integration](../docs/implementation-plan.md#phase-6--connect-research-records-to-the-game) uses `replay/research-records.js` to validate local bundles and `ui/research-panel.js` to render their summaries and charts. Root `index.html` loads both as classic scripts before `app.js` for direct local opening.

| Directory | Intended responsibility |
| --- | --- |
| `simulation/` | DOM-free state transitions, accounting, market inputs, and initialization |
| `tools/` | Information observations, eligibility, fees, and time charges |
| `policies/` | Fixed operational business policy and prototype baseline tool-selection rules |
| `replay/` | Reading immutable episode records and preparing recorded playback |
| `ui/` | Screen rendering, controls, animation, and presentation coordination |

Keep interfaces small and test behavior through them. Rendering, animation timing, and translation must not determine financial outcomes. Avoid duplicate simulation implementations during migration. Root `i18n.js` remains the presentation catalog until a tested extraction needs to change it. Preserve direct local opening and the existing bilingual interface.
