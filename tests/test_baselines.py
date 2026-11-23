import unittest

from little_signal_shop.controllers.baselines import BASELINE_IDS, make_baselines
from little_signal_shop.environment import (
    Action,
    DayInput,
    EnvironmentConfig,
    MarketInputs,
    ShopEnvironment,
)


class BaselineControllerTests(unittest.TestCase):
    def test_baselines_names_and_fixed_order_across_the_two_calls(self):
        config = EnvironmentConfig(days=2)
        controllers = make_baselines(config)
        self.assertEqual(BASELINE_IDS, ("no_tools", "fixed_order", "uncertainty_threshold"))
        self.assertEqual(set(controllers), set(BASELINE_IDS))

        env = ShopEnvironment(config)
        observation = env.reset(MarketInputs(days=(DayInput(demand=5), DayInput(demand=5))))
        self.assertEqual(controllers["no_tools"](observation), Action.STOP)

        fixed_order = controllers["fixed_order"]
        self.assertEqual(fixed_order(observation), Action.MARKET_REPORT)
        observation = env.step(Action.MARKET_REPORT).observation
        self.assertEqual(fixed_order(observation), Action.FORECAST)
        observation = env.step(Action.FORECAST).observation
        self.assertEqual(fixed_order(observation), Action.STOP)

    def test_controllers_stop_when_no_tool_is_legal(self):
        config = EnvironmentConfig(days=2, cutoff_minute=629)
        controllers = make_baselines(config)
        env = ShopEnvironment(config)
        env.reset(MarketInputs(days=(DayInput(demand=5), DayInput(demand=5))))
        observation = env.step(Action.MARKET_REPORT).observation
        self.assertEqual(observation.legal_actions, (Action.STOP,))

        for name, controller in controllers.items():
            with self.subTest(controller=name):
                self.assertEqual(controller(observation), Action.STOP)

    def test_uncertainty_threshold_requires_positive_score_using_post_fee_cash(self):
        inputs = MarketInputs(days=(DayInput(demand=0), DayInput(demand=5)))
        for cash_cents, fee_cents, expected_action in (
            (900, 400, Action.STOP),
            (900, 399, Action.FORECAST),
            (898, 399, Action.STOP),
        ):
            with self.subTest(cash_cents=cash_cents, fee_cents=fee_cents):
                config = EnvironmentConfig(
                    days=2,
                    opening_cash_cents=cash_cents,
                    market_report_minutes=100,
                    forecast_fee_cents=fee_cents,
                )
                observation = ShopEnvironment(config).reset(inputs)
                self.assertEqual(set(observation.legal_actions), {Action.STOP, Action.FORECAST})
                controller = make_baselines(config)["uncertainty_threshold"]
                self.assertEqual(controller(observation), expected_action)

    def test_uncertainty_threshold_favors_market_report_on_a_positive_tie(self):
        config = EnvironmentConfig(days=2, opening_cash_cents=600, forecast_fee_cents=100)
        inputs = MarketInputs(days=(DayInput(demand=2, public_tomorrow=5), DayInput(demand=5)))
        observation = ShopEnvironment(config).reset(inputs)
        self.assertEqual(set(observation.legal_actions), set(Action))

        controller = make_baselines(config)["uncertainty_threshold"]
        self.assertEqual(controller(observation), Action.MARKET_REPORT)

    def test_uncertainty_threshold_reconsiders_forecast_after_market_report(self):
        config = EnvironmentConfig(days=2, opening_cash_cents=1600, opening_stock=11)
        controller = make_baselines(config)["uncertainty_threshold"]
        for report, expected_action in ((0, Action.STOP), (10, Action.FORECAST)):
            with self.subTest(report=report):
                env = ShopEnvironment(config)
                observation = env.reset(MarketInputs(days=(
                    DayInput(demand=6, public_today=6, public_tomorrow=5, market_report=report),
                    DayInput(demand=5),
                )))
                self.assertEqual(controller(observation), Action.MARKET_REPORT)
                observation = env.step(Action.MARKET_REPORT).observation
                self.assertIn(Action.FORECAST, observation.legal_actions)
                self.assertEqual(controller(observation), expected_action)

    def test_uncertainty_threshold_reconsiders_market_report_after_forecast(self):
        config = EnvironmentConfig(days=2)
        controller = make_baselines(config)["uncertainty_threshold"]
        for forecast, expected_action in ((0, Action.STOP), (5, Action.MARKET_REPORT)):
            with self.subTest(forecast=forecast):
                env = ShopEnvironment(config)
                observation = env.reset(MarketInputs(days=(
                    DayInput(demand=1, forecast=forecast),
                    DayInput(demand=5),
                )))
                self.assertEqual(controller(observation), Action.FORECAST)
                observation = env.step(Action.FORECAST).observation
                self.assertIn(Action.MARKET_REPORT, observation.legal_actions)
                self.assertEqual(controller(observation), expected_action)

    def test_changing_hidden_market_rows_does_not_change_baseline_actions(self):
        config = EnvironmentConfig(days=2)
        controllers = make_baselines(config)
        env = ShopEnvironment(config)
        low = env.reset(MarketInputs(days=(DayInput(demand=0), DayInput(demand=0))))
        high = env.reset(MarketInputs(days=(
            DayInput(demand=9, market_report=8, forecast=12),
            DayInput(demand=13),
        )))

        for name, controller in controllers.items():
            with self.subTest(controller=name):
                self.assertEqual(controller(low), controller(high))
