# Little Signal Shop: Agreed Project Plan

Last updated November 23, 2026, following feedback on the extended abstract.

Working research title: **RL-Guided Adaptive Tool Selection for Long-Horizon Autonomous E-Commerce Agents**

Course classification: **CPTS 580, Topic B: New Application**

This plan defines the first controlled experiment and the later application roadmap. The [versioned environment specification](contracts/environment-v1.md) gives the settings implemented and tested in Python.

## 1. Main decision

Start with a Python experiment that runs without a graphical interface. Use one product, two paid information tools, and a fixed replenishment rule over a 90-day episode. The existing browser prototype provides a demonstration of the broader application. Expand the business system and connect the research records to the interface after the first controlled comparison.

Keep **Adaptive Tool Selection** as the single primary research direction. Study whether reinforcement learning can improve long-term business outcomes by learning when to gather information, which tool to use, and when to stop investigating.

The shop provides a test of information acquisition under uncertainty and cost. Use an existing reinforcement learning method for the first experiment.

## 2. Engineering scope

The first environment models uncertain daily demand, sales from stock, lost sales, cash, and prepaid replenishment that arrives the next morning. Hold the selling price and unit purchase cost fixed within a run. The broader application can add multiple products, supplier and pricing decisions, competition, launches, promotions, returns, and operating expenses later.

The later application follows the existing **Warehouse Theatre** design, a toy-like packing studio with shelves, a packing desk, a robot manager, incoming supplies, and courier vans. Customers appear through online orders and messages.

The application has three sections.

| Section | Purpose |
| --- | --- |
| Warehouse | Observe or try business decisions and watch picking, packing, dispatch, and replenishment. |
| Research Lab | Configure controlled comparisons, run experiments without warehouse animation, and inspect results. |
| Business Replay | Inspect a recorded day's information, decision rule, costs, and outcomes, then replay its original warehouse sequence. |

Warehouse movements should reflect actual recorded events. Pack only orders that have stock, dispatch the corresponding fulfilled orders, and receive supplies only when their delivery dates arrive. Animated boxes may represent batches, with exact quantities shown in labels.

Pause, speed changes, skipping, and reduced motion affect presentation. They must not change the simulation's financial results. Experiment pause is independent of animation pause. Historical replay must not spend money, sample new outcomes, or change the live store.

The interface starts in **English** and includes a visible **English/Chinese** switch. Switching languages must preserve the current screen, simulation state, settings, records, and playback. A fresh page load starts in English.

## 3. Research question and control boundary

> Can reinforcement learning improve long-term profitability and decision efficiency by learning when and which information-gathering tools to use under uncertain market conditions and information costs?

### First-experiment tools and fixed business policy

Each tool returns a noisy estimate. All controllers start with the same public estimates of today's and tomorrow's demand. Within a day, the result from each tool replaces the corresponding public estimate and expires at the next day's opening. The environment samples demand independently of the controller's actions.

| Tool | Observation returned | Default fee and duration | How the fixed rule uses it |
| --- | --- | --- | --- |
| Same-day market report | Updated estimate of today's demand | $1 and 30 simulated minutes | Updates expected sales today and therefore estimated stock left for tomorrow |
| Next-day demand forecast | Updated estimate of tomorrow's demand | $2 and 60 simulated minutes | Updates the stock target for tomorrow |

The fixed order-up-to rule projects next morning's stock by subtracting expected sales today from current on-hand stock. Expected sales are capped at current stock. The rule orders the positive difference between the next-day demand estimate and projected stock, capped at what the remaining cash can buy. Use nonnegative integer demand estimates and whole units. The same rule and selling price apply in every comparison. A tool provides information and consumes money and time. Replenishment lead time and realized demand follow the environment schedule.

### Decision clock and resumption

1. At 09:00 on days 1–89, post any deliveries due that morning and issue the public observations. The controller chooses a legal tool or `STOP`.
2. A call pays its fee from cash and advances the simulated clock by its full duration. When the result arrives, the controller receives the observation and chooses again. Each tool can be called once per day, for at most two calls. A tool is eligible only if its fee is affordable and it can finish by 10:30. A result arriving at 10:30 is usable. When no tool is eligible, the remaining action is `STOP`.
3. `STOP` is available throughout the decision window. It invokes the fixed replenishment rule once and places any prepaid order for the next morning. The environment then advances to the day's sales and settlement. The controller resumes at 09:00 the next day after deliveries and the new public observations.
4. Day 90 receives due inventory, settles sales, and values remaining stock. The episode ends after settlement. The final day has no tool or procurement decision because both tools inform replenishment for the next morning.

## 4. Learning method and agent architecture

Use an existing lightweight algorithm, provisionally a **Deep Q-Network (DQN)**. The controller's three discrete actions are the market report, the demand forecast, and `STOP`.

The controller observes permitted sales history and public demand estimates, current stock and cash, the results of completed calls, remaining days, the current clock, and the remaining tool budget. The environment keeps actual demand for the current day private until settlement and keeps future market outcomes private. The same observation rules apply to every method.

For controlled training and evaluation, hold the operational business policy fixed. This helps isolate the effect of tool selection. All baselines must use that same business policy.

Python is the reference implementation for the first experiment. Validate it against the written rules and expected transitions. The browser prototype has its own simulation. A later demonstration can use Python episode records and, if useful, a pretrained large language model for explanations.

## 5. Accounting and reward

**Net worth = cash + realistically valued inventory - liabilities.**

The first experiment uses cash purchases and zero liabilities. Prepaid in-transit stock and on-hand stock are valued at acquisition cost during the episode, with a fixed selling price above unit cost. At day 90 settlement, value leftover stock at the lower of acquisition cost and the configured net realizable value. This terminal write-down is applied once.

The reward at each transition is the change in net worth. A tool fee reduces cash once. A prepaid purchase exchanges cash for in-transit inventory at cost, and arrival transfers it to on-hand inventory. Sales increase cash and remove the carrying value of sold stock. The undiscounted sum of rewards equals final net worth minus initial net worth. The first ledger excludes operating and holding costs.

### Worked example

Consider days 89 and 90 of a hypothetical episode. On day 89 at 09:00 the shop has $100 cash, five units in stock valued at $5 each, and no deliveries due. Public demand estimates are zero today and five tomorrow. The selling price is $9. In both branches, realized demand is zero on day 89 and eight on day 90.

| Event | Stop at 09:00 | Buy the next-day forecast, then stop at 10:00 |
| --- | --- | --- |
| Opening net worth | $100 cash + $25 stock = $125 | $100 cash + $25 stock = $125 |
| Decision-time information | Target five and projected stock five | Forecast raises target to eight. Projected stock stays five |
| Day 89 procurement and settlement | Order zero. Net worth stays $125 | Pay the $2 fee and prepay $15 for three units. Net worth is $83 cash + $25 on hand + $15 in transit = $123 |
| Day 90 arrival and sales | Sell five units for $45. Three orders go unfilled | Receive three units and sell eight for $72. Fill all eight orders |
| Final net worth and cumulative reward from day 89 opening | $145 net worth and +$20 reward | $155 net worth and +$30 reward |

The forecast changes the order from zero to three under the same fixed rule. The three extra sales earn $12 in gross margin and the fee costs $2, for a net $10 gain in this example. The tool's reward effect starts at −$2 on day 89. The additional margin arrives on day 90. If the forecast had left the order unchanged on this trajectory, the fee alone would reduce net worth by $2. Check both the decision change and the eventual financial effect when interpreting a tool call.

## 6. Evaluation plan

Compare four tool-selection policies across repeated business episodes.

1. No additional information gathering.
2. Using feasible tools in a fixed order within the shared time, call, and cash constraints.
3. Fixed-rule or uncertainty-threshold tool selection.
4. The learned controller, once implemented and trained.

An LLM-only tool-selection policy is optional if resources permit.

Use multiple training seeds for the learning algorithm and held-out market seeds for evaluation. Match exogenous market conditions across compared policies. Keep the business policy, initial assets, budgets, operating horizon, and accounting rules consistent. Separate training, validation, and evaluation markets.

Measure mean final net worth, information costs and call frequency, unfilled orders, and unsold inventory. Report paired differences and confidence intervals using matched market seeds. To check whether the fixed rule used a tool's information, recompute the order for a recorded decision with that tool's estimate replaced by the public estimate, while keeping the post-fee cash and all other inputs fixed. Vary signal reliability, market volatility, and tool cost in documented sensitivity runs after the main comparison. Bankruptcy metrics can follow an explicit insolvency model.

Market uncertainty and delayed effects make it difficult to attribute 90-day profit to one tool call. Evaluate whole policies and use recorded trajectories for interpretation. Do not assume that the learned controller will outperform well-tuned rules.

The existing lab's three-seed results are generated by the browser's simplified simulation. They demonstrate interface behavior and reproducibility. They are not formal research findings, training curves, or evidence of DQN performance.

## 7. Research Lab and replay requirements

The lab should show experiment settings, run progress, completed-episode counts, business trajectories, and method comparisons. Once training exists, learning progress must be clearly separated from business evaluation trajectories.

Results should link to the underlying recorded episodes. A replay should identify its source policy and market seed, show a selected day, and separate information available at decision time from facts observed afterward.

Record the tool observations, fees, time consumed, operational decisions, inventory transitions, cash movements, demand, fulfilled orders, and deliveries needed to explain an episode. Post hoc market truth is for analysis only.

Replay the recorded receipt rather than re-running the market. Preserve the current shop's state throughout replay. Experiment configuration changes must not silently relabel old results; identify the configuration that actually produced them.

## 8. Current implementation

The Python environment implements the one-product clock, both information tools, the fixed replenishment rule, daily settlement, and versioned episode records. Tests cover full 90-day episodes on identical saved inputs. The [baseline comparison](docs/baseline-v1-results.md) ran three controllers on 24 matched validation markets and selected `uncertainty_threshold` as the primary reference under the [frozen evaluation protocol](contracts/evaluation-v1.md).

The [DQN training](docs/dqn-v1-training.md) and [held-out evaluation](docs/held-out-v1-results.md) are complete. The selected DQN abstained from all tool calls and averaged $47.23 lower final net worth than the primary reference on 64 held-out markets. The report records the paired interval, sensitivity results, and decision traces.

The Research Lab imports the [versioned browser bundle](contracts/browser-bundle-v1.md) from local Python archives. Imported summaries link to the recorded episodes, and Business Replay presents the original settlements while preserving the live warehouse and its history.

The packaged prototype currently includes:

- A standalone browser application with Warehouse, Research Lab, and Business Replay.
- Robot picking and packing, batch transfers, outbound courier dispatch, and due replenishment animations.
- Paid information tools, daily call limits, procurement, stock, delayed deliveries, sales, and financial settlement.
- Three fixed information policies evaluated over matched, reproducible market seeds.
- Configurable forecast reliability, market volatility, tool cost, and seed count.
- Read-only replay of experiment episodes and completed manual store days.
- Separate experiment and animation pause, playback speed, skipping, and reduced motion.
- English by default and an English/Chinese language button.

The prototype stores state and recordings in browser memory. Refreshing starts a fresh session. It does not yet include persistent storage, a backend, a trained DQN, a connected language model, the full returns and promotions system, or validated research experiments.

## 9. Optional future work

Only explore these if the main implementation and evaluation are complete and time permits:

- **Adaptive Strategy Selection:** choosing or switching between higher-level business strategies such as growth, profitability, exploration, and financial survival.
- **Reward Design / Credit Assignment:** investigating how different reward mechanisms help the controller learn from financial effects that appear later.
- **Broader tools and operations:** add supplier, inventory, and pricing analysis when the expanded operating rules can use their outputs.

These are optional extensions, not parallel primary research objectives or promised deliverables. Visual shop growth, customer stories, and cosmetic unlocks are possible game-design additions; they are not implemented commitments.

## 10. Reproduce and demonstrate the first experiment

Use the [experiment and export commands](research/README.md#export-research-records-for-the-browser) to prepare the archive for viewing in the Research Lab and Business Replay.

For the course extended abstract, retain the five-section structure, a maximum of one page of main text, 11-point font, single-column layout, and single spacing. References may occupy a separate page. Describe planned work honestly and do not present simulated UI examples as completed research results.
