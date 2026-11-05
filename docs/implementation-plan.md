# Little Signal Shop: Initial Phased Implementation Plan

Version: 0.1 proposal · October 31, 2026

Source of scope: [FINAL_PROJECT_PLAN.md](../FINAL_PROJECT_PLAN.md). That document remains the agreed project direction; this document proposes the implementation order, deliverables, and completion gates. Estimates and algorithm settings are not research results. Only Phase 0 is complete; the remaining phases are proposed.

## Review and recommended scope

The agreed plan has a clear central question: whether a controller can improve long-term business outcomes by learning when and which information tools to use. Keep that controller separate from one fixed operational business policy. The current browser application is a useful reference and demonstration, but it is not yet a research environment or a trained agent.

The first research iteration should use three products, the five specified tools, an explicit two-call daily budget, delayed replenishment, a fixed procurement/pricing policy, and 90-day episodes. Product launches, returns, promotions, a connected language model, strategy selection, and alternative reward studies can follow the first controlled comparison. Their omission from the first iteration must remain visible in the limitations. Decide which accounting features are essential in Phase 1; do not silently describe the prototype's inventory discount as the full planned valuation model.

Two details in the existing implementation need particular attention:

- Supplier analysis currently changes delivery lead time from two days to one. Preserve that behavior when reproducing the prototype, then decide whether research tools reveal supplier information or also change operations. A change requires a new environment version and fresh results.
- The seeded noise uses JavaScript `Math.sin`, and monetary/demand rounding uses JavaScript rules. Equal numeric seeds do not establish JavaScript/Python equivalence. Share serialized exogenous inputs or specify portable randomness and rounding before claiming parity.

## Phase overview

| Phase | Deliverable | Completion gate | Status |
| --- | --- | --- | --- |
| 0. Preserve the prototype | Private repository, working browser entry point, directory scaffold | Original files and verified behavior retained | Complete |
| 1. Specify the environment | Versioned contracts and a small research scope | Accounting, observations, actions, randomness, and termination decisions are explicit | Proposed |
| 2. Extract the JavaScript reference | DOM-free simulation and browser presentation modules | Browser and headless receipts match; original interface still works | Proposed |
| 3. Build Python and the baseline harness | Compatible environment, three baseline controllers, reproducible runs | Episode parity and invariant checks pass; comparison protocol is frozen | Proposed |
| 4. Implement and train DQN | A tool-selection controller using the same environment and business policy | Training smoke checks and multi-seed runs complete without changing comparison rules | Proposed |
| 5. Evaluate and report | Held-out comparisons, sensitivity analyses, traceable evidence | Metrics, uncertainty, failures, and limitations can be reproduced | Proposed |
| 6. Connect research records to the game | Research Lab results and immutable Business Replay imports | Records match their runs; playback never changes the live store | Proposed |

Work proceeds through these gates in order. Calendar estimates should be added after Phase 1 establishes the remaining environment scope and the course deadline. No training framework or dependency versions are selected by this scaffold.

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

Write reviewed specifications in `contracts/` before implementing the Python environment.

1. Define state, product and order identifiers, inventory in transit, information observations and their age, configuration, and the fixed operational business policy.
2. Define the decision clock: a controller selects one of five tools or stops. Specify when the two-call limit settles the day, whether repeated tools are allowed, unaffordable/invalid action handling, time budgets, and which actions remain legal. Stopping must remain available whenever settlement is possible.
3. Define what the controller can observe. Keep decision-time observations separate from internal market truth, future outcomes, and post-hoc replay data. Specify units, normalization, missing-information indicators, and history length.
4. Define cash, inventory valuation, prepaid stock, liabilities if included, fees, operating/holding charges, delivery timing, terminal valuation, and rounding. Choose either an explicitly limited prototype-compatible model or a specified research accounting model. Version any difference.
5. Define reward timing. Net-worth changes across tool decisions and settlement should add to the episode's total net-worth change before discounting. Charge each fee once and apply terminal valuation once. Document the discount/time convention so additional tool actions do not accidentally change the objective.
6. Define a versioned episode record: environment and schema versions, code revision, configuration snapshot, seeds or exogenous inputs, controller/model identity, observations, actions, costs/time, decisions, inventory/cash transitions, receipts, and post-hoc truth in a separate field.
7. Define initial conditions, 90-day completion, and any insolvency rule. Report bankruptcy rate only after a corresponding termination rule exists.
8. Define independent market/tool randomness keyed by episode, day, product, and tool as appropriate. Extra tool calls must not shift subsequent market draws. Decide the supplier-analysis semantics explicitly.

Gate: every item has a written decision and a concrete example. Training inputs cannot access analysis-only fields. Research scope omissions and differences from the prototype are listed. Proposed contracts are not called validated until their checks pass.

## Phase 2 — Extract the JavaScript reference

Use the current `observeTool`, `simulateDay`, `newTrial`, and `applyMethod` functions as starting points. Move behavior in small changes, keeping one authoritative implementation for each behavior rather than leaving a second copy in `app.js`.

- `src/simulation/`: transitions, accounting, market inputs, and episode initialization without DOM or animation dependencies.
- `src/tools/`: information observations, eligibility, fees, and decision delays.
- `src/policies/`: the fixed business policy and prototype baseline decision rules.
- `src/replay/`: record selection and playback preparation from immutable recorded receipts.
- `src/ui/`: Warehouse, Research Lab, and Business Replay presentation and playback coordination.

Keep root `app.js` as the entry point during extraction. Preserve English default, bilingual state, appearance, and direct local opening. Do not switch to module loading that breaks `file://` access; choose and verify loading mechanics when extraction begins. Do not add a framework or build step merely to populate the folders.

Gate: identical state/actions/configuration/exogenous inputs yield identical receipts and next state in headless and browser execution. Cover fees, no-stock days, insufficient cash, in-transit orders, delivery dates, terminal valuation, and replay isolation. Browser regression checks still pass, including language changes during paused playback and research.

## Phase 3 — Build Python and establish baselines

Implement the specified environment in `research/src/little_signal_shop/`. First reproduce the chosen compatibility contract; introduce research changes as a separately identified version rather than silently updating the reference.

- Keep environment execution independent of rendering and language-model calls. Expose a small reset/observe/step interface with documented legal actions, rewards, and termination semantics.
- Run complete episodes against shared reference fixtures, including different tool orders, early stopping, exhausted budgets, cash constraints, replenishments, and day 90. Compare observations, receipts, inventory, cash, and accumulated rewards; use exact integer currency where specified and documented tolerances elsewhere.
- Implement no-tools, fixed-order full-budget, and fixed-rule tool controllers. All use the same operational business policy, observation access, daily budgets, initial assets, horizon, and accounting.
- Store environment and experiment configuration in `research/configs/`. Split training, validation/tuning, and held-out evaluation markets; save actual seed lists and version identifiers. Do not treat the three demonstration seeds as a held-out research set.
- Produce per-episode metrics and records, paired results on matched market inputs, run metadata, and a command/script that reproduces a small baseline comparison. Fix the tuning budget and baseline rules before evaluating the learned controller.

Gate: full-episode parity and accounting/observation tests pass. Baseline runs reproduce from saved configuration and inputs. A frozen evaluation protocol exists before DQN tuning starts. Python will own research execution after the compatibility gate; the browser may consume exported records instead of maintaining a second training engine.

## Phase 4 — Implement and train the tool-selection DQN

Use a conventional Deep Q-Network implementation; selecting a maintained library or a small implementation is a phase-level decision. The controller chooses tools or stopping, not a replacement procurement/pricing policy.

- Encode only permitted observations and legal actions. Apply the same action constraints during exploration, greedy action choice, and target calculation.
- Specify network, optimizer, exploration schedule, replay-buffer sampling, target updates, reward scale, training budget, checkpoint selection, and discount/time convention in saved configuration.
- Begin with short smoke runs that verify valid actions, finite losses, terminal handling, checkpoint round trips, and reward accounting. A decreasing training loss alone is not evidence of better business decisions.
- Train across multiple learning seeds. Select settings/checkpoints using validation markets only. Preserve failed runs and record changes instead of tuning against the held-out evaluation markets.

Gate: the training procedure runs reproducibly within the available compute budget, saved controllers reload, and validation behavior is inspectable. No improvement over fixed rules is assumed or required for an honest result. DQN remains labeled unimplemented/untrained until the corresponding milestones actually finish.

## Phase 5 — Evaluate and report

Evaluate frozen controllers on held-out markets using the same environment version and matched exogenous conditions. Separate variation across learning seeds from variation across market episodes.

Report final net worth, information charges and call counts, unfilled orders, remaining inventory, and bankruptcy only where defined. Include paired differences, uncertainty intervals, seed counts, and the exact comparison configuration. Vary forecast reliability, volatility, and tool cost under a documented protocol; reserve any extra tuning for validation data.

Keep learning progress separate from 90-day business trajectories. Inspect recorded decisions for leakage, accounting exploits, repeated/invalid calls, and excessive dependence on one market pattern. Report negative or inconclusive results and simplified assumptions. Save raw episode summaries and run metadata before generating figures or writing conclusions.

Gate: another run can regenerate the comparison tables/figures from saved inputs and checkpoints. Every reported result identifies its environment, configuration, code revision, controller, and seed sets. Any environment correction invalidates and reruns affected comparisons.

## Phase 6 — Connect research records to the game

Add an import/validation path for exported episode records, initially from local files. A backend and persistent database are not prerequisites.

- Validate schema/environment versions and required fields. Identify source controller, market seed/input identifier, and the configuration that produced the result.
- Link Research Lab summaries to the recorded episodes. Separate training curves, evaluation trajectories, and the existing demonstration results.
- Animate recorded receipts without sampling demand, executing decisions, or changing the live store. Retain decision-time information and separately labeled post-hoc truth.
- Preserve the current Warehouse appearance, English default, bilingual state, selected replay day, independent pause controls, speed/skip, and reduced motion.

Gate: imported receipts reconcile with their source runs; replay leaves live cash, stock, incoming orders, fees, history, and day unchanged. Browser regression checks pass. Documentation distinguishes implemented features, trained models, evaluation results, and remaining work.

## Directory map and immediate next work

See [src](../src/README.md), [research](../research/README.md), [contracts](../contracts/README.md), [tests](../tests/README.md), [scripts](../scripts/README.md), and [artifacts](../artifacts/README.md) for ownership. Existing root web files remain active. `.gitkeep` files only retain reserved empty directories in Git.

The next implementation task is Phase 1: specify a complete worked tool/stop/day-settlement example, the cash/inventory/reward ledger, supplier-analysis semantics, and reproducible exogenous inputs. Then capture characterization fixtures and begin one small JavaScript extraction. Do not implement all future folders at once.
