# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002541: the five filters over the unassigned shipment pool.

The sidebar had two - a global text search and a shift START time. Finding one person, or
the cards for one shift, or the runs ending at 00:00, meant scrolling 551 cards.

Three things carry real risk here and are what these tests pin:

* **AND, not OR.** Five filters that ORed would widen the list as the dispatcher added
  criteria, which is the opposite of what narrowing means.
* **The option lists come from every UNASSIGNED card, not the filtered ones.** Built from
  the filtered set they would collapse to whatever is already selected, and a dispatcher
  could never change their mind without clearing first.
* **The sidebar has a fixed width.** Five controls in it only work if each one can shrink;
  a field that cannot gives the whole toolbar a horizontal scrollbar (AC1).

Browser-verified against the live board: employee "RAMA" -> 10 of 551, shift
"Admin-Airport Terminal 4-Morning-1" -> 2 of 551, that shift plus a nonsense employee
-> 0 (so they AND), and "Ends 00:00" -> 11 of 551.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))


class TestTheFiveFiltersExist(FrappeTestCase):
	"""AC1: three rows - global search, the two entity pickers, the two time pickers."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_each_filter_has_its_own_state(self):
		for field in ("searchQuery:", "employeeQuery:", "shiftFilter:",
					  "shiftStartFilter:", "shiftEndFilter:"):
			self.assertIn(field, self.canvas)

	def test_the_toolbar_is_laid_out_in_three_rows(self):
		self.assertEqual(self.canvas.count('<div class="rp-filter-row">'), 3)

	def test_every_field_can_shrink_inside_a_fixed_width_sidebar(self):
		# Without min-width:0 a flex item refuses to go below its content width, so one
		# long shift name pushes the row wider than the panel and the toolbar scrolls.
		self.assertIn(".rp-filter-field { position: relative; flex: 1 1 0; min-width: 0; }",
					  self.canvas)
		self.assertIn(".rp-filter-select { flex: 1 1 0; min-width: 0; cursor: pointer; }",
					  self.canvas)

	def test_long_values_ellipsize_rather_than_overflow(self):
		self.assertIn("text-overflow: ellipsis;", self.canvas)


class TestTheFiltersNarrowTogether(FrappeTestCase):
	"""AC5: strict AND across all five, and a counter that says so."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()
		cls.body = cls.canvas.split("filteredPoolCards() {", 1)[1].split("\n            },", 1)[0]

	def test_each_filter_rejects_on_its_own(self):
		# Every criterion returns false independently - that IS the AND. An OR would be
		# a single combined condition returning true on any match.
		self.assertIn("if (this.shiftStartFilter && c.shift_start !== this.shiftStartFilter) return false;",
					  self.body)
		self.assertIn("if (this.shiftEndFilter && c.shift_end !== this.shiftEndFilter) return false;",
					  self.body)
		self.assertIn("if (emp && !(c.employees || []).some(e =>", self.body)

	def test_the_counter_says_how_many_of_how_many(self):
		self.assertIn("Showing {{ filteredPoolCards.length }} of {{ unassignedPoolCards.length }} cards",
					  self.canvas)

	def test_the_counter_stays_plain_when_nothing_is_filtered(self):
		# "Showing 551 of 551" is noise on an untouched board.
		self.assertIn('v-if="anyPoolFilterActive"', self.canvas)
		self.assertIn("anyPoolFilterActive() {", self.canvas)

	def test_progress_counters_are_not_affected_by_the_filters(self):
		# Cards Planned / Remaining are scheduling progress; they must not move because
		# somebody typed in a filter box (WI-002309).
		planned = self.canvas.split("totalCardsRemaining() {", 1)[1].split("\n            },", 1)[0]
		self.assertNotIn("filteredPoolCards", planned)


class TestTheOptionListsStaySteady(FrappeTestCase):
	"""AC2/AC4: built from every unassigned card, never from the filtered view."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_there_is_one_definition_of_the_unfiltered_pool(self):
		self.assertIn("unassignedPoolCards() {", self.canvas)
		self.assertIn("return this.planData.shipment_cards.filter(c => !this.assignedCards.has(c.id));",
					  self.canvas)

	def test_all_three_option_lists_read_it(self):
		for builder in ("poolShiftOptions() {", "poolShiftEndOptions() {",
						"poolShiftStartOptions() {"):
			after = self.canvas.split(builder, 1)[1].split("\n            },", 1)[0]
			self.assertIn("unassignedPoolCards", after,
						  f"{builder} must not build its options from the filtered set")

	def test_the_shift_list_is_deduplicated_and_ordered(self):
		self.assertIn("return [...new Set(", self.canvas)
		self.assertIn(".filter(Boolean)\n                )].sort();", self.canvas)

	def test_the_shift_end_list_is_ordered_by_time_not_by_label(self):
		# Sorting the printed labels puts "00:00" before "23:00" of the previous day.
		ends = self.canvas.split("poolShiftEndOptions() {", 1)[1].split("\n            },", 1)[0]
		self.assertIn(".sort((a, b) => new Date(a[0]) - new Date(b[0]))", ends)


class TestTypingAndClearing(FrappeTestCase):
	"""AC2 type-ahead, AC3 partial match, AC6 one-click clear."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_shift_filter_uses_the_browsers_own_type_ahead(self):
		# A datalist narrows as you type with no extra dropdown widget to maintain.
		self.assertIn('list="rp-shift-options"', self.canvas)
		self.assertIn('<datalist id="rp-shift-options">', self.canvas)

	def test_a_picked_shift_matches_exactly_and_a_typed_one_narrows(self):
		# Exact once it names a real shift (AC2); until then the half-typed text would
		# match nothing at all, which reads as a broken filter.
		self.assertIn("const shiftIsExact = shift && this.poolShiftOptions.includes(shift);",
					  self.canvas)
		self.assertIn("shiftIsExact ? name !== shift", self.canvas)

	def test_the_employee_match_is_partial_and_case_insensitive(self):
		self.assertIn("const emp = this.employeeQuery.toLowerCase().trim();", self.canvas)
		self.assertIn(".toLowerCase().includes(emp)", self.canvas)

	def test_a_card_with_no_riders_does_not_break_the_match(self):
		self.assertIn("(c.employees || []).some(e =>", self.canvas)
		self.assertIn("String((e && e.name) || '')", self.canvas)

	def test_the_three_text_filters_each_have_a_clear_button(self):
		self.assertEqual(self.canvas.count('class="rp-filter-clear"'), 3)
		for target in ("@click=\"searchQuery = ''\"", "@click=\"employeeQuery = ''\"",
					   "@click=\"shiftFilter = ''\""):
			self.assertIn(target, self.canvas)

	def test_the_clear_button_only_shows_when_there_is_something_to_clear(self):
		for guard in ('v-if="searchQuery"', 'v-if="employeeQuery"', 'v-if="shiftFilter"'):
			self.assertIn(guard, self.canvas)

	def test_typed_text_does_not_run_under_the_clear_button(self):
		self.assertIn("padding-right: 28px;", self.canvas)
