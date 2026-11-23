# Held-out evaluation results v1

The selected Deep Q-Network (DQN) averaged **$47.23 less final net worth** than the preregistered uncertainty-threshold reference on the 64 held-out markets. The paired 95% bootstrap interval for DQN minus reference was **−$68.63 to −$26.36**. These estimates describe the specified one-product simulator and the checkpoints selected in [Phase 4](dqn-v1-training.md).

## Main comparison

Three baselines and five selected DQN checkpoints used identical market inputs for seeds 3001–3064, giving 512 episodes. Each episode lasted 90 business days. All policies used the same replenishment rule. The five DQN learning seeds were 401–405. The primary comparison used the [frozen two-way resampling procedure](../contracts/evaluation-v1.md#phase-5-held-out-comparison), with 10,000 replicates that resampled both markets and learning seeds while preserving the market pairing. The additional contrasts are descriptive.

| Policy | Episodes | Mean final net worth | Mean tool fees | Mean tool calls | Mean units sold | Mean unfilled units | Mean units remaining |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| No tools | 64 | $2,503.09 | $0.00 | 0.00 | 595.36 | 136.08 | 1.67 |
| Fixed order | 64 | $2,534.16 | $267.00 | 178.00 | 669.42 | 62.02 | 0.77 |
| Uncertainty threshold | 64 | $2,550.33 | $252.33 | 163.47 | 669.80 | 61.64 | 0.77 |
| Selected DQN | 320 | $2,503.09 | $0.00 | 0.00 | 595.36 | 136.08 | 1.67 |

The DQN chose `STOP` at every held-out decision. All five learning seeds returned the same mean paired difference of −$47.23, and all 320 DQN episodes matched the no-tool outcome on their respective markets. Compared with fixed order, the DQN averaged $31.06 lower net worth. Compared with the primary reference, it left 74.44 more units of demand unfilled per episode. The interval reflects differences across markets because the five selected policies made the same decisions here.

## How purchased information affected orders

The threshold reference changed the order quantity in 2,968 of 4,775 market-report calls and 5,165 of 5,687 forecast calls. For each purchase, the audit replaced that one estimate with the public estimate and kept the remaining observations and post-fee cash fixed. In market 3001 on day 1, the purchased forecast raised the demand estimate from 6 to 11 units. The order rose from 6 to 11, and the shop sold all 11 units the following day. With the public estimate it would have had 6 units available. The example establishes the path from forecast to order to next-day sales. The paired comparison estimates the net effect over whole episodes.

## Sensitivity with frozen policies

Each scenario changed one factor and used the same five selected checkpoints. The baseline rule used the scenario's prices for information when scoring calls. The values below are exploratory paired results against the same reference policy, in dollars of final net worth. Each scenario used 64 matched markets and 512 episodes.

| Scenario | DQN minus threshold | 95% paired interval |
| --- | ---: | ---: |
| Forecast error ±1 unit | −$120.38 | [−$141.05, −$100.14] |
| Forecast error ±4 units | +$87.27 | [$64.67, $109.38] |
| Daily regime switch probability 0.10 | −$43.89 | [−$64.69, −$23.02] |
| Daily regime switch probability 0.35 | −$51.92 | [−$71.86, −$32.66] |
| Half tool fees | −$173.39 | [−$194.73, −$152.62] |
| Double tool fees | +$204.69 | [$183.25, $225.72] |

The DQN made zero calls in every sensitivity scenario. Poorer forecast quality and higher fees favored abstention against the same reference rule. Better forecasts and lower fees favored that rule. The sign changes show how the value of buying information depends on its quality and cost here.

## Limits and reproduction

Demand is synthetic, the two estimates have specified noise, and the operating policy, prices, and lead time are fixed for one product. The findings apply to the two tested network configurations, five learning seeds, and fixed validation selection rule. The selected models implemented an abstention policy on these evaluation sets. The study leaves performance under alternative learners and on real markets open.

The local archives are `artifacts/phase4-dqn` and `artifacts/phase5-held-out`. The evaluation archive contains the exact market rows, checkpoint identities, episode ledgers, paired results, tool diagnostics, and sensitivity settings. The primary archive reconciles all 46,080 daily settlements and 67,422 legal decisions, and the primary interval was regenerated from the saved paired rows. A second evaluation loaded the archived main inputs and frozen checkpoints, reproducing all 59 output files byte for byte across the main comparison and all six scenarios. See the [training and replay commands](../research/README.md#train-and-evaluate-the-dqn).
