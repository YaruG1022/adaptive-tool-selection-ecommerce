# Adaptive Tool Selection for E-Commerce Agents

[English](README.md) | [简体中文](README.zh-CN.md)

A research project studying when an autonomous e-commerce agent should acquire information, which tool it should use, and when it should stop investigating under uncertainty and cost.

**Current deliverables:** Little Signal Shop, a standalone browser prototype with an animated warehouse, research workbench, and read-only business replay, and a tested headless Python environment for the first experiment.

**Status:** Phases 1–6 are complete. The selected Deep Q-Network (DQN) made zero tool calls and averaged $47.23 lower final net worth than `uncertainty_threshold` on 64 held-out markets. Research Lab can import those results and link to the original receipts. See the [held-out report](docs/held-out-v1-results.md) for the uncertainty interval, sensitivity runs, and reproduction commands.

## Research direction

The working research title is *RL-Guided Adaptive Tool Selection for Long-Horizon Autonomous E-Commerce Agents* (CPTS 580, Topic B: New Application).

The first experiment runs in Python with one product, a fixed selling price, and a 90-day horizon. The controller chooses between a same-day market report, a next-day demand forecast, and stopping. All compared methods use the same replenishment rule. The evaluation uses matched markets, multiple training seeds, held-out markets, and paired confidence intervals.

The [project plan](FINAL_PROJECT_PLAN.md) gives the decision clock and a worked example. The [implementation plan](docs/implementation-plan.md) lists phases and acceptance criteria.

## Run the prototype

Open root `index.html` in a current Edge, Chrome, or Firefox browser with the repository directory structure intact. The browser app runs directly from disk without a build step.

The interface starts in English. The header's `中文` / `English` button switches languages without resetting the current screen, store, experiment settings, selected record, or playback. Reloading starts a fresh English session.

Lucide 1.17.0 icons load from a pinned unpkg URL. If the resource is unavailable, icons may be absent; business logic and controls still run.

To view archived research, select **Research Lab → Import research records** and choose the [JSON bundle exported from Python](research/README.md#export-research-records-for-the-browser).

## What works today

| Screen | Implemented behavior |
| --- | --- |
| Warehouse | Paid information tools, a two-call daily budget, procurement, stock, delayed deliveries, sales, settlement, and picking/packing/shipping animations |
| Research Lab | Import local research results and inspect held-out trajectories and validation-at-checkpoint curves. Run the separate browser demonstration with configurable reliability, volatility, cost, and seed count |
| Business Replay | Inspect recorded decisions, paid estimates, cash movements, stockouts, and post-hoc demand from the live shop, demonstration, or imported research. Play the recorded receipts while preserving live state |

Playback supports pause, speed changes, skipping, and reduced motion. Experiment pause is independent of warehouse playback. The manual store starts on day 28; research demonstration episodes run from day 1 through day 90.

The live shop, demonstration, and imported records stay in browser memory and reset on refresh. The browser uses the archived research results for inspection and replay. Returns, promotions, and broader accounting remain future work. The browser demonstration applies its own ending inventory discount.

## Implementation phases

1. Specify environment, observation, action, accounting, reward, randomness, and record contracts.
2. Build the headless Python environment and check it against deterministic fixtures.
3. Reproduce the three baseline comparisons and freeze the evaluation protocol.
4. Implement and train the DQN tool-selection controller.
5. Evaluate on held-out markets and report uncertainty, failures, and limitations.
6. After the first report, import research episode records into the existing Research Lab and Business Replay.

See the [baseline results](docs/baseline-v1-results.md), [training and selection](docs/dqn-v1-training.md), and [Python run and test guide](research/README.md).

## Repository structure

```text
index.html / styles.css / i18n.js / app.js   Active browser prototype
FINAL_PROJECT_PLAN.md                       Agreed research direction
docs/implementation-plan.md                  Proposed implementation phases
contracts/                                  Research environment and episode record specifications
src/                                        Research import validation and presentation
research/configs/                           Frozen environment settings and seed splits
research/src/little_signal_shop/             Python environment, experiments, and browser export
tests/                                      Python, JavaScript, and browser checks
scripts/                                    Reserved project commands
artifacts/                                  Ignored generated output; README remains tracked
CODEX_SETUP_INSTRUCTIONS.md                  Historical local/GitHub setup instructions
```

The environment and fixed baselines use the Python standard library. DQN training, evaluation, and their tests use the dependency in [requirements-dqn.txt](research/requirements-dqn.txt).

## Verification and limitations

The initial setup was checked for English default, bilingual state preservation, all three screens, one-day settlement, 9/9 default comparison episodes, paused playback, and replay isolation. Those checks characterize the current prototype; they do not validate its economic assumptions. Regression anchors and future test responsibilities are documented in the [implementation plan](docs/implementation-plan.md#phase-0--preserve-the-prototype) and [tests README](tests/README.md).

The repository is private. GitHub Pages is not enabled. `.nojekyll` is retained from the original export and does not enable hosting by itself.

## License

No project license has been selected. The owner should choose a license before distributing the project under an open-source license.
