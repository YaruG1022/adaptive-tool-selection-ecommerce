from dataclasses import asdict
import json
from pathlib import Path
import unittest

from little_signal_shop.environment import (
    Action,
    DayInput,
    EnvironmentConfig,
    MarketInputs,
    ShopEnvironment,
    generate_market,
)


class ShopEnvironmentTests(unittest.TestCase):
    def test_paid_forecast_changes_the_order_and_increases_final_net_worth(self):
        fixture_path = Path(__file__).parent / "fixtures" / "worked-example-v1.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        config = EnvironmentConfig(**fixture["config"])
        inputs = MarketInputs(days=tuple(DayInput(**day) for day in fixture["market_days"]))
        outcomes = {}

        for case in fixture["cases"]:
            controller_id = case["controller_id"]
            with self.subTest(controller=controller_id):
                env = ShopEnvironment(config)
                self.assertEqual(env.reset(inputs).public_tomorrow, 5)
                results = [env.step(Action(name)) for name in case["actions"]]

                self.assertEqual([result.reward_cents for result in results], case["rewards_cents"])
                self.assertTrue(results[-1].terminated)
                self.assertIsNone(results[-1].observation)
                self.assertIsNone(env.observe())

                record = env.episode_record("test-revision", controller_id)
                self.assertEqual(record["initial_net_worth_cents"], 12500)
                self.assertEqual(record["final_net_worth_cents"], case["final_net_worth_cents"])
                self.assertEqual(record["input_id"], fixture["input_id"])
                self.assertEqual(record["analysis_only"], {"daily_demand": [0, 8]})
                self.assertEqual([step["action"] for step in record["transitions"]], case["actions"])
                settlements = record["transitions"][-1]["settlements"]
                for receipt_key, fixture_key in (
                    ("cash_cents", "closing_cash_cents"),
                    ("inventory_value_cents", "closing_inventory_value_cents"),
                    ("net_worth_cents", "closing_net_worth_cents"),
                    ("ordered_units", "orders"),
                    ("received_units", "arrivals"),
                    ("sold_units", "sales"),
                    ("unfilled_units", "unfilled"),
                ):
                    self.assertEqual([day[receipt_key] for day in settlements], case[fixture_key])
                outcomes[controller_id] = record["final_net_worth_cents"]

        if len(outcomes) == 2:
            self.assertEqual(outcomes["forecast_then_stop"] - outcomes["no_tools"], 1000)

    def test_both_tool_orders_work_at_inclusive_cutoff_and_reset_next_day(self):
        inputs = MarketInputs(days=(
            DayInput(demand=1, public_today=0, public_tomorrow=5, market_report=1, forecast=8),
            DayInput(demand=6, public_today=7, public_tomorrow=3),
            DayInput(demand=3),
        ))

        settlements = []
        for first, second, first_minute in (
            (Action.MARKET_REPORT, Action.FORECAST, 570),
            (Action.FORECAST, Action.MARKET_REPORT, 600),
        ):
            with self.subTest(first=first):
                env = ShopEnvironment(EnvironmentConfig(days=3))
                opening = env.reset(inputs)
                self.assertEqual((opening.day, opening.clock_minute, opening.remaining_days), (1, 540, 3))
                self.assertEqual(set(opening.legal_actions), set(Action))
                self.assertIsNone(opening.sales_yesterday)

                one_tool = env.step(first).observation
                self.assertEqual((one_tool.clock_minute, one_tool.remaining_calls), (first_minute, 1))
                self.assertEqual(set(one_tool.legal_actions), {Action.STOP, second})
                with self.assertRaises(ValueError):
                    env.step(first)
                self.assertEqual(env.observe(), one_tool)

                two_tools = env.step(second).observation
                self.assertEqual((two_tools.clock_minute, two_tools.remaining_calls), (630, 0))
                self.assertEqual((two_tools.market_report, two_tools.forecast), (1, 8))
                self.assertEqual(two_tools.legal_actions, (Action.STOP,))

                next_day = env.step(Action.STOP).observation
                self.assertEqual((next_day.day, next_day.clock_minute, next_day.remaining_days), (2, 540, 2))
                self.assertEqual((next_day.cash_cents, next_day.stock, next_day.sales_yesterday), (8600, 8, 1))
                self.assertEqual((next_day.public_today, next_day.public_tomorrow), (7, 3))
                self.assertEqual((next_day.market_report, next_day.forecast), (None, None))
                self.assertEqual(next_day.remaining_calls, 2)
                self.assertEqual(set(next_day.legal_actions), set(Action))
                self.assertTrue(env.step(Action.STOP).terminated)

                record = env.episode_record("test-revision", "two_tools")
                settlements.append(record["transitions"][2]["settlements"])
                self.assertEqual(len(record["transitions"]), 4)
        if len(settlements) == 2:
            self.assertEqual(settlements[0], settlements[1])

    def test_second_tool_that_would_overrun_cutoff_is_rejected_without_charging(self):
        env = ShopEnvironment(EnvironmentConfig(days=2, cutoff_minute=629))
        env.reset(MarketInputs(days=(DayInput(demand=0), DayInput(demand=0))))

        before = env.step(Action.MARKET_REPORT).observation
        self.assertEqual((before.clock_minute, before.cash_cents, before.remaining_calls), (570, 9900, 1))
        self.assertEqual(before.legal_actions, (Action.STOP,))
        with self.assertRaises(ValueError):
            env.step(Action.FORECAST)
        self.assertEqual(env.observe(), before)
        self.assertTrue(env.step(Action.STOP).terminated)
        record = env.episode_record("test-revision", "cutoff")
        self.assertEqual([step["fee_cents"] for step in record["transitions"]], [100, 0])

    def test_exactly_affordable_tool_can_run_and_unaffordable_tool_cannot(self):
        config = EnvironmentConfig(days=2, opening_cash_cents=100, opening_stock=0)
        env = ShopEnvironment(config)
        before = env.reset(MarketInputs(days=(DayInput(demand=0), DayInput(demand=0))))
        self.assertEqual(set(before.legal_actions), {Action.STOP, Action.MARKET_REPORT})
        with self.assertRaises(ValueError):
            env.step(Action.FORECAST)
        self.assertEqual(env.observe(), before)

        result = env.step(Action.MARKET_REPORT)
        self.assertEqual(result.reward_cents, -100)
        self.assertEqual(result.observation.cash_cents, 0)
        self.assertEqual(result.observation.legal_actions, (Action.STOP,))
        self.assertTrue(env.step(Action.STOP).terminated)

    def test_prepayment_respects_post_fee_cash_and_leftovers_are_written_down_once(self):
        config = EnvironmentConfig(days=2, opening_cash_cents=1100, opening_stock=1)
        env = ShopEnvironment(config)
        env.reset(MarketInputs(days=(
            DayInput(demand=1, public_today=1, forecast=10),
            DayInput(demand=0),
        )))

        self.assertEqual(env.step(Action.FORECAST).reward_cents, -200)
        self.assertEqual(env.step(Action.STOP).reward_cents, 200)
        record = env.episode_record("test-revision", "cash_floor")
        purchase_day, terminal_day = record["transitions"][-1]["settlements"]

        self.assertEqual(purchase_day["ordered_units"], 1)
        self.assertEqual(purchase_day["purchase_cents"], 500)
        self.assertEqual(purchase_day["delivery_day"], 2)
        self.assertEqual(purchase_day["revenue_cents"], 900)
        self.assertEqual(purchase_day["cash_cents"], 1300)
        self.assertEqual(purchase_day["in_transit_units"], 1)
        self.assertEqual(purchase_day["net_worth_cents"], 1800)
        self.assertEqual(purchase_day["terminal_write_down_cents"], 0)
        self.assertEqual(terminal_day["received_units"], 1)
        self.assertEqual(terminal_day["ordered_units"], 0)
        self.assertIsNone(terminal_day["delivery_day"])
        self.assertEqual(terminal_day["closing_stock"], 1)
        self.assertEqual(terminal_day["in_transit_units"], 0)
        self.assertEqual(terminal_day["inventory_value_cents"], 300)
        self.assertEqual(terminal_day["terminal_write_down_cents"], 200)
        self.assertEqual(record["final_net_worth_cents"], 1600)

    def test_terminal_inventory_valuation_is_capped_at_acquisition_cost(self):
        env = ShopEnvironment(EnvironmentConfig(days=2, terminal_unit_nrv_cents=850))
        env.reset(MarketInputs(days=(DayInput(demand=0), DayInput(demand=0, public_tomorrow=100))))
        self.assertEqual(env.step(Action.STOP).reward_cents, 0)
        record = env.episode_record("test-revision", "cost_cap")
        terminal = record["transitions"][-1]["settlements"][-1]
        self.assertEqual((terminal["inventory_value_cents"], terminal["terminal_write_down_cents"]), (2500, 0))
        self.assertEqual(terminal["ordered_units"], 0)

    def test_paid_signals_change_orders_at_the_same_cash_and_time(self):
        cases = (
            (Action.FORECAST, DayInput(demand=0, public_tomorrow=5, forecast=5),
             DayInput(demand=0, public_tomorrow=5, forecast=8), DayInput(demand=8), 9800, 600),
            (Action.MARKET_REPORT, DayInput(demand=3, public_tomorrow=5, market_report=0),
             DayInput(demand=3, public_tomorrow=5, market_report=3), DayInput(demand=5), 9900, 570),
        )
        for action, low_signal, high_signal, terminal, post_fee_cash, minute in cases:
            with self.subTest(action=action):
                orders = []
                for opening_day in (low_signal, high_signal):
                    env = ShopEnvironment(EnvironmentConfig(days=2))
                    env.reset(MarketInputs(days=(opening_day, terminal)))
                    after_call = env.step(action).observation
                    self.assertEqual((after_call.cash_cents, after_call.clock_minute), (post_fee_cash, minute))
                    env.step(Action.STOP)
                    record = env.episode_record("test-revision", action.value)
                    orders.append(record["transitions"][-1]["settlements"][0]["ordered_units"])
                self.assertEqual(orders, [0, 3])

    def test_realized_demand_and_uncalled_tools_are_unavailable_in_observations(self):
        env = ShopEnvironment(EnvironmentConfig(days=2))
        low = DayInput(demand=0, public_today=1, public_tomorrow=6, market_report=1, forecast=7)
        high = DayInput(demand=12, public_today=1, public_tomorrow=6, market_report=9, forecast=7)

        opening = env.reset(MarketInputs(days=(low, DayInput(demand=8))))
        bought_forecast = env.step(Action.FORECAST).observation
        self.assertEqual((opening.market_report, opening.forecast), (None, None))
        self.assertEqual((bought_forecast.market_report, bought_forecast.forecast), (None, 7))
        self.assertEqual(env.reset(MarketInputs(days=(high, DayInput(demand=10)))), opening)
        self.assertEqual(env.step(Action.FORECAST).observation, bought_forecast)

        env.step(Action.STOP)
        record = env.episode_record("test-revision", "forecast")
        self.assertEqual(record["analysis_only"]["daily_demand"], [12, 10])
        for step in record["transitions"]:
            for observation in (step["before"], step["after"]):
                if observation is not None:
                    self.assertEqual(set(observation), set(asdict(opening)))
                    self.assertNotIn("demand", observation)
                    self.assertIsNone(observation["market_report"])

    def test_lifecycle_requires_reset_and_export_requires_completion(self):
        env = ShopEnvironment(EnvironmentConfig(days=2))
        with self.assertRaises(RuntimeError):
            env.observe()
        with self.assertRaises(RuntimeError):
            env.step(Action.STOP)
        with self.assertRaises(RuntimeError):
            env.episode_record("test-revision", "stop")

        inputs = MarketInputs(days=(DayInput(demand=1), DayInput(demand=2)))
        opening = env.reset(inputs)
        with self.assertRaises(RuntimeError):
            env.episode_record("test-revision", "stop")
        self.assertTrue(env.step(Action.STOP).terminated)
        self.assertIsNone(env.observe())
        with self.assertRaises(RuntimeError):
            env.step(Action.STOP)
        first_run = env.episode_record("test-revision", "stop")

        self.assertEqual(env.reset(inputs), opening)
        env.step(Action.STOP)
        self.assertEqual(env.episode_record("test-revision", "stop"), first_run)

    def test_saved_market_rows_reproduce_a_90_day_episode_and_match_across_policies(self):
        config = EnvironmentConfig()
        original = generate_market(config, seed=91)
        self.assertEqual(generate_market(config, seed=91), original)
        self.assertNotEqual(generate_market(config, seed=92).days, original.days)
        serialized = json.loads(json.dumps(asdict(original)))
        reloaded = MarketInputs(
            days=tuple(DayInput(**day) for day in serialized["days"]),
            seed=serialized["seed"],
        )

        def run(inputs, controller_id, daily_tools):
            env = ShopEnvironment(config)
            observation = env.reset(inputs)
            for day in range(1, 90):
                self.assertEqual(observation.day, day)
                for tool in daily_tools:
                    if tool in observation.legal_actions:
                        tool_result = env.step(tool)
                        self.assertFalse(tool_result.terminated)
                        observation = tool_result.observation
                stop_result = env.step(Action.STOP)
                self.assertEqual(stop_result.terminated, day == 89)
                observation = stop_result.observation
            self.assertIsNone(observation)
            return env.episode_record("test-revision", controller_id, "model-identity")

        stop_record = run(original, "stop", ())
        self.assertEqual(run(reloaded, "stop", ()), stop_record)
        two_tools = run(reloaded, "two_tools", (Action.MARKET_REPORT, Action.FORECAST))
        seedless = MarketInputs(days=reloaded.days)
        self.assertEqual(run(seedless, "stop", ())["input_id"], stop_record["input_id"])
        self.assertEqual(two_tools["input_id"], stop_record["input_id"])
        self.assertEqual(two_tools["analysis_only"], stop_record["analysis_only"])

        for record in (stop_record, two_tools):
            with self.subTest(controller=record["controller_id"]):
                self.assertEqual(record["environment_version"], "1")
                self.assertEqual(record["schema_version"], "1")
                self.assertEqual(record["code_revision"], "test-revision")
                self.assertEqual(record["model_id"], "model-identity")
                self.assertEqual(record["seed"], 91)
                self.assertEqual(record["config"], asdict(config))
                self.assertEqual(json.loads(json.dumps(record)), record)

                settlements = [day for step in record["transitions"] for day in step["settlements"]]
                self.assertEqual([day["day"] for day in settlements], list(range(1, 91)))
                self.assertEqual([day["sold_units"] + day["unfilled_units"] for day in settlements],
                                 record["analysis_only"]["daily_demand"])
                self.assertEqual([day["received_units"] for day in settlements[1:]],
                                 [day["ordered_units"] for day in settlements[:-1]])
                self.assertTrue(all(day["cash_cents"] >= 0 for day in settlements))
                self.assertEqual(settlements[-1]["ordered_units"], 0)
                self.assertIsNone(record["transitions"][-1]["after"])
                self.assertEqual(sum(step["reward_cents"] for step in record["transitions"]),
                                 record["final_net_worth_cents"] - record["initial_net_worth_cents"])

                total_sold = sum(day["sold_units"] for day in settlements)
                gross_margin = total_sold * (config.selling_price_cents - config.unit_cost_cents)
                total_fees = sum(step["fee_cents"] for step in record["transitions"])
                write_down = settlements[-1]["terminal_write_down_cents"]
                self.assertEqual(record["final_net_worth_cents"],
                                 record["initial_net_worth_cents"] + gross_margin - total_fees - write_down)
