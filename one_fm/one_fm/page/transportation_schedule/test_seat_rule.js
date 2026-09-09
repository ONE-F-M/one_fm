/**
 * Self-check for the canvas seat rule (WI-002401 AC5).
 *
 *   node test_seat_rule.js
 *
 * The helpers are read out of transportation_schedule.js itself rather than copied,
 * so this fails if the shipped rule changes. It mirrors _peak_concurrent_headcount /
 * _trips_share_the_road on the server (tested in test_route_plan.py) - the two must
 * not be able to disagree about whether a run fits, or the canvas accepts a drop the
 * save then refuses.
 */
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = fs.readFileSync(path.join(__dirname, 'transportation_schedule.js'), 'utf8');
const from = src.indexOf('            // ── When two runs are on the road together');
const to = src.indexOf('            // ── Time-aware peak load helper');
assert.ok(from > 0 && to > from, 'seat-rule helpers not found - did the banners move?');

// eslint-disable-next-line no-eval
const rule = eval('({' + src.slice(from, to) + '})');

// Stubs for the two collaborators the rule calls out to. A single-direction run
// carries the sum of its stops; that is all these tests need.
rule.runDirection = (stops) => {
    const first = stops[0].direction || 'OUTBOUND';
    return stops.some(s => (s.direction || 'OUTBOUND') !== first) ? 'MIXED' : first;
};
rule.tripOccupancy = (trip) => trip.headcount;

const trip = (name, from_, to_, occupancy) => ({
    tripId: name, tripName: name, occupancy,
    window: rule._dayWindow.call(rule, from_, to_),
    stops: [{ id: name + '_1' }]
});

// The AC's own scenario, on a 7-seat bus: S-106 05:30-06:05 with 2 aboard and
// S-102 06:35-08:20 with 5. Stamps are UTC and the site runs at UTC+3.
const S106 = trip('S-106', '2026-09-07T02:30:00Z', '2026-09-07T03:05:00Z', 2);
const S102 = trip('S-102', '2026-09-07T03:35:00Z', '2026-09-07T05:20:00Z', 5);
rule._getLogicalTrips = () => [S106, S102];

// The clock is read in the site's own time zone, so the board and the rule agree.
assert.strictEqual(S106.window.from, 5 * 3600 + 30 * 60, 'S-106 leaves at 05:30 local');
assert.strictEqual(S102.window.to, 8 * 3600 + 20 * 60, 'S-102 is back by 08:20 local');

// Sequential runs never see each other.
assert.ok(!rule._sharesTheRoad(S106.window, S102.window), 'S-106 and S-102 are sequential');

// A 6th passenger onto S-102 fits; so does a 3rd onto S-106. Adding the two runs
// together made both of them 8 on a 7-seat bus and refused a free seat.
assert.strictEqual(rule.seatLoad('BUS', 6, { joining: S102.stops }).total, 6);
assert.strictEqual(rule.seatLoad('BUS', 3, { joining: S106.stops }).total, 3);

// Runs that really do share the road still add up.
const EARLY = trip('S-201', '2026-09-07T02:30:00Z', '2026-09-07T04:00:00Z', 2);
const LATE = trip('S-202', '2026-09-07T03:35:00Z', '2026-09-07T05:20:00Z', 5);
rule._getLogicalTrips = () => [EARLY, LATE];
assert.ok(rule._sharesTheRoad(EARLY.window, LATE.window), 'these two overlap');
assert.strictEqual(rule.seatLoad('BUS', 3, { joining: EARLY.stops }).total, 8);

// Midnight is 0, not 24 hours: some engines print "24:00:00" for it and that would
// put a run that leaves at midnight at the far end of the day.
assert.strictEqual(rule._clockSeconds('2026-09-06T21:00:00Z'), 0, 'Kuwait midnight is second 0');
assert.strictEqual(
    rule._dayWindow('2026-09-06T21:00:00Z', '2026-09-06T21:30:00Z').from, 0,
    'a run leaving at midnight starts the day'
);

// A run over midnight keeps its length instead of reading as zero, and still meets
// an early-morning run (22:00-01:00 against 00:30-01:30).
const NIGHT = trip('S-301', '2026-09-06T19:00:00Z', '2026-09-06T22:00:00Z', 4);
const DAWN = trip('S-302', '2026-09-06T21:30:00Z', '2026-09-06T22:30:00Z', 1);
assert.strictEqual(NIGHT.window.to - NIGHT.window.from, 3 * 3600, 'a night run is 3h long');
assert.ok(rule._sharesTheRoad(NIGHT.window, DAWN.window), 'a night run meets the small hours');

// A load starting a run of its own is judged on the window it will occupy, and a
// run nowhere near it has no say.
rule._getLogicalTrips = () => [S106, S102];
assert.strictEqual(
    rule.seatLoad('BUS', 4, { window: rule._dayWindow('2026-09-07T09:00:00Z', '2026-09-07T10:00:00Z') }).total,
    4, 'a midday run is not charged for the morning runs'
);

// A card joining a run going the other way is walked leg by leg, so the outward
// load it replaces does not count against it.
rule.tripOccupancy = (t) => {
    if (t.direction !== 'MIXED') return t.headcount;
    let onBoard = t.stops.filter(s => s.direction !== 'RETURN')
        .reduce((n, s) => n + (s.headcount || 0), 0);
    let peak = onBoard;
    t.stops.forEach(s => {
        onBoard += s.direction === 'RETURN' ? (s.headcount || 0) : -(s.headcount || 0);
        peak = Math.max(peak, onBoard);
    });
    return peak;
};
const outward = [{ id: 'a', direction: 'OUTBOUND', headcount: 5, stopIndex: 1 }];
assert.strictEqual(
    rule.mergedOccupancy(outward, { id: 'ret', direction: 'RETURN', headcount: 5 }),
    5, 'the returning load boards the seats the outward load has just left'
);
assert.strictEqual(
    rule.mergedOccupancy(outward, { id: 'more', direction: 'OUTBOUND', headcount: 5 }),
    10, 'two outward loads ride together'
);

console.log('seat rule OK');
