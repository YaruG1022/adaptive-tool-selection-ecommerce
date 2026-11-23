# Python research environment v1

This contract defines the first Little Signal Shop experiment. One product is sold at a fixed price over an episode of `days` business days. A shared order-up-to policy makes every procurement decision. Controllers choose which paid demand estimates to acquire before the policy orders. The research implementation uses Python 3.10 or newer and the standard library. The standalone browser prototype has its own simulation.

## Configuration and market inputs

`EnvironmentConfig` holds the following defaults. Currency fields are integer cents, stock and demand fields are integer units, and clock fields use minutes after midnight.

| Field | Default |
| --- | ---: |
| `days` | 90 |
| `opening_cash_cents` | 10000 |
| `opening_stock` | 5 |
| `unit_cost_cents` | 500 |
| `selling_price_cents` | 900 |
| `terminal_unit_nrv_cents` | 300 |
| `opening_minute` | 540 |
| `cutoff_minute` | 630 |
| `market_report_fee_cents` | 100 |
| `market_report_minutes` | 30 |
| `forecast_fee_cents` | 200 |
| `forecast_minutes` | 60 |

Quantities and currency are nonnegative, `selling_price_cents > unit_cost_cents > 0`, and tool durations are positive. The decision window satisfies `0 <= opening_minute <= cutoff_minute < 1440`. `days >= 2` permits short deterministic fixtures and ensures at least one decision day.

`DayInput(demand, public_today=0, public_tomorrow=0, market_report=0, forecast=0)` contains five nonnegative integer quantities in the stated order. `MarketInputs(days=tuple[DayInput, ...], seed=None)` holds the immutable inputs for one episode. Supply the rows as a tuple whose length matches the configured horizon. The optional seed is a nonnegative integer. The terminal row uses only `demand`.

`generate_market(config, seed)` samples the complete episode before any controller action. Use a separate `random.Random(f"lss-market-v1:{seed}:{channel}")` stream for each of `regime`, `demand`, `public_today`, `public_tomorrow`, `market_report`, and `forecast`. On day 1, start at the low demand level (5) if the first regime draw satisfies `random() < 0.5`. Otherwise start at the high level (11). At each later day's opening, a regime draw of `random() < 0.20` switches the level. Realized daily demand is the level plus an independent `randint(-3, 3)` draw, clipped at zero.

| Input | Quantity estimated | Uniform integer error |
| --- | --- | --- |
| `public_today` | Realized demand that day | −4 through 4 |
| `public_tomorrow` | Realized demand the following day | −6 through 6 |
| `market_report` | Realized demand that day | −1 through 1 |
| `forecast` | Realized demand the following day | −2 through 2 |

For each estimate, draw its error with `randint` from the specified channel. Clip each estimate at zero and set the four estimate fields on the terminal row to zero. The estimates are correlated with the hidden outcome by construction. This stylized generator gives the experiment information channels of known relative precision. The controller sees the public estimates and any estimates it purchases. Exact demand is kept in the environment and recorded separately for analysis. With the same saved rows, calling, omitting, or reordering tools leaves both realized demand and potential tool results unchanged.

The `input_id` is the lowercase SHA-256 hex digest of the compact ASCII JSON array of day objects. Each object has `demand`, `public_today`, `public_tomorrow`, `market_report`, and `forecast` in that field order. Serialization uses separators `(',', ':')` and no trailing newline. The optional `seed` identifies where the rows came from and is excluded from the digest. Save or regenerate the same rows to pair comparisons.

## Lifecycle, observation and actions

| API | Behavior |
| --- | --- |
| `ShopEnvironment(config, record_transitions=True)` | Constructs an environment for the given configuration. Training may disable recording without changing observations, rewards, or settlement. |
| `reset(inputs) -> Observation` | Starts a fresh episode at the opening of day 1 and clears prior transitions. Opening stock is on hand and opening cash is available. |
| `observe() -> Observation \| None` | Returns the current decision observation, or `None` after the episode ends. |
| `step(action: Action) -> StepResult` | Executes a legal action and returns `observation`, `reward_cents`, and `terminated`. A terminal result has `observation=None`. |

An immutable `Observation` exposes `day`, `clock_minute`, `cash_cents`, `stock`, `public_today`, `public_tomorrow`, `market_report`, `forecast`, `sales_yesterday`, `remaining_days`, `remaining_calls`, and `legal_actions`. Days are one-indexed and `remaining_days` includes the current day. `remaining_calls` is two minus the number of tools used that day. A tool result is `None` until its call completes on that day. `sales_yesterday` is `None` on day 1 and holds the preceding day's fulfilled unit count on subsequent decision days. `legal_actions` is a tuple ordered as `STOP`, `MARKET_REPORT`, `FORECAST`, with ineligible tools omitted. Exact current and future demand and unpurchased paid signals are private.

`Action` is a string enum with `STOP` (`'stop'`), `MARKET_REPORT` (`'market_report'`), and `FORECAST` (`'forecast'`). `STOP` is legal at every decision observation. Each tool is legal if it has yet to be used that day, its fee is affordable, and its result can complete at or before the cutoff. An illegal action raises `ValueError` before any mutation. Calling `observe` or `step` before reset raises `RuntimeError`. Calling `step` after termination also raises `RuntimeError`. Reset can start another episode when needed.

## Daily timing and order rule

1. On days 1 through `days - 1`, post due receipts to on-hand stock before building the observation at `opening_minute`. Public estimates update and both paid results and the daily call count reset.
2. A legal tool action deducts its fee once, advances the clock by the configured duration, and returns the new observation with the completed tool result. Arrival at `cutoff_minute` is valid. When the window permits no more calls, the controller still chooses `STOP`.
3. `STOP` invokes the order-up-to rule once using post-fee cash and the estimates then available. The business prepays its order, which arrives at the next morning's opening. Next, settle the current day's sales in units equal to `min(stock, demand)`. Add sales revenue to cash, remove the sold units from on-hand stock, and count remaining realized demand as unfilled units.
4. Following `STOP`, the controller resumes at the next decision day's opening after receipt posting. When `STOP` occurs on day `days - 1`, that same step also posts the terminal day's receipts, settles its sales, applies ending inventory valuation, and returns a terminal result. The terminal day has neither replenishment decisions nor tool calls.

The same fixed rule uses a purchased estimate if it is present, otherwise its corresponding public estimate. The market report updates today's estimate, which can change projected leftover stock. The demand forecast updates tomorrow's stock target. Evaluate the following quantities at `STOP`.

```text
expected_sales_today = min(stock, selected_today_estimate)
projected_stock = stock - expected_sales_today
requested_order = max(0, selected_tomorrow_estimate - projected_stock)
order_units = min(requested_order, cash_cents // unit_cost_cents)
```

## Accounting and rewards

During the episode, net worth is cash plus both on-hand and prepaid in-transit units valued at `unit_cost_cents`. Prepayment converts cash to an inventory asset, and receipt posting moves that asset into on-hand stock. Each sale adds `selling_price_cents` in cash and removes `unit_cost_cents` in inventory value. The first experiment uses a cash-only ledger with prepaid purchasing and zero liabilities.

At the terminal close, remaining on-hand stock is worth `min(unit_cost_cents, terminal_unit_nrv_cents)` per unit. There is no outstanding order at that point. Apply this valuation once. Costs in v1 are acquisition costs and the tool fees.

Every `reward_cents` is post-step net worth minus pre-step net worth. A tool step therefore rewards the negative of its fee. A `STOP` step includes the applicable operating settlements, inclusive of final sales and terminal valuation when it ends the episode. The undiscounted step rewards sum to `final_net_worth_cents - initial_net_worth_cents`.

## Deterministic worked fixtures

These hand-supplied inputs isolate specific transitions and may use values outside the generator's noise ranges. Run the [worked example](../FINAL_PROJECT_PLAN.md#worked-example) with `days=2` and default values for all other configuration fields. Feed `DayInput(demand=0, public_today=0, public_tomorrow=5, market_report=0, forecast=8)` and `DayInput(demand=8)`. Opening net worth is $125 in both branches. The first day's `STOP` includes both days' settlement.

| Controller actions | Day 1 order | Terminal sales and unfilled demand | Step rewards | Final net worth |
| --- | ---: | --- | --- | ---: |
| `STOP` at 09:00 | 0 | 5 sold, 3 unfilled | +$20 | $145 |
| `FORECAST` at 09:00, `STOP` at 10:00 | 3 | 8 sold, 0 unfilled | −$2, +$32 | $155 |

The forecast changes the order target from five to eight. Cash falls from $100 to $98 on the call and to $83 on prepayment for three units. Net worth after ordering is $83 cash plus $25 on hand plus $15 in transit, or $123. The extra three sales earn $12 in margin, making the cumulative advantage $10 after the $2 fee.

In the same fixture, call `MARKET_REPORT` at 09:00 and then `FORECAST` at 09:30. The latter completes exactly at the 10:30 cutoff and updates the observation. At 10:30, `remaining_calls` is zero and `STOP` is the sole legal action. If the cutoff is instead 10:29, the forecast is ineligible following the market report.

To isolate how information enters the policy, hold the fee, time, public estimates, and realized demand fixed within each of the following pairs. Use the same two-day configuration with both tools' default costs and durations. Change only the one paid signal identified in each row.

| Purchased tool | Fixed day 1 public estimates, day 1 demand and day 2 demand | Lower signal and order | Higher signal and order |
| --- | --- | --- | --- |
| `FORECAST` | 0 today, 5 tomorrow, demands 0 and 8 | Forecast 5, order 0 | Forecast 8, order 3 |
| `MARKET_REPORT` | 0 today, 5 tomorrow, demands 3 and 5 | Report 0, order 0 | Report 3, order 3 |

In the market-report pair, the signal changes projected stock from five to two at equal cash and time. Both pairs can be verified from the respective order quantities without attributing a decision change to differences in fees or elapsed time.

## Episode record

After termination, `episode_record(code_revision, controller_id, model_id=None) -> dict` returns a fresh, detached, JSON-compatible record. It includes the following fields.

| Top-level field | Meaning |
| --- | --- |
| `environment_version`, `schema_version` | Both are the string `"1"`. |
| `config` | Snapshot of `EnvironmentConfig` field names and values. |
| `input_id`, `seed` | The digest of the exogenous inputs and their seed, or `null` for a missing seed. |
| `code_revision`, `controller_id`, `model_id` | Nonblank strings identifying the run. `model_id` is `null` when omitted. |
| `initial_net_worth_cents`, `final_net_worth_cents` | Net worth at opening and after terminal valuation. |
| `transitions` | One entry per successful `step`, in execution order. |
| `analysis_only` | An object containing `daily_demand`, a list of realized integer demands in day order. The demand for day `d` is at index `d - 1`. This information stays outside the controller observation. |

A transition includes `action` as its enum string value, `before` and `after` as copies of the decision observations with `legal_actions` represented by a list of strings, `reward_cents`, ending `net_worth_cents`, `fee_cents`, and `settlements`. The terminal transition has `after=null`. `settlements` is empty for a tool call, has one entry for an ordinary `STOP`, and has two entries for terminal `STOP`. `fee_cents` records the cost charged by that step, with zero for `STOP`. The clock fields in `before` and `after` record the decision observations. Each settlement represents the close of its business day.

| Settlement field | Meaning |
| --- | --- |
| `day`, `received_units`, `opening_stock` | Business day, units received at opening, and on-hand stock after receipt. |
| `ordered_units`, `purchase_cents`, `delivery_day` | Prepaid quantity, the amount paid, and the due day, or `null` if no order was placed. |
| `sold_units`, `unfilled_units`, `revenue_cents` | Demand fulfilled and unfilled, and cash received from sales. |
| `closing_stock`, `in_transit_units`, `cash_cents` | End-of-day on-hand stock, prepaid units still due, and cash balance. |
| `inventory_value_cents`, `terminal_write_down_cents`, `net_worth_cents` | Closing inventory valuation including in-transit stock, the terminal reduction in inventory value (zero at other settlements), and closing net worth. |

Requesting a record before final settlement or from an environment with recording disabled raises `RuntimeError`. Invalid supplied identifiers raise `ValueError` after the episode has ended.
