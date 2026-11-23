'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const validatorPath = path.join(__dirname, '../src/replay/research-records.js');
const {parse} = require(validatorPath);

function matchedExample() {
  const dayOne = {
    opening_cash_cents: 10000, opening_net_worth_cents: 12500,
    public_today: 0, public_tomorrow: 5, stop_minute: 540, tools: [], demand: 0,
    settlement: {
      day: 1, received_units: 0, opening_stock: 5, ordered_units: 0, purchase_cents: 0, delivery_day: null,
      sold_units: 0, unfilled_units: 0, revenue_cents: 0, closing_stock: 5, in_transit_units: 0,
      cash_cents: 10000, inventory_value_cents: 2500, terminal_write_down_cents: 0, net_worth_cents: 12500,
    },
  };
  const dayTwo = {
    opening_cash_cents: 10000, opening_net_worth_cents: 12500,
    public_today: null, public_tomorrow: null, stop_minute: null, tools: [], demand: 8,
    settlement: {
      day: 2, received_units: 0, opening_stock: 5, ordered_units: 0, purchase_cents: 0, delivery_day: null,
      sold_units: 5, unfilled_units: 3, revenue_cents: 4500, closing_stock: 0, in_transit_units: 0,
      cash_cents: 14500, inventory_value_cents: 0, terminal_write_down_cents: 0, net_worth_cents: 14500,
    },
  };
  const reference = {
    seed: 3001, input_id: '8'.repeat(64), controller_id: 'no_tools', model_id: null, learning_seed: null,
    initial_net_worth_cents: 12500, final_net_worth_cents: 14500, days: [dayOne, dayTwo],
  };
  const learned = {
    ...reference,
    controller_id: 'dqn', model_id: `mlp32:seed-401:episode-100:sha256:${'9'.repeat(64)}`, learning_seed: 401,
    final_net_worth_cents: 15500,
    days: [{
      ...dayOne,
      stop_minute: 600,
      tools: [{id: 'forecast', start_minute: 540, end_minute: 600, fee_cents: 200, estimate: 8}],
      settlement: {
        ...dayOne.settlement, ordered_units: 3, purchase_cents: 1500, delivery_day: 2,
        in_transit_units: 3, cash_cents: 8300, inventory_value_cents: 4000, net_worth_cents: 12300,
      },
    }, {
      ...dayTwo, opening_cash_cents: 8300, opening_net_worth_cents: 12300,
      settlement: {
        ...dayTwo.settlement, received_units: 3, opening_stock: 8, sold_units: 8, unfilled_units: 0,
        revenue_cents: 7200, cash_cents: 15500, net_worth_cents: 15500,
      },
    }],
  };
  return {
    format: 'little-signal-shop-research', schema_version: '1', environment_version: '1',
    run: {
      code_revision: `commit+sha256:${'a'.repeat(64)}`, split: 'held_out', scenario: 'primary', primary_baseline: 'no_tools',
      config: {
        days: 2, opening_cash_cents: 10000, opening_stock: 5, unit_cost_cents: 500, selling_price_cents: 900,
        terminal_unit_nrv_cents: 300, opening_minute: 540, cutoff_minute: 630,
        market_report_fee_cents: 100, market_report_minutes: 30, forecast_fee_cents: 200, forecast_minutes: 60,
      },
    },
    episodes: [reference, learned],
    evaluation: {
      reference_id: 'no_tools', mean_delta_cents: 1000, confidence_level: 0.95, confidence_interval_cents: [1000, 1000],
    },
    training: {
      selected_candidate: 'mlp32', selected_episode: 100, learning_seeds: [401],
      series: [{candidate_id: 'mlp32', points: [{episode: 100, mean_final_net_worth_cents: 15833.5}]}],
    },
  };
}

test('classic script and CommonJS expose the same deeply frozen research bundle', () => {
  const sandbox = vm.createContext({});
  vm.runInContext(fs.readFileSync(validatorPath, 'utf8'), sandbox);
  const example = matchedExample();
  const source = JSON.stringify(example);
  assert.equal(typeof sandbox.LittleSignalResearch.parse, 'function');
  assert.equal(JSON.stringify(sandbox.LittleSignalResearch.parse(source)), source);

  const parsed = parse(source);
  assert.deepEqual(parsed, example);
  assert.ok(Object.isFrozen(parsed));
  assert.ok(Object.isFrozen(parsed.run.config));
  assert.ok(Object.isFrozen(parsed.episodes[1].days[0].tools[0]));
  assert.ok(Object.isFrozen(parsed.training.series[0].points));
  assert.throws(() => { parsed.episodes[1].days[1].settlement.sold_units = 0; }, TypeError);
});

test('invalid versions, fields, numeric amounts, and commitments are rejected', () => {
  for (const [modify, error] of [
    [bundle => { bundle.environment_version = '2'; }, /unsupported format or version/],
    [bundle => { bundle.run.config.unknown = 0; }, /unexpected fields/],
    [bundle => { bundle.run.config.unit_cost_cents = 1.5; }, /expected an integer/],
    [bundle => { bundle.episodes[0].days[0].demand = Number.MAX_SAFE_INTEGER + 1; }, /expected an integer/],
    [bundle => { bundle.episodes[1].days[0].settlement.purchase_cents = 1400; }, /purchase_cents/],
    [bundle => { bundle.episodes[1].days[0].settlement.ordered_units = 2; }, /ordered_units/],
    [bundle => { bundle.episodes[1].days[1].settlement.received_units = 2; }, /received_units/],
    [bundle => { bundle.episodes[1].days[1].opening_cash_cents = 8200; }, /opening_cash_cents/],
    [bundle => { bundle.episodes[1].days[1].settlement.cash_cents = 15400; }, /cash_cents/],
    [bundle => { bundle.episodes[1].final_net_worth_cents = 15400; }, /final_net_worth_cents/],
    [bundle => { bundle.episodes[1].days[1].stop_minute = 540; }, /terminal day/],
  ]) {
    const bundle = matchedExample();
    modify(bundle);
    assert.throws(() => parse(JSON.stringify(bundle)), error);
  }
});

test('tool results arriving at the cutoff are usable and alter the prepaid ledger once', () => {
  const bundle = matchedExample();
  const learned = bundle.episodes[1];
  const [whenOrdered, onTerminalDay] = learned.days;
  whenOrdered.tools.push({id: 'market_report', start_minute: 600, end_minute: 630, fee_cents: 100, estimate: 0});
  whenOrdered.stop_minute = 630;
  whenOrdered.settlement.cash_cents = onTerminalDay.opening_cash_cents = 8200;
  whenOrdered.settlement.net_worth_cents = onTerminalDay.opening_net_worth_cents = 12200;
  onTerminalDay.settlement.cash_cents = onTerminalDay.settlement.net_worth_cents = learned.final_net_worth_cents = 15400;
  bundle.evaluation.mean_delta_cents = 900;
  bundle.evaluation.confidence_interval_cents = [900, 900];
  assert.equal(parse(JSON.stringify(bundle)).episodes[1].days[0].tools[1].end_minute, 630);

  bundle.run.config.cutoff_minute = 629;
  assert.throws(() => parse(JSON.stringify(bundle)), /decision window/);
  bundle.run.config.cutoff_minute = 630;
  whenOrdered.tools[1].id = 'forecast';
  assert.throws(() => parse(JSON.stringify(bundle)), /repeated tool/);
});

test('terminal leftover stock reconciles at the lower of cost and net realizable value', () => {
  const bundle = matchedExample();
  bundle.evaluation = null;
  bundle.training = null;
  bundle.run.split = 'validation';
  const [reference] = bundle.episodes;
  bundle.episodes = [reference];
  const terminal = reference.days[1];
  terminal.demand = 2;
  Object.assign(terminal.settlement, {
    sold_units: 2, unfilled_units: 0, revenue_cents: 1800, closing_stock: 3,
    cash_cents: 11800, inventory_value_cents: 900, terminal_write_down_cents: 600, net_worth_cents: 12700,
  });
  reference.final_net_worth_cents = 12700;
  assert.equal(parse(JSON.stringify(bundle)).episodes[0].final_net_worth_cents, 12700);

  terminal.settlement.terminal_write_down_cents = 0;
  assert.throws(() => parse(JSON.stringify(bundle)), /terminal_write_down_cents/);
});

test('market identity, one record per policy and seed, paired mean, and selected model must agree', () => {
  for (const [modify, error] of [
    [bundle => { bundle.episodes[1].input_id = 'c'.repeat(64); }, /input_id/],
    [bundle => { bundle.episodes.push(bundle.episodes[0]); }, /duplicate controller/],
    [bundle => { bundle.episodes[1].seed = 3002; }, /lacks a paired reference market/],
    [bundle => { bundle.evaluation.mean_delta_cents = -1000; }, /paired episode results/],
    [bundle => { bundle.evaluation.confidence_interval_cents = [1200, 800]; }, /out of order/],
    [bundle => { bundle.episodes[1].learning_seed = 402; }, /model identity/],
    [bundle => { bundle.training.selected_episode = 250; }, /selected checkpoint/],
    [bundle => { bundle.training.series[0].points[0].episode = 250; }, /missing from the training chart/],
  ]) {
    const bundle = matchedExample();
    modify(bundle);
    assert.throws(() => parse(JSON.stringify(bundle)), error);
  }
});
