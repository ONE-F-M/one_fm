/**
 * Self-check for the pool search normaliser.
 *
 *   node test_search_normalize.js
 *
 * normalizeSearchText is read out of transportation_schedule.js between its two
 * banner comments rather than copied, so this fails if the shipped helper changes.
 * Stored employee names carry doubled, leading and trailing spaces ("Samir  Basnet"),
 * and the Employee name filter has to find them from what a dispatcher types.
 */
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = fs.readFileSync(path.join(__dirname, 'transportation_schedule.js'), 'utf8');
const from = src.indexOf('// ── Search text normalising ──');
const to = src.indexOf('// ── End search text normalising');
assert.ok(from >= 0 && to > from, 'search normaliser not found - did the banners move?');

// eslint-disable-next-line no-new-func
const normalizeSearchText = new Function(src.slice(from, to) + '\nreturn normalizeSearchText;')();

// The filter's rule: both sides flattened, then a substring match.
const matches = (stored, typed) =>
    normalizeSearchText(stored).includes(normalizeSearchText(typed));

assert.ok(matches('Samir  Basnet', 'Samir Basnet'), 'one typed space finds a doubled stored space');
assert.ok(matches('Samir  Basnet', ' samir '), 'leading and trailing typed spaces are ignored');
assert.ok(matches('  Samir Basnet ', 'samir basnet'), 'stored leading/trailing spaces are ignored');
assert.ok(matches('Samir\tBasnet', 'samir basnet'), 'any whitespace run counts as one space');
assert.ok(!matches('Samir  Basnet', 'samirbasnet'), 'no space at all is a different name');

// Missing values never throw and never match a real query.
assert.strictEqual(normalizeSearchText(null), '');
assert.strictEqual(normalizeSearchText(undefined), '');
assert.ok(!matches(null, 'samir'));

console.log('search normaliser OK');
