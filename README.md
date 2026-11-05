# Adaptive Tool Selection for E-Commerce Agents

[English](README.md) | [简体中文](README.zh-CN.md)

A research project studying when an autonomous e-commerce agent should acquire information, which tool it should use, and when it should stop investigating under uncertainty and cost.

**Current deliverable:** Little Signal Shop, a standalone browser prototype with an animated warehouse, a research workbench, and read-only business replay. The repository also contains an initial phased implementation plan and a directory scaffold for future research code.

**Status:** Deep Q-Network (DQN) training and the Python research environment are not implemented. The browser comparisons illustrate three fixed policies in a simplified simulation; they are not validated research findings or evidence of learned-agent performance.

## Research direction

The working research title is *RL-Guided Adaptive Tool Selection for Long-Horizon Autonomous E-Commerce Agents* (CPTS 580, Topic B: New Application).

The planned controller selects among demand forecasting, market research, supplier analysis, inventory analysis, pricing analysis, and stopping. A separate, fixed business policy handles procurement and pricing so comparisons can isolate tool selection. The evaluation plan calls for matched market conditions, multiple training seeds, held-out evaluation markets, and explicit information costs.

The [agreed project plan](FINAL_PROJECT_PLAN.md) defines the scope and limitations. The [initial implementation plan](docs/implementation-plan.md) proposes the phases and completion gates.

## Run the prototype

Open root `index.html` in a current Edge, Chrome, or Firefox browser. No package installation, build step, account, or API key is required. Keep `index.html`, `styles.css`, `i18n.js`, and `app.js` together.

The interface starts in English. The header's `中文` / `English` button switches languages without resetting the current screen, store, experiment settings, selected record, or playback. Reloading starts a fresh English session.

Lucide 1.17.0 icons load from a pinned unpkg URL. If the resource is unavailable, icons may be absent; business logic and controls still run.

## What works today

| Screen | Implemented behavior |
| --- | --- |
| Warehouse | Paid information tools, a two-call daily budget, procurement, stock, delayed deliveries, sales, settlement, and picking/packing/shipping animations |
| Research Lab | Compare no tools, full daily tool budget, and a fixed rule over matched market seeds; configure forecast reliability, volatility, tool cost, and seed count |
| Business Replay | Inspect recorded decisions, information, cash movements, stockouts, and post-hoc demand; play the original receipt without changing the live store |

Playback supports pause, speed changes, skipping, and reduced motion. Experiment pause is independent of warehouse playback. The manual store starts on day 28; research demonstration episodes run from day 1 through day 90.

All state and histories live in browser memory and reset on refresh. There is no backend, database, connected large language model (LLM), or saved trained model. Business trajectories are distinct from learning curves. Returns, promotions, and the full planned accounting/valuation model remain future work. The current ending inventory discount is a demonstration assumption.

## Implementation phases

1. Specify environment, observation, action, accounting, reward, randomness, and record contracts.
2. Extract a JavaScript reference simulation while preserving the browser prototype.
3. Build the Python environment, establish cross-language parity, and reproduce baseline comparisons.
4. Implement and train the DQN tool-selection controller.
5. Evaluate on held-out markets and report uncertainty, failures, and limitations.
6. Import research episode records into the existing Research Lab and Business Replay.

Only the prototype preservation and directory scaffold are complete. The remaining phases are proposals; see the [implementation plan](docs/implementation-plan.md) for completion criteria.

## Repository structure

```text
index.html / styles.css / i18n.js / app.js   Active browser prototype
FINAL_PROJECT_PLAN.md                       Agreed research direction
docs/implementation-plan.md                  Proposed implementation phases
contracts/                                  Reserved shared specifications and schemas
src/                                        Reserved browser module extraction
research/configs/                           Reserved research configuration
research/src/little_signal_shop/             Reserved Python environment and controllers
tests/                                      Reserved browser, contract, research, and fixture checks
scripts/                                    Reserved project commands
artifacts/                                  Ignored generated output; README remains tracked
CODEX_SETUP_INSTRUCTIONS.md                  Historical local/GitHub setup instructions
```

Reserved directories contain explanatory READMEs or `.gitkeep` files, not completed implementations. No dependency installation or training command is provided yet. The original local checkout may remain named `little-signal-shop` after the GitHub repository rename.

## Verification and limitations

The initial setup was checked for English default, bilingual state preservation, all three screens, one-day settlement, 9/9 default comparison episodes, paused playback, and replay isolation. Those checks characterize the current prototype; they do not validate its economic assumptions. Regression anchors and future test responsibilities are documented in the [implementation plan](docs/implementation-plan.md#phase-0--preserve-the-prototype) and [tests README](tests/README.md).

The repository is private. GitHub Pages is not enabled. `.nojekyll` is retained from the original export and does not enable hosting by itself.

## License

No project license has been selected. The owner should choose a license before distributing the project under an open-source license.
