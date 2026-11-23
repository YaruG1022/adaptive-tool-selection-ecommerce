# Little Signal Shop evaluation protocol v1

Does a Deep Q-Network (DQN) improve 90-day final net worth by choosing when to buy information? The primary comparison runs on held-out markets and uses the baseline with the highest mean final net worth on validation markets. The [environment contract](environment-v1.md) fixes prices, inventory accounting, the common replenishment rule, and the information each policy can use. [The frozen configuration](../research/configs/baselines-v1.json) records the full experiment settings. This document specifies the comparisons and analysis planned before examining the held-out results.

## Matched markets and seed splits

Use environment version `1` and market model `lss-market-v1`. Every controller sees the same opening assets, selling price, decision window, action limits, and accounting. Generate each market's daily demand and potential signals before any controller acts. Match episodes by the exact input rows and `input_id` digest, including when one controller buys a tool the other skips.

| Set | Seeds | Use |
| --- | --- | --- |
| Training markets | 1001-1128 (128) | DQN training in Phase 4 |
| Validation markets | 2001-2024 (24) | Baseline comparison in Phase 3 and DQN selection in Phase 4 |
| Held-out markets | 3001-3064 (64) | Final comparison in Phase 5 |
| Learning seeds | 401, 402, 403, 404, 405 | Independent DQN training runs for every configuration |

The JSON file lists all seeds individually. Keep the held-out markets out of Phase 3 and Phase 4 evaluation and tuning. Save the exact rows evaluated in each split so the evaluation can be restored without relying on regeneration.

## Phase 3 baselines

Implement the following deterministic policies in the listed order. Each has one predeclared candidate and receives the same legal action list as the learned policy. Choose actions from the current observation on each call to the controller.

| Controller ID | Decision rule |
| --- | --- |
| `no_tools` | Choose `STOP` immediately. |
| `fixed_order` | Buy `MARKET_REPORT` when legal, otherwise buy `FORECAST` when legal, otherwise choose `STOP`. |
| `uncertainty_threshold` | Buy the legal tool with the highest strictly positive score defined below. Resolve an equal score in favor of `MARKET_REPORT`. Choose `STOP` if there is no positive score. |

For each legal tool in `uncertainty_threshold`, use the fixed replenishment rule to compute two hypothetical orders. For `MARKET_REPORT`, vary today's estimate from `max(0, public_today - 4)` to `public_today + 4`. For `FORECAST`, vary tomorrow's estimate from `max(0, public_tomorrow - 6)` to `public_tomorrow + 6`. Hold the other estimate at its currently visible value, using its purchased result when present and its public estimate otherwise. Both orders use the same cash after deducting the candidate tool's fee. Use the configured cost and price in the following calculation.

```text
score_cents = (high_order_units - low_order_units)
              * (selling_price_cents - unit_cost_cents)
              - candidate_fee_cents
```

Recompute scores after each observation, with updated cash, estimates, and legal actions. The order spread measures how much the candidate signal could change the decision over the chosen range. It is a fixed threshold heuristic. The range, score, and tie-break are specified before running the comparison, with no fitting or threshold search.

Run all three policies over the 24 validation markets. Rank the policies by mean final net worth. Ties go to the policy listed first. Record the winning baseline ID as the primary reference for the Phase 5 DQN contrast. Record the other comparisons for description. Report validation results as development results.

### Reproduce the validation comparison

Run from the repository root with `research/src` on Python's module search path.

```text
python -B -m little_signal_shop.experiments.baseline_comparison --output artifacts/phase3-baselines
```

The default configuration is `research/configs/baselines-v1.json`. Use `--config PATH` to supply a configuration explicitly and `--inputs PATH` to replay an exported `market_inputs.json`. Use a new output directory for each run. The runner uses only the validation split. Archive the configuration and input bundle used for any comparison reported later.

| Output | Contents |
| --- | --- |
| `config.json` | Exact experiment configuration used for the run. |
| `manifest.json` | Run provenance, versions, split, seeds, and counts. |
| `market_inputs.json` | Exact generated or reloaded validation rows and their identifiers. |
| `episodes.jsonl` | Full episode records, one per line. The registered comparison produces 72 records. |
| `metrics.csv` | One row of outcomes per controller and validation market, 72 rows in the registered comparison. |
| `paired_differences.csv` | All three baseline pairs on each matching market, 72 rows in the registered comparison. Each difference is later-listed baseline minus earlier-listed baseline. |
| `summary.json` | Controller counts and means, and the frozen primary reference. |

## Phase 4 DQN selection

Record each configuration under a fixed candidate ID. Use at most four DQN configurations and train each on all five listed learning seeds, with at most 500 training episodes per run. Predeclare at most ten checkpoint evaluation times per run and use the same times across a candidate's learning seeds. DQN takes only the legal tool actions and `STOP`. Keep the common operational rule and use undiscounted net worth changes for the finite-horizon objective.

At each scheduled checkpoint, evaluate the candidate on all 24 validation markets for each of its five learning seeds. Average final net worth over the complete seed-by-market grid. Select the candidate and checkpoint jointly by the highest aggregate mean. For a tie, choose the earlier checkpoint by the number of completed training episodes, then the candidate ID in ascending order. Save the selected checkpoint for each learning seed and the baseline ID frozen in Phase 3. Preserve settings, training seeds, validation scores, and failed runs. Use the same selected candidate and checkpoint for all held-out comparisons.

## Phase 5 held-out comparison

Run the frozen baselines once per market and each of the five selected DQN checkpoints on all 64 held-out markets. Use deterministic evaluation actions and the same saved market rows in every comparison. The primary outcome is the mean paired difference in final net worth between the DQN and the primary reference baseline.

Define every signed difference as the candidate value minus the reference value within the same market. Each held-out DQN comparison pairs one run for each learning seed with the baseline outcome on that market. Use integer cents for episode accounting and retain numeric precision when taking means.

| Metric | Episode value | Meaning of a positive difference |
| --- | --- | --- |
| Final net worth | Cash plus ending inventory at terminal valuation, in cents | Higher final net worth |
| Tool fees | Sum of fees over tool actions, in cents | More money spent on information |
| Tool calls | Number of completed tool actions | More information calls |
| Unfilled units | Sum of unfilled demand across settlements | More demand left unfilled |
| Remaining units | Ending on-hand stock at terminal settlement | More unsold stock at the horizon |
| Sold units | Sum of fulfilled demand across settlements | More units sold |

Estimate a 95% percentile confidence interval using a paired two-way bootstrap. Use 10,000 replicates with `random.Random(8801)`. In each replicate, sample 64 of the market indices with replacement, then independently sample five of the learning-seed indices with replacement. Use the same sampled markets for both arms. Average the differences over the sampled seed-by-market grid, counting repeated indices each time they occur. The interval uses the 2.5th and 97.5th percentiles of the replicate means. For a percentile `p` on the 0-to-1 scale, linearly interpolate at index `p * (replicates - 1)` in the sorted means. Report the point estimate over the full grid and the mean difference across markets for each learning seed. Report the secondary metrics and additional baseline contrasts descriptively.

If the primary interval includes zero, describe the evidence as inconclusive about the direction of the mean effect in this simulator. Also report the magnitude of the difference, operational outcomes, and limitations of the synthetic demand and signal settings. Link estimates and example decisions to recorded market inputs, controller IDs, and model IDs where applicable. The [environment fixtures](environment-v1.md#deterministic-worked-fixtures) show how to check whether a signal changed the order before assessing whether it covered its cost.

### Sensitivity after the main comparison

Keep the selected models, reference baseline, and decision rules fixed. In separate runs, vary one factor at a time from the registered default. Use paid forecast error ranges of ±1 or ±4 units in place of ±2, daily regime switch probabilities of 0.10 or 0.35 in place of 0.20, and half or twice the default tool fees. Use distinct versioned scenario configurations if these settings are implemented, and match the market rows within each scenario. Report these runs separately and perform no further tuning on their results.
