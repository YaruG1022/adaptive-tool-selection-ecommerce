# Browser implementation

Reserved for the staged extraction described in [the implementation plan](../docs/implementation-plan.md). These directories contain no extracted runtime code yet. The active application remains root `index.html`, `styles.css`, `i18n.js`, and `app.js`.

| Directory | Intended responsibility |
| --- | --- |
| `simulation/` | DOM-free state transitions, accounting, market inputs, and initialization |
| `tools/` | Information observations, eligibility, fees, and time charges |
| `policies/` | Fixed operational business policy and prototype baseline tool-selection rules |
| `replay/` | Reading immutable episode records and preparing recorded playback |
| `ui/` | Screen rendering, controls, animation, and presentation coordination |

Keep interfaces small and test behavior through them. Rendering, animation timing, and translation must not determine financial outcomes. Avoid duplicate simulation implementations during migration. Root `i18n.js` remains the presentation catalog until a tested extraction needs to change it. Preserve direct local opening and the existing bilingual interface.
