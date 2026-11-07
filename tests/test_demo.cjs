// Run with: node --test tests/test_demo.cjs
// Executes the actual inline model code; this is not a browser/layout test.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../demo/index.html'), 'utf8');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map(m => m[1]);
assert.equal(scripts.length, 3, 'Expected the dashboard, copy update, and AI workbench scripts');
const coreEnd = scripts[0].indexOf('\nfunction line(');
const explainEnd = scripts[2].indexOf('\n(() => {');
assert.ok(coreEnd > 0 && explainEnd > 0, 'Model extraction boundaries must exist');

function context() {
  const fields = { indoor: { value: '27.4' }, comfort: { value: '27.5' } };
  const ctx = vm.createContext({ document: { getElementById: id => fields[id] } });
  vm.runInContext(scripts[0].slice(0, coreEnd), ctx);
  vm.runInContext(scripts[2].slice(0, explainEnd), ctx);
  return ctx;
}
const run = (ctx, source) => vm.runInContext(source, ctx, { timeout: 10000 });
const plain = value => JSON.parse(JSON.stringify(value));
const close = (actual, expected, tolerance = 1e-9) =>
  assert.ok(Math.abs(actual - expected) < tolerance, `${actual} differs from ${expected}`);

test('all shipped inline JavaScript parses', () => {
  scripts.forEach((source, i) => new vm.Script(source, { filename: `inline-script-${i + 1}.js` }));
});

test('training is reproducible and purges examples crossing the time split', () => {
  const ctx = context();
  const first = plain(run(ctx, 'trainModels(30, 17)'));
  const second = plain(run(ctx, 'trainModels(30, 17)'));
  assert.deepEqual(first, second);
  assert.equal(Object.values(first.models).reduce((n, model) => n + model.w.length, 0), 39);
  for (const h of [2, 4, 6]) {
    const model = first.models[h];
    assert.equal(model.trainN, 4 * (12 * 96 - h * 4 - 8));
    assert.equal(model.testN, 4 * (4 * 96 - h * 4));
    assert.equal(model.mean.length, 12);
    assert.equal(model.sd.length, 12);
    assert.ok(model.sd.every(v => Number.isFinite(v) && v > 0));
    assert.ok(model.w.every(Number.isFinite));
    for (const metric of ['mae', 'regional', 'persistence']) {
      assert.ok(Number.isFinite(model[metric]) && model[metric] >= 0);
    }
  }
});

test('explanation reconstructs the forecast for every node and horizon', () => {
  const ctx = context();
  const results = run(ctx, `
    bundle = trainModels(30, 17);
    nodes.flatMap(node => [2, 4, 6].flatMap(h => [-100, 0, 2, 100].map(offset => {
      const x = vector({offset, trend: .2, hour: 13, macro: 31, rh: 55}, h, 33, node);
      const explanation = aeroclimExplain(bundle.models[h], x, 33);
      return {explanation, raw: predict(bundle.models[h], x)};
    })))
  `);
  for (const { explanation: e, raw } of results) {
    close(e.raw, raw);
    close(e.groups.reduce((sum, group) => sum + group.value, 0), e.terms.reduce((a, b) => a + b, 0));
    close(33 + e.intercept + e.groups.reduce((sum, group) => sum + group.value, 0) + e.clipping, e.prediction);
    close(e.prediction, 33 + Math.max(-4, Math.min(12, raw)));
  }
  assert.throws(() => run(ctx, 'aeroclimExplain(bundle.models[2], [1], 33)'), /feature mapping/);
});

test('six-hour plans obey the thermal model and account for energy and tariffs', () => {
  const ctx = context();
  for (const outdoor of [Array(24).fill(22), Array(24).fill(38), Array.from({ length: 24 }, (_, i) => 28 + i / 3)]) {
    ctx.outdoor = outdoor;
    const plan = run(ctx, 'controlPlan(outdoor, 27.4, 27.5)');
    assert.equal(plan.price.length, 24);
    for (const kind of ['smart', 'reactive']) {
      const schedule = plan[kind];
      assert.equal(schedule.actions.length, 24);
      assert.equal(schedule.temps.length, 25);
      close(schedule.temps[0], 27.4);
      let energy = 0, cost = 0, hot = 0;
      for (let i = 0; i < 24; i++) {
        const u = schedule.actions[i];
        assert.ok([0, .5, 1].includes(u));
        const expected = schedule.temps[i] + .25 * ((outdoor[i] - schedule.temps[i]) / 4 + .15 - 2.6 * u);
        close(schedule.temps[i + 1], expected);
        const e = .25 * 2.2 * u;
        energy += e;
        cost += e * (i >= 8 && i < 16 ? 14 : 8);
        hot += expected > 27.5 ? .25 : 0;
      }
      close(schedule.kwh, energy);
      close(schedule.cost, cost);
      close(schedule.hot, hot);
    }
  }
});

test('spike detection needs two consecutive unusual readings', () => {
  const ctx = context();
  assert.equal(run(ctx, 'anomaly(Array(22).fill(30)).flag'), false);
  assert.equal(run(ctx, 'anomaly([...Array(20).fill(30), 34]).flag'), false);
  assert.equal(run(ctx, 'anomaly([...Array(20).fill(30), 34, 34]).flag'), true);
  assert.equal(run(ctx, 'anomaly([...Array(20).fill(30), 34, 30]).flag'), false);
});

test('scenario calculations connect learned horizon points to the planner', () => {
  const ctx = context();
  run(ctx, 'bundle = trainModels(30, 17)');
  for (const scenario of ['baseline', 'heatwave', 'pocket']) {
    ctx.scenario = scenario;
    const result = run(ctx, 'state.scenario = scenario; calculate()');
    assert.equal(result.rows.length, 4);
    for (const row of result.rows) {
      assert.equal(row.curve.length, 25);
      assert.ok(row.curve.every(Number.isFinite));
      for (const point of row.points) close(row.curve[point.t * 4], point.value);
    }
    if (scenario === 'pocket') assert.equal(result.rows[0].anomaly.flag, true);
    assert.equal(result.plan.smart.actions.length, 24);
  }
});

test('weather interpolation uses forecast timestamps and rejects out-of-range times', () => {
  const ctx = context();
  run(ctx, `weather = {current: {time: 1800}, hourly: {
    time: [0, 3600, 7200], temperature_2m: [20, 24, 22]
  }}`);
  close(run(ctx, 'weatherValue("temperature_2m", 0)'), 22);
  close(run(ctx, 'weatherValue("temperature_2m", 1)'), 23);
  assert.equal(run(ctx, 'weatherValue("temperature_2m", 2)'), null);
  assert.equal(run(ctx, 'weatherValue("temperature_2m", -1)'), null);
});
