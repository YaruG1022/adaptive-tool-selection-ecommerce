(() => {
  'use strict';

  const names = {
    no_tools: ['不调查', 'No tools'],
    fixed_order: ['固定顺序', 'Fixed order'],
    uncertainty_threshold: ['不确定性阈值', 'Uncertainty threshold'],
    dqn: ['深度 Q 网络（DQN）', 'Deep Q-Network (DQN)'],
  };
  const toolNames = {
    market_report: ['当日市场快报', 'Same-day market report'],
    forecast: ['次日需求预测', 'Next-day demand forecast'],
  };
  const lineStyles = [
    ['var(--sw-green)', ''],
    ['light-dark(#527b97,#add0e9)', '8 5'],
    ['light-dark(#a65a38,#e4b197)', '3 4'],
    ['light-dark(#714097,#d3a5f0)', '11 4 2 4'],
  ];
  const dollars = new Intl.NumberFormat('en-US', {style:'currency',currency:'USD'});
  const cents = value => dollars.format(value / 100);
  const mean = values => values.reduce((total, value) => total + value, 0) / values.length;
  const setText = (element, labels) => signalI18n.setText(element, ...labels);

  function element(parent, tag, labels, className) {
    const node = document.createElement(tag);
    if (labels) setText(node, labels);
    if (className) node.className = className;
    parent.append(node);
    return node;
  }

  function seriesLabel(episode) {
    const name = names[episode.controller_id];
    const learning = episode.learning_seed;
    return [
      `研究记录 · ${name[0]} · 市场 ${episode.seed}${learning === null ? '' : ` · 训练种子 ${learning}`}`,
      `Research · ${name[1]} · Market ${episode.seed}${learning === null ? '' : ` · Learning seed ${learning}`}`,
    ];
  }

  function table(parent, headings, className) {
    const wrapper = element(parent, 'div', null, 'sw-table-scroll');
    const grid = element(wrapper, 'table', null, 'sw-result-table');
    grid.classList.add(className);
    const header = element(element(grid, 'thead'), 'tr');
    for (const heading of headings) element(header, 'th', heading).scope = 'col';
    return element(grid, 'tbody');
  }

  function chart(parent, series, axisTitle, chartTitle) {
    const svgNamespace = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNamespace, 'svg');
    svg.setAttribute('viewBox', '0 0 640 202');
    svg.setAttribute('role', 'img');
    svg.classList.add('sw-research-plot');
    parent.append(svg);

    function svgElement(tag, attributes, labels) {
      const node = document.createElementNS(svgNamespace, tag);
      for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
      if (labels) setText(node, labels);
      svg.append(node);
      return node;
    }

    svgElement('title', {}, chartTitle);
    const points = series.flatMap(line => line.points);
    const minX = Math.min(...points.map(point => point.x));
    const maxX = Math.max(...points.map(point => point.x));
    const minY = Math.min(...points.map(point => point.y));
    const maxY = Math.max(...points.map(point => point.y));
    const spread = maxY - minY || Math.max(100, Math.abs(maxY) * 0.02);
    const bottom = minY - spread * 0.08;
    const top = maxY + spread * 0.08;
    const x = value => minX === maxX ? 364 : 106 + (value - minX) / (maxX - minX) * 516;
    const y = value => 150 - (value - bottom) / (top - bottom) * 122;

    for (const number of [minY, (minY + maxY) / 2, maxY].filter((value, index, ticks) => ticks.indexOf(value) === index)) {
      svgElement('line', {x1:106,x2:622,y1:y(number),y2:y(number),stroke:'var(--sw-border)'});
      svgElement('text', {x:100,y:y(number) + 5,'text-anchor':'end'}, [cents(number), cents(number)]);
    }
    for (const tick of new Set([minX, maxX])) {
      svgElement('text', {x:x(tick),y:174,'text-anchor':'middle'}, [String(tick), String(tick)]);
    }
    svgElement('text', {x:622,y:197,'text-anchor':'end'}, axisTitle);
    const legend = element(parent, 'ul', null, 'sw-research-legend');
    series.forEach((line, index) => {
      const [color, dash] = lineStyles[index % lineStyles.length];
      const path = line.points.map((point, i) => `${i ? 'L' : 'M'}${x(point.x)},${y(point.y)}`).join(' ');
      svgElement('path', {d:path,fill:'none',stroke:color,'stroke-width':3,'stroke-dasharray':dash});
      if (line.points.length === 1) {
        const point = line.points[0];
        svgElement('circle', {cx:x(point.x),cy:y(point.y),r:4,fill:color});
      }
      const item = element(legend, 'li');
      const swatch = element(item, 'i');
      swatch.style.borderColor = color;
      swatch.style.borderTopStyle = dash ? 'dashed' : 'solid';
      swatch.setAttribute('aria-hidden', 'true');
      element(item, 'span', line.labels);
    });
  }

  function groupResults(episodes, days) {
    const groups = [];
    for (const [method, labels] of Object.entries(names)) {
      const matches = episodes.filter(episode => episode.controller_id === method);
      if (!matches.length) continue;
      const points = [{x:0,y:mean(matches.map(episode => episode.initial_net_worth_cents))}];
      for (let day = 0; day < days; day++) {
        points.push({x:day + 1,y:mean(matches.map(episode => episode.days[day].settlement.net_worth_cents))});
      }
      const fees = matches.map(episode => episode.days.reduce((total, day) =>
        total + day.tools.reduce((amount, tool) => amount + tool.fee_cents, 0), 0));
      const unfilled = matches.map(episode => episode.days.reduce((total, day) => total + day.settlement.unfilled_units, 0));
      groups.push({method,labels,points,count:matches.length,fees:mean(fees),unfilled:mean(unfilled)});
    }
    return groups;
  }

  function render(container, bundle) {
    const {run, episodes, evaluation, training} = bundle;
    const config = run.config;
    const marketCount = new Set(episodes.map(episode => episode.seed)).size;
    const title = run.split === 'held_out' ? ['留出市场结果', 'Held-out results'] : ['验证市场结果', 'Validation results'];
    container.replaceChildren();
    element(container, 'h3', title);
    element(container, 'p', [
      `${marketCount} 个市场 · ${episodes.length} 个回合 · 每回合 ${config.days} 天`,
      `${marketCount} markets · ${episodes.length} episodes · ${config.days} days per episode`,
    ], 'sw-fine');
    const metadata = element(container, 'details', null, 'sw-research-config');
    element(metadata, 'summary', ['来源与设置', 'Source and settings']);
    const version = bundle.environment_version;
    const schema = bundle.schema_version;
    const rows = [
      [`环境 v${version} · 记录格式 v${schema} · 情景 ${run.scenario}`, `Environment v${version} · Record format v${schema} · Scenario ${run.scenario}`],
      [`代码版本 ${run.code_revision}`, `Source revision ${run.code_revision}`],
      [`起始现金 ${cents(config.opening_cash_cents)} · 起始库存 ${config.opening_stock} 件 · 售价 ${cents(config.selling_price_cents)}`, `Opening cash ${cents(config.opening_cash_cents)} · Opening stock ${config.opening_stock} · Selling price ${cents(config.selling_price_cents)}`],
      [`单位成本 ${cents(config.unit_cost_cents)} · 单位期末可变现价值 ${cents(config.terminal_unit_nrv_cents)}`, `Unit cost ${cents(config.unit_cost_cents)} · Terminal unit realizable value ${cents(config.terminal_unit_nrv_cents)}`],
      [`快报 ${cents(config.market_report_fee_cents)} / ${config.market_report_minutes} 分钟 · 预测 ${cents(config.forecast_fee_cents)} / ${config.forecast_minutes} 分钟`, `Market report ${cents(config.market_report_fee_cents)} / ${config.market_report_minutes} min · Forecast ${cents(config.forecast_fee_cents)} / ${config.forecast_minutes} min`],
      [`调查窗口 ${clock(config.opening_minute)}–${clock(config.cutoff_minute)}`, `Investigation window ${clock(config.opening_minute)}–${clock(config.cutoff_minute)}`],
    ];
    for (const row of rows) element(metadata, 'p', row, 'sw-fine');

    const groups = groupResults(episodes, config.days);
    const headings = [
      ['策略', 'Policy'], ['回合', 'Episodes'], ['平均期末净资产', 'Mean final net worth'],
      ['平均工具费', 'Mean tool fees'], ['平均缺货件数', 'Mean unfilled units'], ['回放', 'Replay'],
    ];
    const tbody = table(container, headings, 'sw-research-comparison');
    for (const group of groups) {
      const row = element(tbody, 'tr');
      element(row, 'td', group.labels);
      const values = [String(group.count), cents(group.points.at(-1).y), cents(group.fees), group.unfilled.toFixed(1)];
      values.forEach((value, index) => {
        const cell = element(row, 'td');
        element(cell, 'span', headings[index + 1], 'sw-research-metric-label').setAttribute('aria-hidden', 'true');
        element(cell, 'span').textContent = value;
      });
      const link = element(element(row, 'td'), 'button', ['回放 →', 'Replay →']);
      link.type = 'button';
      link.dataset.researchTrace = group.method;
      link.title = group.method;
    }
    if (evaluation) {
      const name = names[evaluation.reference_id];
      const difference = cents(evaluation.mean_delta_cents);
      const interval = evaluation.confidence_interval_cents.map(cents).join(' – ');
      const confidence = Math.round(evaluation.confidence_level * 10000) / 100;
      element(container, 'p', [
        `DQN 相对${name[0]}：${difference} · ${confidence}% 配对置信区间 ${interval}`,
        `DQN vs. ${name[1]}: ${difference} · ${confidence}% paired confidence interval ${interval}`,
      ], 'sw-research-contrast');
    }

    const trajectory = element(container, 'details', null, 'sw-research-chart');
    trajectory.dataset.researchTrajectory = '';
    element(trajectory, 'summary', ['评估经营轨迹', 'Evaluation trajectories']);
    chart(trajectory, groups, ['经营日', 'Business day'], ['每日平均净资产（美元）', 'Mean daily net worth (USD)']);
    if (training) {
      const history = element(container, 'details', null, 'sw-research-chart');
      history.dataset.researchTraining = '';
      element(history, 'summary', ['训练检查点验证结果', 'Validation at training checkpoints']);
      element(history, 'p', [
        `选定 ${training.selected_candidate} 第 ${training.selected_episode} 回合 · 训练种子 ${training.learning_seeds.join(', ')}`,
        `Selected ${training.selected_candidate} at episode ${training.selected_episode} · Learning seeds ${training.learning_seeds.join(', ')}`,
      ], 'sw-fine');
      chart(history, training.series.map(line => ({
        labels:[line.candidate_id,line.candidate_id],
        points:line.points.map(point => ({x:point.episode,y:point.mean_final_net_worth_cents})),
      })), ['训练回合', 'Training episode'], ['检查点平均验证净资产（美元）', 'Mean validation net worth by checkpoint (USD)']);
      const validation = table(history, [['模型', 'Model'], ['训练回合', 'Training episode'], ['平均验证净资产', 'Mean validation net worth']], 'sw-research-checkpoints');
      for (const line of training.series) for (const point of line.points) {
        const row = element(validation, 'tr');
        for (const value of [line.candidate_id, point.episode, cents(point.mean_final_net_worth_cents)]) {
          element(row, 'td').textContent = value;
        }
      }
    }
    container.hidden = false;
  }

  function clock(value) {
    return `${String(Math.floor(value / 60)).padStart(2,'0')}:${String(value % 60).padStart(2,'0')}`;
  }

  globalThis.LittleSignalResearchView = Object.freeze({render, seriesLabel, cents, clock, setText, toolNames});
})();
