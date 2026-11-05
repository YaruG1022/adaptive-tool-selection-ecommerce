# Verification

Reserved test locations; this scaffold adds no executable tests or test-runner dependencies.

| Directory | Intended checks |
| --- | --- |
| `browser/` | Three screens, English default, state-preserving language changes, settlement, playback controls, and replay isolation |
| `contracts/` | Records and observation schemas, cash/stock/reward invariants, and full-episode JavaScript/Python parity |
| `research/` | Legal actions, observation leakage, fixed-policy baselines, episode termination, and controller training/evaluation smoke checks |
| `fixtures/` | Small versioned inputs, action sequences, receipts, and reference episodes shared by checks |

The initial browser setup was verified against the unchanged prototype. Reproducible reference values are recorded in [Phase 0](../docs/implementation-plan.md#phase-0--preserve-the-prototype); these rounded values are characterization anchors, not a substitute for full fixtures.

Add meaningful tests with each implementation phase. Keep generated reports, browser profiles, screenshots, and large episode dumps in `artifacts/`, not fixtures. Fixtures must be small, intentional, free of credentials, and identify their environment version.
