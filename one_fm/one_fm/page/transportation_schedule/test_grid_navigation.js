// Self-check for the grid navigation helpers (WI-004331). Run: node test_grid_navigation.js
// It slices the shipped helpers out of transportation_schedule.js by their banners
// rather than copying them, so a change to the real code is what gets tested.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(path.join(__dirname, 'transportation_schedule.js'), 'utf8');
const from = src.indexOf('// \u2500\u2500 Grid navigation');
const to = src.indexOf('// \u2500\u2500 End grid navigation');
assert.ok(from >= 0 && to > from, 'the Grid navigation banners are missing');
const { panWindow, snapScrollTop, workWindow } = new Function(
    src.slice(from, to) + '\nreturn { panWindow, snapScrollTop, workWindow };'
)();

const H = 3600000;
let passed = 0;
function check(name, fn) {
    fn();
    passed += 1;
    console.log('ok - ' + name);
}

// panWindow ------------------------------------------------------------------
const MIN = 0;
const MAX = 100 * H;

check('panWindow moves right by half the visible range', () => {
    const r = panWindow(10 * H, 30 * H, MIN, MAX, 0.5);
    assert.deepStrictEqual(r, { start: 20 * H, end: 40 * H });
});

check('panWindow moves left by half the visible range', () => {
    const r = panWindow(40 * H, 60 * H, MIN, MAX, -0.5);
    assert.deepStrictEqual(r, { start: 30 * H, end: 50 * H });
});

check('panWindow clamps at the lower bound and keeps the duration', () => {
    const r = panWindow(4 * H, 24 * H, MIN, MAX, -0.5);
    assert.strictEqual(r.start, MIN);
    assert.strictEqual(r.end - r.start, 20 * H);
});

check('panWindow clamps at the upper bound and keeps the duration', () => {
    const r = panWindow(70 * H, 90 * H, MIN, MAX, 0.5);
    assert.strictEqual(r.end, MAX);
    assert.strictEqual(r.end - r.start, 20 * H);
});

check('panWindow at an edge does not move', () => {
    assert.strictEqual(panWindow(MIN, 20 * H, MIN, MAX, -0.5).start, MIN);
    assert.strictEqual(panWindow(80 * H, MAX, MIN, MAX, 0.5).end, MAX);
});

check('panWindow with frac 0 only clamps (used to centre)', () => {
    assert.strictEqual(panWindow(-5 * H, 15 * H, MIN, MAX, 0).start, MIN);
    assert.strictEqual(panWindow(95 * H, 115 * H, MIN, MAX, 0).end, MAX);
});

// snapScrollTop --------------------------------------------------------------
const tops = [0, 121, 242, 363, 484, 605, 726, 847, 968, 1089];

check('snapScrollTop down picks the last row top within one viewport', () => {
    assert.strictEqual(snapScrollTop(tops, 0, 500, 1), 484);
    assert.strictEqual(snapScrollTop(tops, 484, 500, 1), 968);
});

check('snapScrollTop up picks the first row top within one viewport', () => {
    assert.strictEqual(snapScrollTop(tops, 968, 500, -1), 484);
    assert.strictEqual(snapScrollTop(tops, 484, 500, -1), 0);
});

check('snapScrollTop mid-row snaps to a boundary in both directions', () => {
    assert.strictEqual(snapScrollTop(tops, 300, 500, 1), 726);
    assert.strictEqual(snapScrollTop(tops, 300, 500, -1), 0);
});

check('snapScrollTop stops at 0 and at the last row', () => {
    assert.strictEqual(snapScrollTop(tops, 0, 500, -1), 0);
    assert.strictEqual(snapScrollTop(tops, 1089, 500, 1), 1089);
});

check('snapScrollTop still moves when a row is taller than the viewport', () => {
    assert.strictEqual(snapScrollTop(tops, 0, 50, 1), 121);
    assert.strictEqual(snapScrollTop(tops, 484, 50, -1), 363);
});

check('snapScrollTop does not depend on the order of the row tops', () => {
    assert.strictEqual(snapScrollTop(tops.slice().reverse(), 0, 500, 1), 484);
});

// workWindow -----------------------------------------------------------------
check('workWindow regression: planStart 2026-11-03T18:00Z is 2026-11-04 05:00-19:00 Kuwait', () => {
    const w = workWindow(Date.parse('2026-11-03T18:00:00Z'));
    assert.strictEqual(new Date(w.start).toISOString(), '2026-11-04T02:00:00.000Z');
    assert.strictEqual(new Date(w.end).toISOString(), '2026-11-04T16:00:00.000Z');
});

check('workWindow always starts after planStart (the old setUTCHours anchor ended before it)', () => {
    const planStart = Date.parse('2026-11-03T18:00:00Z');
    const w = workWindow(planStart);
    assert.ok(w.start > planStart && w.end - w.start === 14 * H);
});

console.log(passed + ' checks passed');
