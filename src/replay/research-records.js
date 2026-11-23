(() => {
  'use strict';

  const FORMAT = 'little-signal-shop-research';
  const BASELINES = new Set(['no_tools', 'fixed_order', 'uncertainty_threshold']);
  const HASH = /^[a-f0-9]{64}$/;
  const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9_.:+-]*$/;
  const MODEL_ID = /^([a-z][a-z0-9_-]*):seed-(0|[1-9]\d*):episode-([1-9]\d*):sha256:[a-f0-9]{64}$/;
  const CONFIG_FIELDS = [
    'days', 'opening_cash_cents', 'opening_stock', 'unit_cost_cents', 'selling_price_cents',
    'terminal_unit_nrv_cents', 'opening_minute', 'cutoff_minute', 'market_report_fee_cents',
    'market_report_minutes', 'forecast_fee_cents', 'forecast_minutes',
  ];
  const SETTLEMENT_FIELDS = [
    'day', 'received_units', 'opening_stock', 'ordered_units', 'purchase_cents', 'delivery_day',
    'sold_units', 'unfilled_units', 'revenue_cents', 'closing_stock', 'in_transit_units',
    'cash_cents', 'inventory_value_cents', 'terminal_write_down_cents', 'net_worth_cents',
  ];

  function require(condition, location, reason) {
    if (!condition) throw new Error(`${location}: ${reason}`);
  }

  function object(value, fields, location) {
    require(value !== null && typeof value === 'object' && !Array.isArray(value)
      && Object.keys(value).length === fields.length && fields.every(field => Object.hasOwn(value, field)),
    location, 'unexpected fields');
  }

  function integer(value, location, minimum = 0) {
    require(Number.isSafeInteger(value) && value >= minimum, location, `expected an integer of at least ${minimum}`);
  }

  function finite(value, location) {
    require(Number.isFinite(value) && Math.abs(value) <= Number.MAX_SAFE_INTEGER, location, 'expected a finite number');
  }

  function identifier(value, location) {
    require(typeof value === 'string' && IDENTIFIER.test(value), location, 'invalid identifier');
  }

  function equal(actual, expected, location) {
    require(actual === expected, location, 'does not reconcile');
  }

  function validateRun(run) {
    object(run, ['code_revision', 'split', 'scenario', 'primary_baseline', 'config'], 'run');
    identifier(run.code_revision, 'run.code_revision');
    identifier(run.scenario, 'run.scenario');
    require(run.split === 'validation' || run.split === 'held_out', 'run.split', 'unknown market split');
    require(BASELINES.has(run.primary_baseline), 'run.primary_baseline', 'unknown baseline');
    const config = run.config;
    object(config, CONFIG_FIELDS, 'run.config');
    for (const field of CONFIG_FIELDS) integer(config[field], `run.config.${field}`);
    require(config.days >= 2 && config.unit_cost_cents > 0 && config.unit_cost_cents < config.selling_price_cents,
      'run.config', 'invalid business horizon, cost, or price');
    require(config.opening_minute <= config.cutoff_minute && config.cutoff_minute < 1440
      && config.market_report_minutes > 0 && config.forecast_minutes > 0,
    'run.config', 'invalid decision window or tool durations');
  }

  function validateDay(day, config, start, number, location) {
    object(day, ['settlement', 'opening_cash_cents', 'opening_net_worth_cents', 'public_today',
      'public_tomorrow', 'stop_minute', 'tools', 'demand'], location);
    const settlement = day.settlement;
    object(settlement, SETTLEMENT_FIELDS, `${location}.settlement`);
    for (const field of SETTLEMENT_FIELDS) {
      if (field !== 'delivery_day') integer(settlement[field], `${location}.settlement.${field}`);
    }
    integer(day.opening_cash_cents, `${location}.opening_cash_cents`);
    integer(day.opening_net_worth_cents, `${location}.opening_net_worth_cents`);
    integer(day.demand, `${location}.demand`);
    equal(settlement.day, number, `${location}.settlement.day`);
    equal(settlement.opening_stock, start.stock, `${location}.settlement.opening_stock`);
    equal(settlement.received_units, start.received, `${location}.settlement.received_units`);
    equal(day.opening_cash_cents, start.cash, `${location}.opening_cash_cents`);
    equal(day.opening_net_worth_cents, start.cash + start.stock * config.unit_cost_cents,
      `${location}.opening_net_worth_cents`);

    const terminal = number === config.days;
    require(Array.isArray(day.tools) && day.tools.length <= 2, `${location}.tools`, 'invalid tool count');
    let cash = start.cash;
    let order = 0;
    if (terminal) {
      require(day.public_today === null && day.public_tomorrow === null && day.stop_minute === null
        && day.tools.length === 0, location, 'terminal day cannot contain tool or procurement decisions');
    } else {
      integer(day.public_today, `${location}.public_today`);
      integer(day.public_tomorrow, `${location}.public_tomorrow`);
      let today = day.public_today;
      let tomorrow = day.public_tomorrow;
      let clock = config.opening_minute;
      const called = new Set();
      for (const [index, tool] of day.tools.entries()) {
        const toolLocation = `${location}.tools[${index}]`;
        object(tool, ['id', 'start_minute', 'end_minute', 'fee_cents', 'estimate'], toolLocation);
        require((tool.id === 'market_report' || tool.id === 'forecast') && !called.has(tool.id),
          toolLocation, 'unknown or repeated tool');
        called.add(tool.id);
        const fee = config[`${tool.id}_fee_cents`];
        const duration = config[`${tool.id}_minutes`];
        equal(tool.start_minute, clock, `${toolLocation}.start_minute`);
        equal(tool.end_minute, clock + duration, `${toolLocation}.end_minute`);
        equal(tool.fee_cents, fee, `${toolLocation}.fee_cents`);
        require(tool.end_minute <= config.cutoff_minute && cash >= fee,
          toolLocation, 'tool exceeds decision window or available cash');
        integer(tool.estimate, `${toolLocation}.estimate`);
        cash -= fee;
        clock = tool.end_minute;
        if (tool.id === 'market_report') today = tool.estimate;
        else tomorrow = tool.estimate;
      }
      equal(day.stop_minute, clock, `${location}.stop_minute`);
      const projectedStock = start.stock - Math.min(start.stock, today);
      order = Math.min(Math.max(0, tomorrow - projectedStock), Math.floor(cash / config.unit_cost_cents));
    }

    const sold = Math.min(start.stock, day.demand);
    const closingStock = start.stock - sold;
    const purchase = order * config.unit_cost_cents;
    const revenue = sold * config.selling_price_cents;
    const writeDown = terminal ? closingStock * Math.max(0, config.unit_cost_cents - config.terminal_unit_nrv_cents) : 0;
    const inventoryValue = (closingStock + order) * config.unit_cost_cents - writeDown;
    const closingCash = cash - purchase + revenue;
    const expected = {
      ordered_units: order, purchase_cents: purchase, delivery_day: order ? number + 1 : null,
      sold_units: sold, unfilled_units: day.demand - sold, revenue_cents: revenue,
      closing_stock: closingStock, in_transit_units: order, cash_cents: closingCash,
      inventory_value_cents: inventoryValue, terminal_write_down_cents: writeDown,
      net_worth_cents: closingCash + inventoryValue,
    };
    for (const [field, value] of Object.entries(expected)) equal(settlement[field], value, `${location}.settlement.${field}`);
    return {cash: closingCash, stock: closingStock + order, received: order};
  }

  function validateEpisode(episode, config, location) {
    object(episode, ['seed', 'input_id', 'controller_id', 'model_id', 'learning_seed',
      'initial_net_worth_cents', 'final_net_worth_cents', 'days'], location);
    integer(episode.seed, `${location}.seed`);
    require(typeof episode.input_id === 'string' && HASH.test(episode.input_id),
      `${location}.input_id`, 'expected a SHA-256 fingerprint');
    let model = null;
    if (episode.controller_id === 'dqn') {
      integer(episode.learning_seed, `${location}.learning_seed`);
      model = typeof episode.model_id === 'string' ? MODEL_ID.exec(episode.model_id) : null;
      require(model && model[2] === String(episode.learning_seed) && Number.isSafeInteger(Number(model[3])),
        `${location}.model_id`, 'DQN model identity does not match its learning seed');
    } else {
      require(BASELINES.has(episode.controller_id) && episode.model_id === null && episode.learning_seed === null,
        location, 'invalid baseline controller identity');
    }

    integer(episode.initial_net_worth_cents, `${location}.initial_net_worth_cents`);
    integer(episode.final_net_worth_cents, `${location}.final_net_worth_cents`);
    equal(episode.initial_net_worth_cents, config.opening_cash_cents + config.opening_stock * config.unit_cost_cents,
      `${location}.initial_net_worth_cents`);
    require(Array.isArray(episode.days) && episode.days.length === config.days, `${location}.days`, 'wrong episode length');
    let start = {cash: config.opening_cash_cents, stock: config.opening_stock, received: 0};
    for (const [index, day] of episode.days.entries()) {
      start = validateDay(day, config, start, index + 1, `${location}.days[${index}]`);
    }
    equal(episode.final_net_worth_cents, episode.days.at(-1).settlement.net_worth_cents, `${location}.final_net_worth_cents`);
    return model;
  }

  function validateEvaluation(evaluation, run, episodes, models, references) {
    if (evaluation === null) return;
    object(evaluation, ['reference_id', 'mean_delta_cents', 'confidence_level', 'confidence_interval_cents'], 'evaluation');
    equal(evaluation.reference_id, run.primary_baseline, 'evaluation.reference_id');
    finite(evaluation.mean_delta_cents, 'evaluation.mean_delta_cents');
    require(Number.isFinite(evaluation.confidence_level) && evaluation.confidence_level > 0
      && evaluation.confidence_level < 1, 'evaluation.confidence_level', 'expected a level strictly between zero and one');
    const interval = evaluation.confidence_interval_cents;
    require(Array.isArray(interval) && interval.length === 2, 'evaluation.confidence_interval_cents', 'expected two endpoints');
    finite(interval[0], 'evaluation.confidence_interval_cents[0]');
    finite(interval[1], 'evaluation.confidence_interval_cents[1]');
    require(interval[0] <= interval[1], 'evaluation.confidence_interval_cents', 'endpoints are out of order');

    let total = 0n;
    let pairs = 0;
    for (const episode of episodes) {
      if (episode.controller_id !== 'dqn') continue;
      require(references.has(episode.seed), 'evaluation', 'DQN episode lacks a paired reference market');
      total += BigInt(episode.final_net_worth_cents) - BigInt(references.get(episode.seed));
      pairs += 1;
    }
    require(pairs > 0 && pairs === references.size * models.size, 'evaluation', 'paired learning-seed grid is incomplete');
    const expected = Number(total) / pairs;
    const tolerance = Math.max(1e-9, Math.abs(expected) * Number.EPSILON);
    require(Math.abs(evaluation.mean_delta_cents - expected) <= tolerance, 'evaluation.mean_delta_cents',
      'does not match the paired episode results');
  }

  function validateTraining(training, models) {
    if (training === null) return;
    object(training, ['selected_candidate', 'selected_episode', 'learning_seeds', 'series'], 'training');
    identifier(training.selected_candidate, 'training.selected_candidate');
    integer(training.selected_episode, 'training.selected_episode', 1);
    require(Array.isArray(training.learning_seeds) && training.learning_seeds.length > 0,
      'training.learning_seeds', 'expected learning seeds');
    for (const seed of training.learning_seeds) integer(seed, 'training.learning_seeds');
    const learningSeeds = new Set(training.learning_seeds);
    equal(learningSeeds.size, training.learning_seeds.length, 'training.learning_seeds');
    require(models.size === 0 || models.size === learningSeeds.size,
      'training.learning_seeds', 'does not match the imported DQN models');
    for (const [seed, model] of models) {
      require(learningSeeds.has(seed) && model[1] === training.selected_candidate && model[3] === String(training.selected_episode),
        'training', 'DQN model does not match the selected checkpoint');
    }

    require(Array.isArray(training.series) && training.series.length > 0, 'training.series', 'expected validation series');
    const candidates = new Set();
    let selectedFound = false;
    for (const [index, series] of training.series.entries()) {
      const location = `training.series[${index}]`;
      object(series, ['candidate_id', 'points'], location);
      identifier(series.candidate_id, `${location}.candidate_id`);
      require(!candidates.has(series.candidate_id), location, 'duplicate candidate');
      candidates.add(series.candidate_id);
      require(Array.isArray(series.points) && series.points.length > 0, `${location}.points`, 'expected checkpoint scores');
      let previousEpisode = 0;
      for (const point of series.points) {
        object(point, ['episode', 'mean_final_net_worth_cents'], `${location}.points`);
        integer(point.episode, `${location}.points.episode`, previousEpisode + 1);
        finite(point.mean_final_net_worth_cents, `${location}.points.mean_final_net_worth_cents`);
        require(point.mean_final_net_worth_cents >= 0, `${location}.points`, 'negative final net worth');
        previousEpisode = point.episode;
        if (series.candidate_id === training.selected_candidate && point.episode === training.selected_episode) selectedFound = true;
      }
    }
    require(selectedFound, 'training', 'selected checkpoint is missing from the training chart');
  }

  function freeze(value) {
    if (value !== null && typeof value === 'object') {
      for (const child of Object.values(value)) freeze(child);
      Object.freeze(value);
    }
    return value;
  }

  function parse(source) {
    require(typeof source === 'string', 'bundle', 'expected JSON text');
    const bundle = JSON.parse(source);
    object(bundle, ['format', 'schema_version', 'environment_version', 'run', 'episodes', 'evaluation', 'training'], 'bundle');
    require(bundle.format === FORMAT && bundle.schema_version === '1' && bundle.environment_version === '1',
      'bundle', 'unsupported format or version');
    validateRun(bundle.run);
    require(Array.isArray(bundle.episodes) && bundle.episodes.length > 0, 'episodes', 'expected at least one episode');

    const identifiers = new Set();
    const inputIds = new Map();
    const models = new Map();
    const references = new Map();
    for (const [index, episode] of bundle.episodes.entries()) {
      const location = `episodes[${index}]`;
      const model = validateEpisode(episode, bundle.run.config, location);
      const identifier = `${episode.seed}/${episode.controller_id}/${episode.learning_seed}`;
      require(!identifiers.has(identifier), location, 'duplicate controller on the same market and learning seed');
      identifiers.add(identifier);
      if (inputIds.has(episode.seed)) equal(episode.input_id, inputIds.get(episode.seed), `${location}.input_id`);
      else inputIds.set(episode.seed, episode.input_id);
      if (model) {
        if (models.has(episode.learning_seed)) equal(model[0], models.get(episode.learning_seed)[0], `${location}.model_id`);
        else models.set(episode.learning_seed, model);
      }
      if (episode.controller_id === bundle.run.primary_baseline) references.set(episode.seed, episode.final_net_worth_cents);
    }
    validateEvaluation(bundle.evaluation, bundle.run, bundle.episodes, models, references);
    validateTraining(bundle.training, models);
    return freeze(bundle);
  }

  const api = Object.freeze({parse});
  if (typeof module === 'object' && module.exports) module.exports = api;
  else globalThis.LittleSignalResearch = api;
})();
