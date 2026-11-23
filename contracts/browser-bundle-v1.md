# Browser research bundle v1

The bundle is a UTF-8 JSON file for local import into the Research Lab. The [export command](../research/README.md#export-research-records-for-the-browser) reads completed Python archives. The maximum file size in the browser is 64 MiB.

| Field | Content |
| --- | --- |
| `format`, `schema_version`, `environment_version` | `little-signal-shop-research`, `1`, and `1` as strings |
| `run` | Source revision, validation or held-out split, scenario ID, primary baseline, and environment settings |
| `episodes` | Controller and optional model and learning seed, market seed and input digest, opening and final net worth, and chronological day records |
| `evaluation` | Archived paired mean, confidence level, and interval for the held-out primary contrast, or `null` |
| `training` | Selected checkpoint and validation results for the matching training archive, or `null` |

Every day holds its original [settlement fields](environment-v1.md#episode-record), opening cash and net worth, the two public estimates, the stop time, each completed call's timing, fee and result, and realized demand. The last day has no investigation. Decision-time estimates and purchased information appear in the replay sidebar. Realized demand appears in its separate post-hoc section.

The exporter reconciles source records with stored market rows, metrics, and summaries. The browser independently checks compatibility, record identity, complete matched-market coverage, the action clock, cash, stock, fees, and terminal valuation before making the bundle available. It computes research tables and mean trajectories from the imported episodes and displays the archived confidence interval for the checked primary contrast. Validation-at-checkpoint curves remain separate from held-out trajectories and the browser demonstration.

Replay reads only the selected archived day and its following morning's receipt, when present. The day starts with the recorded opening stock, animates the recorded shipped units, and shows the next recorded delivery after closing. The live shop keeps a separate state and history.
