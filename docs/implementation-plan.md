# Little Signal Shop: Phased Implementation Plan

Version 0.5 · November 23, 2026

The [project plan](../FINAL_PROJECT_PLAN.md) defines the first experiment following feedback on the extended abstract. Phases 0–5 are complete. The remaining phase connects research records to the game.

## First experiment

Build a headless Python environment for one product, a fixed selling price, and one fixed replenishment policy. The controller chooses the same-day market report, the next-day demand forecast, or stopping. Use 90-day episodes, at most one call per tool per decision day, and a deadline for completing those calls. The first comparison ends with reproducible results and a report.

The broader business system and graphical integration follow the first comparison. The browser prototype has a separate simulation and its own regression cases. Validate the Python environment against the first experiment's written rules, ledger examples, and saved market inputs.

## Phase overview

| Phase | Deliverable | Completion gate | Status |
| --- | --- | --- | --- |
| 0. Preserve the prototype | Private repository, working browser entry point, directory scaffold | Original files and verified behavior retained | Complete |
| 1. Specify the environment | Versioned rules, input model, and record format | Decisions, clock, accounting, randomness, and expected examples are documented | Complete |
| 2. Build and validate the Python environment | Headless environment, fixed business policy, deterministic fixtures | Example ledgers reconcile and transition, timing, and observation checks pass | Complete |
| 3. Run the baseline comparison | Three baseline controllers and reproducible runs | Baselines reproduce from saved inputs and the comparison protocol is frozen | Complete |
| 4. Implement and train DQN | A tool-selection controller using the same environment and business policy | Training smoke checks and multi-seed runs complete without changing comparison rules | Complete |
| 5. Evaluate and report | Held-out comparisons, sensitivity analyses, traceable evidence | Metrics, uncertainty, failures, and limitations can be reproduced | Complete |
| 6. Connect research records to the game | Research Lab results and immutable Business Replay imports | Imported records reconcile with the source runs and replay preserves the live store | Later |

The independent browser prototype remains available while research record integration is pending.

## Phase 0 — Preserve the prototype

Completed foundation:

- Initial commit `04f60443d895cb638a8199e3ae1058d1f945af95` preserves all nine original project files.
- The repository is private; opening root `index.html` directly remains the supported run path.
- Browser verification covered English default, state-preserving bilingual switching, Warehouse, Research Lab, Business Replay, settlement, paused playback, experiment comparisons, and replay isolation.
- This scaffold reserves places for implementation, contracts, tests, scripts, and generated artifacts. Reserved directories do not indicate implemented modules.

Useful characterization anchors for later regression fixtures:

| Scenario | Existing prototype output |
| --- | --- |
| Fresh Warehouse, no tools, settle day 28 | Day 29; cash $4,161; net worth $6,080; inventory [28, 19, 22] |
| Same day receipt | 19 shipped; 0 unfilled; revenue $935; procurement $0; operating/holding charges $34; 18 units received next morning |
| Default lab, seeds 101–103, 90 days | 9/9 complete episodes across three methods |
| No-tools final net worth | Mean $38,627; sample standard deviation $128 |
| Full-budget final net worth | Mean $33,167; sample standard deviation $250 |
| Rule-based final net worth | Mean $35,184; sample standard deviation $291 |

These are rounded prototype regression anchors, not formal research findings. Later fixtures should capture full records and unrounded values. Warehouse starts at day 28 with $3,260 and prepaid incoming inventory; research trials start at day 1 with $5,000 and no incoming orders. Do not compare those initial conditions as if they were the same experiment.

## Phase 1 — Specify the environment

Delivered in [environment v1](../contracts/environment-v1.md) and the [worked fixture](../tests/fixtures/worked-example-v1.json).

Record the [tool and clock rules](../FINAL_PROJECT_PLAN.md#decision-clock-and-resumption) and [worked example](../FINAL_PROJECT_PLAN.md#worked-example) in versioned specifications and fixtures. Resolve the experiment settings before implementing the environment.

1. Specify opening cash and stock, selling price, unit purchase cost, net realizable value at the horizon, demand generation, and units and rounding. Use integer currency units such as cents for accounting.
2. Specify the public demand estimates and both tools' signal models, including noise, calibration, and what the controller observes on completion. Generate independent market and tool-noise inputs from saved seeds or serialized streams so taking more actions leaves future market draws unchanged. Keep realized demand and future outcomes out of decision-time observations.
3. Record the legal actions, the 09:00–10:30 investigation window, and the order of fee, clock advance, result delivery, and `STOP`. Specify how the environment rejects illegal actions without changing state. Include exact-deadline completion, insufficient cash, repeated calls, and the transition to the next decision day.
4. Specify the fixed order-up-to rule, prepaid inventory ledger, terminal valuation, and transition rewards. Use undiscounted finite-horizon return for the first experiment and verify that the sum of transition rewards equals the change in net worth.
5. Define the versioned episode record with the code revision, configuration, seed or input identifiers, controller and model identity, timestamps, observations, actions, fees, purchases, cash and inventory changes, and sales. Keep post-settlement demand in a separate field for analysis.

Phase 1 is complete when the rules yield a unique expected outcome for the worked example, boundary cases, and a small full episode. Include one example per tool in which its signal changes the order quantity while the state, fee, time, and market are held fixed across signal values.

## Phase 2 — Build and validate the Python environment

Delivered in [the Python research package and its tests](../research/README.md). The 90-day checks replay saved market rows and reconcile daily and cumulative rewards across different tool action sequences.

Implement the versioned environment and fixed replenishment rule in `research/src/little_signal_shop/`. Expose a small reset/observe/step interface with legal actions and transition rewards. Settle each operating day once and model day 90 as final delivery, sales, and valuation.

- Verify the worked example and the change in orders caused by each tool's signal. Check no-stock days, cash limits, prepaid stock, delivery dates, and terminal valuation.
- Check both tool orders, exact-cutoff completion, a tool that would overrun the cutoff, exhausted budgets, repeated calls, early `STOP`, and next-day reset. Check that day 90 settles without an extra purchasing decision.
- Run complete episodes on saved market inputs. Verify market draws are shared across policies, observations exclude hidden inputs, and the cash, inventory, and reward ledger reconciles.

Phase 2 is complete when deterministic fixtures and complete-episode checks pass independently of the browser.

## Phase 3 — Run the baseline comparison

Delivered in the [baseline development report](baseline-v1-results.md) and [frozen evaluation protocol](../contracts/evaluation-v1.md). The comparison completed 72 episodes on 24 validation markets and reproduced from the archived market rows. `uncertainty_threshold` is the frozen primary reference.

- Implement immediate `STOP`, a fixed-order controller that uses feasible calls, and a fixed-rule or uncertainty-threshold controller. All share the operational policy, observation interface, daily limits, initial assets, horizon, and accounting. Document the fixed order, thresholds, and tuning budget.
- Store environment and experiment configurations in `research/configs/`. Save separate lists of training, validation/tuning, and held-out evaluation markets, with the input model version.
- Produce per-episode metrics and records, paired results on matched development markets, run metadata, and a command that reproduces a small baseline comparison.

Phase 3 is complete when baseline runs reproduce from saved configurations and inputs. Freeze the comparison protocol before deep Q-network tuning starts.

## Phase 4 — Implement and train the tool-selection DQN

Delivered in the [training and selection report](dqn-v1-training.md). Both settings and all five learning seeds completed training. Validation selected `mlp32` at episode 100 under the registered tie rule.

Use a conventional Deep Q-Network implementation for the two tool actions and `STOP`. The fixed replenishment rule continues to place orders.

- Encode only permitted observations and legal actions. Apply the same action constraints during exploration, greedy action choice, and target calculation.
- Save the network, optimizer, exploration schedule, replay-buffer sampling, target updates, reward scale, training budget, and checkpoint selection in configuration. Use a discount factor of 1 for the fixed 90-day objective so an extra tool action cannot change the discount on later rewards.
- Begin with short smoke runs that verify valid actions, finite losses, terminal handling, checkpoint round trips, and reward accounting. A decreasing training loss alone is not evidence of better business decisions.
- Train across multiple learning seeds. Select settings/checkpoints using validation markets only. Preserve failed runs and record changes instead of tuning against the held-out evaluation markets.

Gate: the training procedure runs reproducibly within the available compute budget, saved controllers reload, and validation behavior is inspectable. No improvement over fixed rules is assumed or required for an honest result. DQN remains labeled unimplemented/untrained until the corresponding milestones actually finish.

## Phase 5 — Evaluate and report

Delivered in the [held-out evaluation report](held-out-v1-results.md). The main comparison includes 512 episodes across 64 markets. The report includes the paired interval, tool-use diagnostics, six sensitivity scenarios, and the reproduction procedure.

Evaluate frozen controllers on held-out markets using the same environment version and matched exogenous conditions. Separate variation across learning seeds from variation across market episodes.

Report final net worth, information charges and call counts, unfilled orders, and remaining inventory. Report paired differences and confidence intervals based on matched markets, seed counts, and the exact comparison configuration. Preserve market pairing when estimating intervals, and account for multiple training seeds. Vary signal reliability, volatility, and tool cost in documented sensitivity runs. Use validation data for tuning.

Keep learning progress separate from 90-day business trajectories. Inspect decision records to see which signals changed orders and whether those changes helped after fees. Check for information leakage, accounting errors, illegal calls, and dependence on one market pattern. Report negative or inconclusive results and simplified assumptions. Save raw episode summaries and run metadata before generating figures or writing conclusions.

Gate: another run can regenerate the comparison tables/figures from saved inputs and checkpoints. Every reported result identifies its environment, configuration, code revision, controller, and seed sets. Any environment correction invalidates and reruns affected comparisons.

## Phase 6 — Connect research records to the game

After the first experiment is reported, add a local import and validation path for exported episode records. Extract browser modules as needed for presentation and playback.

- Validate schema/environment versions and required fields. Identify source controller, market seed/input identifier, and the configuration that produced the result.
- Link Research Lab summaries to the recorded episodes. Separate training curves, evaluation trajectories, and the existing demonstration results.
- Animate recorded receipts without sampling demand, executing decisions, or changing the live store. Retain decision-time information and separately labeled post-hoc truth.
- Preserve the current Warehouse appearance, English default, bilingual state, selected replay day, independent pause controls, speed/skip, and reduced motion.

Gate: imported receipts reconcile with their source runs; replay leaves live cash, stock, incoming orders, fees, history, and day unchanged. Browser regression checks pass. Documentation distinguishes implemented features, trained models, evaluation results, and remaining work.

## Directory map and immediate next work

See [src](../src/README.md), [research](../research/README.md), [contracts](../contracts/README.md), [tests](../tests/README.md), [scripts](../scripts/README.md), and [artifacts](../artifacts/README.md) for ownership. Existing root web files remain active. `.gitkeep` files only retain reserved empty directories in Git.

Phase 6 can use the archived episode records to connect research findings to the existing Research Lab and Business Replay.
