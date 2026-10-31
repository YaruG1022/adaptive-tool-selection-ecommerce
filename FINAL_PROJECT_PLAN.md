# Little Signal Shop: Agreed Project Plan

Last updated: October 31, 2026

Working research title: **RL-Guided Adaptive Tool Selection for Long-Horizon Autonomous E-Commerce Agents**

Course classification: **CPTS 580, Topic B: New Application**

This document records the decisions made in the project discussion. It distinguishes the intended research system from the working browser prototype. Features described as planned are not completed results or validated design choices.

## 1. Main decision

Build an autonomous agent that operates a simulated online retail business, with a game-like interface that makes its decisions and their consequences visible.

Keep **Adaptive Tool Selection** as the single primary research direction. Study whether reinforcement learning can improve long-term business outcomes by learning when to gather information, which tool to use, and when to stop investigating.

The shop is the experimental environment. The research question concerns information acquisition under uncertainty and cost. The project does not require inventing a new reinforcement learning algorithm or training a large language model.

## 2. Engineering scope

The intended business system covers product procurement and launches, inventory and replenishment, pricing, promotions, orders, returns, cash flow, and operating expenses. The environment should represent uncertain demand, competition, supplier constraints, and market events over a 90-day business episode.

The main visual direction is **Warehouse Theatre**: a warm, toy-like packing studio for an online shop, with shelves, a packing desk, a small robot manager, incoming supplies, and courier vans. Customers appear through online orders and messages.

Three sections share one application:

| Section | Purpose |
| --- | --- |
| Warehouse | Observe or try business decisions and watch picking, packing, dispatch, and replenishment. |
| Research Lab | Configure controlled comparisons, run experiments without warehouse animation, and inspect results. |
| Business Replay | Inspect a recorded day's information, decision rule, costs, and outcomes, then replay its original warehouse sequence. |

Warehouse movements should reflect actual recorded events. Pack only orders that have stock, dispatch the corresponding fulfilled orders, and receive supplies only when their delivery dates arrive. Animated boxes may represent batches, with exact quantities shown in labels.

Pause, speed changes, skipping, and reduced motion affect presentation. They must not change the simulation's financial results. Experiment pause is independent of animation pause. Historical replay must not spend money, sample new outcomes, or change the live store.

The interface starts in **English** and includes a visible **English/Chinese** switch. Switching languages must preserve the current screen, simulation state, settings, records, and playback. A fresh page load starts in English.

## 3. Research question and control boundary

Research question:

> Can reinforcement learning improve long-term profitability and decision efficiency by learning when and which information-gathering tools to use under uncertain market conditions and information costs?

The tool-selection controller gathers information. A separate business policy turns the available information into procurement, pricing, and other operational decisions.

The decision flow is:

1. Observe the information currently available to the agent.
2. Invoke an information tool or stop investigating.
3. Charge the tool's cost and time, and update the available observations.
4. Repeat within the daily tool budget, or stop at the budget limit.
5. Pass the available information to the business policy.
6. Execute operational decisions and settle the simulated business outcomes.

The five information tools are demand forecasting, market research, supplier analysis, inventory analysis, and pricing analysis. Their outputs should be related to market or business conditions but may be noisy, incomplete, or stale. Tools can incur monetary costs and decision delays.

The prototype uses a maximum of two calls per day. The research implementation should make the budget explicit and apply the same budget to all compared methods.

## 4. Learning method and agent architecture

Use an existing lightweight algorithm, provisionally a **Deep Q-Network (DQN)**, for the external tool-selection controller. Its discrete actions are the five tool choices and stopping.

The planned observation includes visible sales and demand indicators, inventory, cash, liabilities where supported, previously acquired information and its age, remaining operating time, and the tool budget. Hidden market truth and future outcomes must not be supplied directly to the policy.

For controlled training and evaluation, hold the operational business policy fixed. This helps isolate the effect of tool selection. All baselines must use that same business policy.

The complete engineering system should support an autonomous, tool-using business agent. A pretrained large language model may assist planning and natural-language explanations during demonstrations. Large language model fine-tuning and repeated paid model calls are not required for large-scale training.

The simulation must run independently of rendering and language-model calls. A lightweight Python environment is the intended research training path. The current JavaScript simulation is a working interface prototype; any later Python implementation must preserve and verify transition, observation, and accounting contracts before results are compared.

## 5. Accounting and reward

Planned net worth:

**Net worth = cash + realistically valued inventory - liabilities.**

The reward should track changes in net worth. Inventory should be valued at the lower of acquisition cost and estimated net realizable value, with appropriate reductions for obsolescence or unsalable goods. Buying stock changes cash or liabilities and inventory; it does not create profit simply because inventory exists.

Record tool charges, operating costs, holding costs, and procurement consistently. A charge already included in the ledger must not be subtracted again as a separate reward penalty.

The prototype currently has cash, prepaid incoming inventory, holding and operating charges, and a simple 20% ending inventory discount. It does not implement the full planned liabilities and net-realizable-value model. That discount is a demonstration assumption, not a validated financial model.

## 6. Evaluation plan

Compare complete tool-selection policies across repeated business episodes. The required baselines are:

1. No additional information gathering.
2. Using available tools whenever the shared budget permits, with an explicit fixed call order.
3. Fixed-rule or uncertainty-threshold tool selection.
4. The learned controller, once implemented and trained.

An LLM-only tool-selection policy is optional if resources permit.

Use multiple training seeds for the learning algorithm and held-out market seeds for evaluation. Match exogenous market conditions across compared policies. Keep the business policy, initial assets, budgets, operating horizon, and accounting rules consistent.

Measure mean final net worth, information costs and call frequency, unfilled orders, unsold inventory, and bankruptcy rate where termination mechanics support it. Report variability and paired comparison uncertainty. Vary forecast reliability, market volatility, and tool cost.

Market uncertainty and delayed effects make it difficult to attribute 90-day profit to one tool call. Evaluate whole policies and use recorded trajectories for interpretation. Do not assume that the learned controller will outperform well-tuned rules.

The existing lab's three-seed results are generated by the browser's simplified simulation. They demonstrate interface behavior and reproducibility. They are not formal research findings, training curves, or evidence of DQN performance.

## 7. Research Lab and replay requirements

The lab should show experiment settings, run progress, completed-episode counts, business trajectories, and method comparisons. Once training exists, learning progress must be clearly separated from business evaluation trajectories.

Results should link to the underlying recorded episodes. A replay should identify its source policy and market seed, show a selected day, and separate information available at decision time from facts observed afterward.

Record the tool observations, fees, time consumed, operational decisions, inventory transitions, cash movements, demand, fulfilled orders, and deliveries needed to explain an episode. Post hoc market truth is for analysis only.

Replay the recorded receipt rather than re-running the market. Preserve the current shop's state throughout replay. Experiment configuration changes must not silently relabel old results; identify the configuration that actually produced them.

## 8. Current implementation

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

These are optional extensions, not parallel primary research objectives or promised deliverables. Visual shop growth, customer stories, and cosmetic unlocks are possible game-design additions; they are not implemented commitments.

## 10. Next implementation steps

1. Preserve the bilingual prototype and this plan in a GitHub repository.
2. Separate the simulation, information tools, business policy, controller interface, and replay records into maintainable modules.
3. Validate accounting, delivery timing, observation boundaries, seed control, and equivalent headless execution.
4. Build the research training environment and implement the DQN controller.
5. Train, evaluate against the baselines on held-out markets, and document limitations and actual results.
6. Connect recorded research episodes to the game interface for demonstrations.

For the course extended abstract, retain the five-section structure, a maximum of one page of main text, 11-point font, single-column layout, and single spacing. References may occupy a separate page. Describe planned work honestly and do not present simulated UI examples as completed research results.
