/**
 * Self-check for the timeline's "Group by" lane grouping.
 *
 *   node test_lane_grouping.js
 *
 * groupLaneRows is read out of transportation_schedule.js between its two banner
 * comments rather than copied, so this fails if the shipped rule changes.
 */
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = fs.readFileSync(path.join(__dirname, 'transportation_schedule.js'), 'utf8');
const open = '// \u2500\u2500 Lane grouping \u2500\u2500';
const close = '// \u2500\u2500 End lane grouping';
const from = src.indexOf(open);
const to = src.indexOf(close);
assert.ok(from >= 0 && to > from, `${open} not found - did the banners move?`);

// eslint-disable-next-line no-new-func
const groupLaneRows = new Function(src.slice(from, to) + '\nreturn groupLaneRows;')();

const DASH = '\u2014';
const vehicles = [
    { id: 'V1', type: 'Bus', accommodation: 'Mahboula Camp', location: 'Mahboula 1' },
    { id: 'V2', type: 'Van', accommodation: '', location: 'Abbasiya' },
    { id: 'V3', type: 'Bus', accommodation: 'Abbasiya Camp', location: 'Abbasiya' },
    { id: 'V4', type: '', accommodation: DASH, location: '' },
    { id: 'V5', type: 'Van', accommodation: 'Mahboula Camp', location: 'Mahboula 2' },
    { id: 'V6', type: DASH, accommodation: '', location: DASH },
];
const trips = { V1: 2, V2: 1, V3: 0, V4: 4, V5: 3 }; // V6 has no entry -> 0

const lanes = (rows) => rows.filter(r => r.type === 'lane').map(r => r.vehicle.id);
const groups = (rows) => rows.filter(r => r.type === 'group');

// None: lanes only, in the incoming order, no headers.
const flat = groupLaneRows(vehicles, '', trips);
assert.strictEqual(groups(flat).length, 0, 'no headers when ungrouped');
assert.deepStrictEqual(lanes(flat), ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']);
assert.deepStrictEqual(groupLaneRows(null, '', null), [], 'missing vehicles never throws');

// Location: accommodation first, location as the fallback, '\u2014' is blank.
const byLoc = groupLaneRows(vehicles, 'location', trips);
assert.deepStrictEqual(
    groups(byLoc).map(g => [g.name, g.vehicleCount, g.tripCount]),
    [['Abbasiya', 1, 1], ['Abbasiya Camp', 1, 0], ['Mahboula Camp', 2, 5], ['No location', 2, 4]],
    'location groups A-Z, blank last, with vehicle and trip counts');
assert.strictEqual(byLoc[0].type, 'group', 'a header leads the list');
assert.deepStrictEqual(lanes(byLoc), ['V2', 'V3', 'V1', 'V5', 'V4', 'V6'], 'lanes keep original order inside a group');
assert.strictEqual(groups(byLoc)[3].key, '', 'blank group has a blank key');

// Type.
const byType = groupLaneRows(vehicles, 'type', trips);
assert.deepStrictEqual(
    groups(byType).map(g => [g.name, g.vehicleCount, g.tripCount]),
    [['Bus', 2, 2], ['Van', 2, 4], ['No vehicle type', 2, 4]],
    'type groups A-Z, blank last, with vehicle and trip counts');
assert.deepStrictEqual(lanes(byType), ['V1', 'V3', 'V2', 'V5', 'V4', 'V6']);

// A header is immediately followed by exactly its own lanes.
byType.forEach((row, i) => {
    if (row.type === 'group') {
        const next = byType.slice(i + 1, i + 1 + row.vehicleCount);
        assert.ok(next.every(r => r.type === 'lane'), 'lanes follow their header');
    }
});

// Every vehicle appears exactly once in every mode.
['', 'location', 'type'].forEach(mode => {
    const ids = lanes(groupLaneRows(vehicles, mode, trips)).sort();
    assert.deepStrictEqual(ids, vehicles.map(v => v.id).sort(), `each vehicle once in mode "${mode}"`);
});

// Only blanks: a single "No ..." group.
const blanks = groupLaneRows([{ id: 'A', type: DASH }, { id: 'B' }], 'type', {});
assert.deepStrictEqual(groups(blanks).map(g => [g.name, g.vehicleCount, g.tripCount]), [['No vehicle type', 2, 0]]);

console.log('lane grouping OK');
