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


// ── How big a split is (WI-002401) ────────────────────────────────────────────
// The reported case: 60/59220 takes 7 passengers, the card has 17 staff, and the run
// it is dropped on already carries 3. The split used to be sized on the bus (keep 7),
// which came back still 3 over the run and was then refused. It is sized on the seats
// free ON THAT RUN.
const BUS = { id: 'BUS', label: '60/59220, Pajero', max_passenger_capacity: 7 };
rule.planData = { vehicles: [BUS] };
rule.passengerSeats = (v) => v.max_passenger_capacity;

const RUN = { id: 'RUN', tripId: 'T-RUN', tripName: 'S-106', occupancy: 3, headcount: 3,
    window: rule._dayWindow.call(rule, '2026-09-07T02:30:00Z', '2026-09-07T03:05:00Z'),
    stops: [{ id: 's106a', direction: 'OUTBOUND', headcount: 3, stopIndex: 1 }] };
rule._getLogicalTrips = () => [RUN];

assert.strictEqual(rule._seatsAvailableFor({ headcount: 99 }, 'BUS', null), 7, 'a run of its own gets the whole bus');
assert.strictEqual(rule._seatsAvailableFor({ id: 'C', direction: 'OUTBOUND', headcount: 99 }, 'BUS', RUN.stops), 4, '7 seats less the 3 already on S-106');

// A concurrent run takes seats off the total too.
const OVERLAP = { id: 'X', tripId: 'T-X', tripName: 'S-999', occupancy: 2, headcount: 2,
    window: rule._dayWindow.call(rule, '2026-09-07T02:45:00Z', '2026-09-07T03:30:00Z'),
    stops: [{ id: 'x1', direction: 'OUTBOUND', headcount: 2, stopIndex: 1 }] };
rule._getLogicalTrips = () => [RUN, OVERLAP];
assert.ok(rule._sharesTheRoad(RUN.window, OVERLAP.window), 'these two overlap');
assert.strictEqual(rule._seatsAvailableFor({ id: 'C', direction: 'OUTBOUND', headcount: 99 }, 'BUS', RUN.stops), 2, '7 less 3 on the run less 2 sharing the road');

// The gate: offered when the card is over the seats it can have, not over the bus.
rule._getLogicalTrips = () => [RUN];
let offered = null;
rule._openSplitModal = (card, vehicle, opts) => { offered = { card, opts }; };

const card17 = { id: 'C', headcount: 17, direction: 'OUTBOUND' };
assert.strictEqual(rule._splitIfOver(card17, BUS, RUN.stops, () => {}), true);
assert.strictEqual(offered.opts.free, 4,
    'the modal is handed 4 - not the 7 the bus takes');

// A card of 5 fits the BUS but not the RUN: it used to fall through the gate entirely
// and get refused later with a flat capacity error.
offered = null;
const card5 = { id: 'D', headcount: 5, direction: 'OUTBOUND' };
assert.strictEqual(rule._splitIfOver(card5, BUS, RUN.stops, () => {}), true,
    '5 is under the 7-seat bus but over the 4 seats free on the run');
assert.ok(offered, 'so the split is offered rather than a refusal');

// And a card that genuinely fits is left alone.
offered = null;
assert.strictEqual(rule._splitIfOver({ id: 'E', headcount: 4 }, BUS, RUN.stops, () => {}), false);
assert.strictEqual(offered, null, 'no dialog for a card that fits');


// ── A return card boards the seats the outward load has left (WI-002401) ──────
// The reported case: a run whose outbound legs already fill the bus must still accept
// a return card. Subtracting the run's peak said zero seats and put a split, or a
// "No Seats Free", in front of a merge that fits perfectly well.
rule.cardOwnDirection = (i) => (i.direction === 'RETURN' ? 'RETURN' : 'OUTBOUND');
rule.tripOccupancy = function (trip) {
    if (trip.direction !== 'MIXED') return trip.headcount;
    const stops = this._inRunOrder(trip.stops);
    const boards = (i) => this.cardOwnDirection(i) === 'RETURN';
    let onBoard = stops.reduce((n, s) => n + (boards(s) ? 0 : (s.headcount || 0)), 0);
    let peak = onBoard;
    stops.forEach(s => {
        onBoard += boards(s) ? (s.headcount || 0) : -(s.headcount || 0);
        peak = Math.max(peak, onBoard);
    });
    return peak;
};
rule._inRunOrder = (items) => [...items].sort(
    (a, b) => (new Date(a.start) - new Date(b.start)) || (a.stopIndex || 0) - (b.stopIndex || 0));

// 7-seat bus, an outbound run carrying all 7 - completely full outbound.
const FULL = { id: 'FULL', tripId: 'T-FULL', tripName: 'S-201', occupancy: 7, headcount: 7,
    window: rule._dayWindow.call(rule, '2026-09-07T02:30:00Z', '2026-09-07T03:05:00Z'),
    stops: [{ id: 'f1', direction: 'OUTBOUND', headcount: 7, stopIndex: 1,
              start: '2026-09-07T02:30:00Z' }] };
rule._getLogicalTrips = () => [FULL];

const ret3 = { id: 'R', direction: 'RETURN', headcount: 3 };
assert.strictEqual(rule._seatsAvailableFor(ret3, 'BUS', FULL.stops), 3,
    'all 3 returning riders fit a bus that is full outbound');
assert.strictEqual(rule._splitIfOver(ret3, BUS, FULL.stops, () => {}), false,
    'so no split modal, and no "No Seats Free"');

// A full busload of returning riders also fits; one more does not.
assert.strictEqual(rule._seatsAvailableFor({ id: 'R', direction: 'RETURN', headcount: 7 },
    'BUS', FULL.stops), 7);
assert.strictEqual(rule._seatsAvailableFor({ id: 'R', direction: 'RETURN', headcount: 9 },
    'BUS', FULL.stops), 7, 'capped at the bus, and split rather than refused');

// An OUTBOUND card onto the same full run still cannot ride - those riders DO share it.
assert.strictEqual(rule._seatsAvailableFor({ id: 'O', direction: 'OUTBOUND', headcount: 3 },
    'BUS', FULL.stops), 0, 'nothing outbound fits a bus that is already full outbound');

// A run that already mixes: 4 out, 2 back. A further return card has the seats the
// outward load leaves, not what is spare beside its peak.
const MIX = { id: 'MIX', tripId: 'T-MIX', tripName: 'S-301', occupancy: 4, headcount: 6,
    window: rule._dayWindow.call(rule, '2026-09-07T02:30:00Z', '2026-09-07T03:05:00Z'),
    stops: [{ id: 'm1', direction: 'OUTBOUND', headcount: 4, stopIndex: 1,
              start: '2026-09-07T02:30:00Z' },
            { id: 'm2', direction: 'RETURN', headcount: 2, stopIndex: 2,
              start: '2026-09-07T02:45:00Z' }] };
rule._getLogicalTrips = () => [MIX];
assert.strictEqual(rule._seatsAvailableFor({ id: 'R2', direction: 'RETURN', headcount: 5 },
    'BUS', MIX.stops), 5, '2 already aboard on the way home plus 5 more is 7');
assert.strictEqual(rule._seatsAvailableFor({ id: 'R2', direction: 'RETURN', headcount: 6 },
    'BUS', MIX.stops), 5, 'the sixth would make 8 on a 7-seat bus');

console.log('seat rule OK');
