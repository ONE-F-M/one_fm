/**
 * Self-check for the lobby board rules.
 *
 *   node test_board_rules.js
 *
 * The helpers are read out of transportation_schedules_board.js, so this fails if the
 * shipped rules change.
 */
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const src = fs.readFileSync(path.join(__dirname, "transportation_schedules_board.js"), "utf8");
const from = src.indexOf("// ── Board rules");
const to = src.indexOf("// ── End of board rules");
assert.ok(from >= 0 && to > from, "board rules block not found - did the banners move?");
const block = src.slice(from, to);

global.__ = (text, args) => text.replace(/\{(\d+)\}/g, (m, i) => args[i]);
const load = (code) => new Function(code + "\nreturn { visibleTrips, statusText, countdownText, layoutFor, windowLabel, emptyText, naiveMs };")();

const R = load(block);
const at = (hhmm) => R.naiveMs(`2026-11-25 ${hhmm}:00`);
const trip = (dep, qoa) => ({
	key: dep, departure: `2026-11-25T${dep}:00`, qoa: qoa || null, qoa_at: qoa ? `2026-11-25T${qoa}:00` : null,
});
const keys = (list) => list.map((t) => t.key);

// AC10 / AC11: window 14:07 -> 16:07, departed kept for 15 minutes.
const trips = [trip("16:08"), trip("14:00"), trip("16:07"), trip("15:00")];
assert.deepStrictEqual(keys(R.visibleTrips(trips, at("14:07"))), ["14:00", "15:00", "16:07"]);
assert.strictEqual(R.countdownText(trip("14:00"), at("14:07")), "Departed 7 min ago");
assert.strictEqual(R.statusText(trip("14:00"), at("14:07")), "Departed");
assert.ok(R.visibleTrips([trip("14:00")], at("14:15")).length === 1, "still shown at 15 minutes");
assert.deepStrictEqual(R.visibleTrips([trip("14:00")], at("14:16")), []);
assert.strictEqual(R.windowLabel(at("14:07")), "14:07 → 16:07");
assert.strictEqual(R.windowLabel(at("14:30")), "14:30 → 16:30");

// Countdown wording.
assert.strictEqual(R.countdownText(trip("14:30"), at("14:07")), "Departs in 23 min");
assert.strictEqual(R.countdownText(trip("15:12"), at("14:07")), "Departs in 1 h 5 min");

// AC13: QoA 14:00, departure 14:45.
const t = trip("14:45", "14:00");
assert.strictEqual(R.statusText(t, at("13:59")), "Scheduled");
assert.strictEqual(R.statusText(t, at("14:00")), "QoA 14:00");
assert.strictEqual(R.statusText(t, at("14:25")), "Boarding now");
assert.strictEqual(R.statusText(t, at("14:45")), "Departed");

// The AC's own values (QoA 14:15, departure 14:30): Boarding wins from 14:10.
const ac = trip("14:30", "14:15");
assert.strictEqual(R.statusText(ac, at("14:09")), "Scheduled");
assert.strictEqual(R.statusText(ac, at("14:10")), "Boarding now");

// AC12: one constant moves the filter, the label and the empty text together.
assert.strictEqual(R.emptyText().en, "No departures in the next 2 hours");
const hour = load(block.replace("const WINDOW_MINUTES = 120;", "const WINDOW_MINUTES = 60;"));
assert.deepStrictEqual(keys(hour.visibleTrips(trips, at("14:07"))), ["14:00", "15:00"]);
assert.strictEqual(hour.windowLabel(at("14:07")), "14:07 → 15:07");
assert.strictEqual(hour.emptyText().en, "No departures in the next hour");

// AC19: layout by headcount.
assert.deepStrictEqual([0, 1, 2, 6, 7].map(R.layoutFor), ["empty", "single", "pair", "pair", "grid"]);

console.log("board rules: ok");
