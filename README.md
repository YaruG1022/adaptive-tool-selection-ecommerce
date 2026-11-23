# Adaptive Tool Selection for E-Commerce Agents

[English](README.md) | [简体中文](README.zh-CN.md)

A research project studying when an autonomous e-commerce agent should acquire information, which tool it should use, and when it should stop investigating under uncertainty and cost.

**Current deliverables:** Little Signal Shop, a standalone browser prototype with an animated warehouse, research workbench, and read-only business replay, and a tested headless Python environment for the first experiment.

**Status:** Phases 1–3 are complete. The Python baseline comparison ran on 24 matched validation markets and froze `uncertainty_threshold` as the primary reference. Deep Q-Network (DQN) training and held-out evaluation follow. The browser comparisons illustrate three fixed policies in the demonstration simulation.

## Research direction

The working research title is *RL-Guided Adaptive Tool Selection for Long-Horizon Autonomous E-Commerce Agents* (CPTS 580, Topic B: New Application).

The first experiment runs in Python with one product, a fixed selling price, and a 90-day horizon. The controller chooses between a same-day market report, a next-day demand forecast, and stopping. All compared methods use the same replenishment rule. The evaluation uses matched markets, multiple training seeds, held-out evaluation markets, and paired confidence intervals. The broader business system and browser integration follow the first comparison.

The [project plan](FINAL_PROJECT_PLAN.md) gives the decision clock and a worked example. The [implementation plan](docs/implementation-plan.md) lists phases and acceptance criteria.

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
2. Build the headless Python environment and check it against deterministic fixtures.
3. Reproduce the three baseline comparisons and freeze the evaluation protocol.
4. Implement and train the DQN tool-selection controller.
5. Evaluate on held-out markets and report uncertainty, failures, and limitations.
6. After the first report, import research episode records into the existing Research Lab and Business Replay.

The prototype and Phases 1–3 are complete. See the [baseline results](docs/baseline-v1-results.md), [frozen evaluation protocol](contracts/evaluation-v1.md), and [Python usage and test guide](research/README.md).

## Repository structure

```text
index.html / styles.css / i18n.js / app.js   Active browser prototype
FINAL_PROJECT_PLAN.md                       Agreed research direction
docs/implementation-plan.md                  Proposed implementation phases
contracts/                                  Research environment and episode record specifications
src/                                        Reserved browser module extraction
research/configs/                           Frozen environment settings and seed splits
research/src/little_signal_shop/             Python environment, fixed policy, and baseline runner
tests/                                      Python verification and deterministic fixtures
scripts/                                    Reserved project commands
artifacts/                                  Ignored generated output; README remains tracked
CODEX_SETUP_INSTRUCTIONS.md                  Historical local/GitHub setup instructions
```

The research environment and its tests use only the Python standard library. The original local checkout may remain named `little-signal-shop` after the GitHub repository rename.

## Verification and limitations

The initial setup was checked for English default, bilingual state preservation, all three screens, one-day settlement, 9/9 default comparison episodes, paused playback, and replay isolation. Those checks characterize the current prototype; they do not validate its economic assumptions. Regression anchors and future test responsibilities are documented in the [implementation plan](docs/implementation-plan.md#phase-0--preserve-the-prototype) and [tests README](tests/README.md).

The repository is private. GitHub Pages is not enabled. `.nojekyll` is retained from the original export and does not enable hosting by itself.

## License

No project license has been selected. The owner should choose a license before distributing the project under an open-source license.
