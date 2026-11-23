# Baseline development results v1

The three fixed controllers ran on the same 24 validation markets, seeds 2001–2024. Each episode lasted 90 business days and used environment v1, market model `lss-market-v1`, and the [frozen settings](../research/configs/baselines-v1.json). The run produced 72 episode records. All results below describe the synthetic validation markets. The 64 held-out markets are reserved for Phase 5.

| Controller | Mean final net worth | Mean tool fees | Mean calls | Mean units sold | Mean unfilled units | Mean units remaining |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| No tools (`no_tools`) | $2,456.17 | $0.00 | 0.0 | 583.67 | 125.96 | 1.75 |
| Fixed order (`fixed_order`) | $2,453.67 | $267.00 | 178.0 | 649.25 | 60.38 | 0.67 |
| Uncertainty threshold (`uncertainty_threshold`) | $2,469.42 | $253.08 | 164.1 | 649.71 | 59.92 | 0.67 |

Each paired difference below subtracts the reference outcome on the same market before averaging across markets.

| Candidate | Reference | Mean difference in final net worth | Mean difference in tool fees | Mean difference in unfilled units |
| --- | --- | ---: | ---: | ---: |
| Fixed order | No tools | −$2.50 | +$267.00 | −65.58 |
| Uncertainty threshold | No tools | +$13.25 | +$253.08 | −66.04 |
| Uncertainty threshold | Fixed order | +$15.75 | −$13.92 | −0.46 |

**Frozen primary reference for Phase 5: `uncertainty_threshold`.** It had the highest validation mean under the [selection rule](../contracts/evaluation-v1.md#phase-3-baselines). It made 13.9 fewer calls per episode than fixed order and had similar fulfillment. These development differences are descriptive. The [held-out protocol](../contracts/evaluation-v1.md#phase-5-held-out-comparison) specifies how to estimate the DQN's paired effect and its uncertainty.

## Reproduction

See the [run and replay commands](../research/README.md#run-the-baseline-comparison). The original local run is under `artifacts/phase3-baselines`, with the exact inputs, episode records, metrics, and all within-market differences. The replay from the archived configuration and market rows produced identical scientific outputs. Both runs used Python 3.12.4. The run manifest records the parent Git revision and the SHA-256 fingerprint of the Python source tree at execution.
