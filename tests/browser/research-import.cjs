const assert = require("node:assert/strict");
const { existsSync, readFileSync } = require("node:fs");
const { join, resolve } = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

const root = resolve(__dirname, "../..");
const bundlePath = process.argv[2]
  ? resolve(process.argv[2])
  : join(root, "artifacts", "phase6-research-v1.json");

function browserExecutable() {
  if (process.env.PLAYWRIGHT_BROWSER_EXECUTABLE) {
    return process.env.PLAYWRIGHT_BROWSER_EXECUTABLE;
  }
  if (process.platform === "win32") {
    const paths = [
      join(process.env.ProgramFiles || "C:/Program Files", "Google/Chrome/Application/chrome.exe"),
      join(process.env["ProgramFiles(x86)"] || "C:/Program Files (x86)", "Microsoft/Edge/Application/msedge.exe"),
    ];
    return paths.find(existsSync);
  }
  return undefined;
}

async function waitForText(page, selector, pattern) {
  await page.locator(selector).filter({ hasText: pattern }).waitFor();
}

async function waitForLanguage(page, language) {
  await page.waitForFunction(
    expected => document.documentElement.lang === expected,
    language,
  );
}

async function liveSnapshot(page) {
  return page.locator('[data-screen="shop"]').evaluate(shop => {
    const visibleText = selector => shop.querySelector(selector).innerText;
    return {
      day: Number(document.querySelector("[data-day]").textContent),
      cash: visibleText("[data-cash]"),
      netWorth: visibleText("[data-worth]"),
      fees: visibleText("[data-fees]"),
      shipments: visibleText("[data-total]"),
      toolBudget: visibleText("[data-budget]"),
      toolResult: visibleText("[data-result]"),
      stockAndIncomingOrders: visibleText(".sw-products"),
      journal: visibleText("[data-journal]"),
      lastReceipt: visibleText("[data-receipt]"),
    };
  });
}

async function stageLiveStore(page) {
  await page.locator("[data-reduce]").check();
  for (const nextDay of [29, 30, 31]) {
    if (nextDay === 31) await page.locator('[data-tool="0"]').click();
    await page.locator("[data-open]").click();
    await page.waitForFunction(
      day => Number(document.querySelector("[data-day]").textContent) === day,
      nextDay,
    );
  }
  await page.locator('[data-tool="0"]').click();
  const state = await liveSnapshot(page);
  assert.equal(state.day, 31);
  assert.notEqual(state.fees, "$0");
  assert.match(state.stockAndIncomingOrders, /Incoming\s+[1-9]\d*/);
  assert.match(state.lastReceipt, /30/);
  return state;
}

async function checkInvalidImport(page, name, data, acceptedResults) {
  await page.locator("[data-research-file]").setInputFiles({
    name,
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(data)),
  });
  await waitForText(page, "[data-research-status]", /^Could not import this file\./);
  assert.equal(await page.locator("[data-research-results]").innerText(), acceptedResults);
}

async function testResearchImport(page, bundle) {
  const lab = page.locator('[data-view="lab"]');
  const toggleLanguage = page.locator("[data-language-toggle]");
  const researchResults = page.locator("[data-research-results]");

  await lab.click();
  await waitForText(page, "[data-lab-count]", /9\s*\/\s*9/);
  assert.equal(await researchResults.isVisible(), false);
  await page.locator('[data-config="volatility"]').selectOption("1.7");
  await page.locator("[data-research-file]").setInputFiles(bundlePath);
  await waitForText(page, "[data-research-status]", /^Imported \d+ research episodes\./);
  await researchResults.waitFor();
  for (const [chart, label] of [
    ["[data-research-trajectory]", /^Evaluation trajectories$/],
    ["[data-research-training]", /^Validation at training checkpoints$/],
  ]) {
    await waitForText(page, `${chart} > summary`, label);
    await page.locator(`${chart} > summary`).click();
    await page.locator(`${chart} svg`).waitFor();
    await page.locator(`${chart} > summary`).click();
  }
  for (const name of ["no_tools", "fixed_order", "uncertainty_threshold", "dqn"]) {
    await page.locator(`[data-research-trace="${name}"]`).first().waitFor();
  }

  await toggleLanguage.click();
  await waitForLanguage(page, "zh-CN");
  assert.equal(await lab.getAttribute("aria-pressed"), "true");
  assert.equal(await page.locator('[data-config="volatility"]').inputValue(), "1.7");
  assert.equal(await researchResults.isVisible(), true);
  await toggleLanguage.click();
  await waitForLanguage(page, "en");

  const acceptedResults = await researchResults.innerText();
  const wrongVersion = structuredClone(bundle);
  wrongVersion.schema_version = "unsupported-test-version";
  await checkInvalidImport(page, "bad-version.json", wrongVersion, acceptedResults);

  await page.locator("[data-research-file]").setInputFiles(bundlePath);
  await waitForText(page, "[data-research-status]", /^Imported \d+ research episodes\./);
  const wrongLedger = structuredClone(bundle);
  wrongLedger.episodes[0].days[0].settlement.cash_cents += 1;
  await checkInvalidImport(page, "bad-ledger.json", wrongLedger, acceptedResults);
  assert.equal(await page.locator('[data-config="volatility"]').inputValue(), "1.7");
}

async function testReplay(page, bundle) {
  const toggleLanguage = page.locator("[data-language-toggle]");
  const replayView = page.locator('[data-view="replay"]');
  const source = page.locator("[data-replay-source]");
  const day = page.locator("[data-replay-day]");
  const play = page.locator("[data-replay-play]");
  const motion = page.locator("[data-reduce]");
  const pause = page.locator("[data-pause]");
  const speed = page.locator("[data-speed]");
  const skip = page.locator("[data-skip]");
  const formatCents = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
  const dollars = cents => formatCents.format(cents / 100);

  await page.locator('[data-research-trace="fixed_order"]').first().click();
  assert.equal(await replayView.getAttribute("aria-pressed"), "true");
  const importedSource = await source.inputValue();
  assert.match(importedSource, /^research-/);
  const episode = bundle.episodes.find(record => record.controller_id === "fixed_order");
  const allSources = await source.locator("option").evaluateAll(options => options.map(option => option.value));
  for (const oldSource of ["live", "demo-none", "demo-always", "demo-rules"]) {
    assert.ok(allSources.includes(oldSource), `Missing existing replay source ${oldSource}`);
  }

  const selectedDay = await day.inputValue();
  assert.equal(await day.locator("option").count(), bundle.run.config.days);
  const record = episode.days[Number(selectedDay)];
  const close = record.settlement;
  const recipe = await page.locator("[data-replay-reason]").innerText();
  assert.match(recipe, /Public demand estimates/);
  assert.ok(recipe.includes(`${record.public_today} units today, ${record.public_tomorrow} tomorrow`));
  assert.doesNotMatch(recipe, /Realized demand/);
  assert.ok((await page.locator("[data-replay-event]").innerText()).includes(episode.input_id));
  const ledger = await page.locator("[data-replay-ledger]").innerText();
  assert.ok(ledger.includes(`${dollars(record.opening_cash_cents)} → ${dollars(close.cash_cents)}`));
  assert.ok(ledger.includes(`${close.received_units} / ${close.ordered_units} / ${close.in_transit_units}`));
  await waitForText(page, "[data-tool-trace]", /market report|demand forecast/i);
  assert.equal(await page.locator("[data-replay-truth]").isVisible(), false);
  await page.locator(".sw-after-fact summary").click();
  await waitForText(page, "[data-replay-truth]", /actual|realized/i);
  assert.ok((await page.locator("[data-replay-truth]").innerText()).includes(`Realized demand: ${record.demand} units.`));

  await motion.uncheck();
  await speed.selectOption("1");
  await play.click();
  await page.locator('.sw-world[aria-busy="true"]').waitFor();
  await pause.click();
  await waitForText(page, "[data-pause]", /^Resume$/);
  await speed.selectOption("4");
  await toggleLanguage.click();
  await waitForLanguage(page, "zh-CN");
  assert.equal(await replayView.getAttribute("aria-pressed"), "true");
  assert.equal(await source.inputValue(), importedSource);
  assert.equal(await day.inputValue(), selectedDay);
  assert.equal(await speed.inputValue(), "4");
  assert.equal(await page.locator('.sw-world').getAttribute("aria-busy"), "true");
  await toggleLanguage.click();
  await waitForLanguage(page, "en");
  await waitForText(page, "[data-pause]", /^Resume$/);
  await pause.click();
  await skip.click();
  await page.locator('.sw-world[aria-busy="false"]').waitFor();

  await motion.check();
  await play.click();
  await page.locator('.sw-world[aria-busy="false"]').waitFor();
  assert.equal(await motion.isChecked(), true);
  assert.equal(await pause.isDisabled(), true);
  assert.equal(await source.inputValue(), importedSource);
  assert.equal(await day.inputValue(), selectedDay);

  const terminalDay = bundle.run.config.days - 1;
  await day.selectOption(String(terminalDay));
  await waitForText(page, "[data-replay-reason]", /final day records delivery, sales, and settlement/i);
  await waitForText(page, "[data-tool-trace]", /No paid tools were called/);
  assert.equal(await page.locator("[data-replay-next]").isDisabled(), true);
  await page.locator("[data-replay-prev]").click();
  assert.equal(await day.inputValue(), String(terminalDay - 1));
  await page.locator("[data-replay-next]").click();
  assert.equal(await day.inputValue(), String(terminalDay));

  await source.selectOption("demo-rules");
  await play.click();
  await page.locator('.sw-world[aria-busy="false"]').waitFor();
  assert.equal(await source.inputValue(), "demo-rules");
  await source.selectOption("live");
  assert.equal(await day.locator("option").count(), 3);
  await page.locator('[data-view="shop"]').click();
}

async function main() {
  const bundle = JSON.parse(readFileSync(bundlePath, "utf-8"));
  const browser = await chromium.launch({
    executablePath: browserExecutable(),
    headless: true,
    timeout: 15_000,
    args: ["--disable-crash-reporter", "--disable-breakpad"],
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    page.setDefaultTimeout(10_000);
    page.setDefaultNavigationTimeout(15_000);
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.route("https://unpkg.com/**", route => route.abort());
    await page.goto(pathToFileURL(join(root, "index.html")).href);
    await waitForLanguage(page, "en");
    await waitForText(page, '[data-view="shop"]', /^Warehouse$/);

    const before = await stageLiveStore(page);
    await testResearchImport(page, bundle);
    await testReplay(page, bundle);
    const after = await liveSnapshot(page);
    assert.deepEqual(after, before);
    assert.deepEqual(errors, []);
    console.log("Browser research import, validation, bilingual replay, and live-store isolation passed.");
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
