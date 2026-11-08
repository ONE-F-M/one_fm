/**
 * Self-check for the shared card / block filter predicate.
 *
 *   node test_card_filter.js
 *
 * cardMatchesFilters and blockMatchesFilters are read out of transportation_schedule.js
 * between their banner comments (together with normalizeSearchText) rather than copied,
 * so this fails if the shipped predicate changes.
 */
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = fs.readFileSync(path.join(__dirname, 'transportation_schedule.js'), 'utf8');
const slice = (open, close) => {
    const from = src.indexOf(open);
    const to = src.indexOf(close);
    assert.ok(from >= 0 && to > from, `${open} not found - did the banners move?`);
    return src.slice(from, to);
};

const body = slice('// \u2500\u2500 Search text normalising \u2500\u2500', '// \u2500\u2500 End search text normalising')
    + slice('// \u2500\u2500 Card filter \u2500\u2500', '// \u2500\u2500 End card filter');

// eslint-disable-next-line no-new-func
const { cardMatchesFilters, blockMatchesFilters } =
    new Function(body + '\nreturn { cardMatchesFilters, blockMatchesFilters };')();

const none = { q: '', emp: '', shift: '', shiftExact: false, shiftStart: '', shiftEnd: '' };
const f = (over) => Object.assign({}, none, over);

const cards = {
    a: { id: 'A', shift_name: 'Security-AUM-Day-1', site_location: 'Airport T4', accommodation: 'Camp A',
         stop_location: 'Gate 1', direction: 'OUTBOUND', shift_start: '07:00', shift_end: '15:00',
         employees: [{ name: 'Samir  Basnet' }, { name: 'Asha Rai' }] },
    b: { id: 'B', shift_name: 'Security-AUM-Day-11', site_location: 'Mall', accommodation: 'Camp B',
         stop_location: 'Dock', direction: 'RETURN', shift_start: '07:00', shift_end: '00:00',
         employees: [{ name: 'Ravi Kumar' }] },
    c: { id: 'C', shift_name: 'Cashier-Night-1', site_location: 'Hotel', accommodation: 'Camp A',
         stop_location: '', direction: 'OUTBOUND', shift_start: '22:00', shift_end: '06:00' },
};
const all = Object.values(cards);
const ids = (filters) => all.filter(c => cardMatchesFilters(c, filters)).map(c => c.id);

// No filters keeps everything; a missing card or filter object never throws.
assert.deepStrictEqual(ids(none), ['A', 'B', 'C']);
assert.strictEqual(cardMatchesFilters(null, none), true);
assert.strictEqual(cardMatchesFilters(cards.a, null), true);

// Text filters are case-insensitive "contains" with spaces flattened.
assert.deepStrictEqual(ids(f({ q: 'AIRPORT' })), ['A'], 'site, any case');
assert.deepStrictEqual(ids(f({ q: 'camp a' })), ['A', 'C'], 'accommodation');
assert.deepStrictEqual(ids(f({ q: 'return' })), ['B'], 'direction');
assert.deepStrictEqual(ids(f({ q: 'gate' })), ['A'], 'stop location');
assert.deepStrictEqual(ids(f({ emp: 'samir basnet' })), ['A'], 'doubled stored space is flattened');
assert.deepStrictEqual(ids(f({ emp: ' RAV ' })), ['B'], 'partial rider, edge spaces ignored');
assert.deepStrictEqual(ids(f({ emp: 'nobody' })), [], 'a card with no riders never matches a rider filter');

// A typed shift narrows by contains; a picked one is exact.
assert.deepStrictEqual(ids(f({ shift: 'aum-day-1' })), ['A', 'B'], 'typed text is partial');
assert.deepStrictEqual(ids(f({ shift: 'Security-AUM-Day-1', shiftExact: true })), ['A'], 'picked name is exact');

// The two time selects are exact.
assert.deepStrictEqual(ids(f({ shiftStart: '07:00' })), ['A', 'B']);
assert.deepStrictEqual(ids(f({ shiftEnd: '00:00' })), ['B']);

// Every filter ANDs with the others.
assert.deepStrictEqual(ids(f({ shiftStart: '07:00', q: 'mall' })), ['B']);
assert.deepStrictEqual(ids(f({ shiftStart: '07:00', emp: 'asha', shiftEnd: '15:00' })), ['A']);
assert.deepStrictEqual(ids(f({ q: 'camp a', emp: 'ravi' })), [], 'AND, not OR');

// A block matches when any one of its cards matches; an empty block never does.
assert.strictEqual(blockMatchesFilters([cards.b, cards.c], f({ q: 'hotel' })), true);
assert.strictEqual(blockMatchesFilters([cards.b, cards.c], f({ emp: 'ravi', q: 'hotel' })), false,
    'criteria AND within one card, they are not spread across the block');
assert.strictEqual(blockMatchesFilters([], f({ q: 'x' })), false);
assert.strictEqual(blockMatchesFilters(null, none), false);
// A fallback card (a plan item whose card left the pool) still matches on its site.
assert.strictEqual(blockMatchesFilters([{ site_location: 'Depot', shift_name: '\u2014' }], f({ q: 'depot' })), true);

console.log('card filter OK');
