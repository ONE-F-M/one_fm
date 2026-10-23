/**
 * Self-check for the Employee Traceability Matrix filter predicate.
 *
 *   node test_matrix_filter.js
 *
 * matrixMatches is read out of transportation_schedule.js between its two banner
 * comments (together with normalizeSearchText, which it uses) rather than copied,
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
    + slice('// \u2500\u2500 Traceability matrix filter \u2500\u2500', '// \u2500\u2500 End traceability matrix filter');

// eslint-disable-next-line no-new-func
const matrixMatches = new Function(body + '\nreturn matrixMatches;')();

const none = { shift: '', accommodation: '', project: '', q: '', issuesOnly: false };
const f = (over) => Object.assign({}, none, over);

const rows = {
    assigned: { id: 'HR-EMP-1', name: 'Samir  Basnet', designation: 'Driver', project: 'Alpha',
                roster_shift: 'Morning', camp: 'Camp A', room: '12', status: 'Assigned' },
    pool:     { id: 'HR-EMP-2', name: 'Asha Rai', designation: 'Cleaner', project: 'Beta',
                roster_shift: 'Night', camp: 'Camp B', status: 'Pool' },
    missing:  { id: 'HR-EMP-3', name: 'Ravi Kumar', designation: 'Guard', project: 'Alpha',
                roster_shift: 'Morning', camp: '', status: 'Missing', is_reliever: 1,
                reliever_name: 'Bina Thapa' },
    exempt:   { id: 'HR-EMP-4', name: 'Lena Cruz', designation: 'Nurse', project: 'Beta',
                roster_shift: 'Night', camp: 'Camp A', status: 'Exempt' },
    stale:    { id: 'HR-EMP-5', name: 'Omar Ali', designation: 'Driver', project: 'Alpha',
                roster_shift: 'Night', camp: 'Camp B', status: 'Stale' },
};
const all = Object.values(rows);
const ids = (filters) => all.filter(r => matrixMatches(r, filters)).map(r => r.id);

// No filters keeps everything; a missing row or filter object never throws.
assert.strictEqual(ids(none).length, 5, 'no filters shows every row');
assert.strictEqual(matrixMatches(null, none), true);
assert.strictEqual(matrixMatches(rows.pool, null), true);

// Issues-only isolates Missing and Stale and nothing else.
assert.deepStrictEqual(ids(f({ issuesOnly: true })), ['HR-EMP-3', 'HR-EMP-5']);

// Each dropdown filters exactly.
assert.deepStrictEqual(ids(f({ shift: 'Night' })), ['HR-EMP-2', 'HR-EMP-4', 'HR-EMP-5']);
assert.deepStrictEqual(ids(f({ project: 'Beta' })), ['HR-EMP-2', 'HR-EMP-4']);
assert.deepStrictEqual(ids(f({ accommodation: 'Camp A' })), ['HR-EMP-1', 'HR-EMP-4']);
assert.deepStrictEqual(ids(f({ accommodation: 'Live-Out' })), ['HR-EMP-3'], 'no camp means Live-Out');

// The universal search covers name (flattened), id, designation and reliever.
assert.deepStrictEqual(ids(f({ q: 'samir basnet' })), ['HR-EMP-1'], 'doubled stored space is flattened');
assert.deepStrictEqual(ids(f({ q: ' hr-emp-4 ' })), ['HR-EMP-4'], 'id, case and edge spaces ignored');
assert.deepStrictEqual(ids(f({ q: 'driver' })), ['HR-EMP-1', 'HR-EMP-5'], 'designation');
assert.deepStrictEqual(ids(f({ q: 'bina' })), ['HR-EMP-3'], 'reliever name');
assert.deepStrictEqual(ids(f({ q: 'reliever' })), ['HR-EMP-3'], 'reliever flag');
assert.deepStrictEqual(ids(f({ q: 'nobody' })), []);

// Every filter ANDs with the others.
assert.deepStrictEqual(ids(f({ shift: 'Night', project: 'Alpha', issuesOnly: true })), ['HR-EMP-5']);
assert.deepStrictEqual(ids(f({ accommodation: 'Camp B', q: 'driver' })), ['HR-EMP-5']);

console.log('matrix filter OK');
