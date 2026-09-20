# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002543: the Trip Builder's leg table stops scrolling sideways.

Eleven columns in a dialog capped near 900px meant the right-hand ones - Target Arrival
and On Board, which are what the dispatcher is checking - lived off the edge behind a
horizontal scrollbar.

Three things had to change together, and any one alone would not have worked:

* **The dialog takes 95% of the viewport.** The Trip Builder is a working surface, not a
  message box.
* **The table is ``table-layout: fixed``.** Without it the browser sizes columns from
  their CONTENT, so one long location name widens the whole table however much room the
  dialog has - the widths below would be suggestions.
* **``table-responsive`` is gone.** Its ``overflow-x: auto`` IS the sideways scrollbar
  AC1 asks to eliminate; a wider dialog with it still present just moves the problem.

Measured on the live board at four widths, with the whole run's legs rendered:

    viewport   dialog   frame scrolls x   last column   Accommodation col
    1854px     95%      no                flush          377px
    1280px     95%      no                flush          195px
    1024px     95%      no                flush          114px
     900px     95%      no                flush           75px

The location columns absorb the squeeze, which is AC3's "allocate remaining space
proportionally to text columns", and the "+N more" badges keep the multi-shift cells to
one line with the full list on the tooltip (AC2).
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))

# Every column given a fixed width is numeric or a clock; the rest is shared between the
# three location columns. Kept here so a future column cannot quietly claim fixed space.
FIXED_WIDTH_COLUMNS = {
	".rp-leg-num-col": 44,    # Stop
	".rp-leg-act-col": 92,    # Action
	".rp-leg-time-col": 76,   # QOA / Departure / Target Arrival / On Board
	".rp-leg-mins-col": 74,   # Buffer / Transit
}


class TestTheTableCannotScrollSideways(FrappeTestCase):
	"""AC1 + AC4."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_frame_scrolls_down_only(self):
		self.assertIn("max-height: 46vh; overflow-y: auto; overflow-x: hidden;", self.canvas)

	def test_the_responsive_wrapper_is_gone_from_the_leg_table(self):
		# Bootstrap's .table-responsive is overflow-x:auto - the scrollbar itself.
		self.assertIn('<div class="rp-leg-table-frame">', self.canvas)
		builder = self.canvas.split("_mergeModalHtml(p, vehicle) {", 1)[1].split("\n            },", 1)[0]
		self.assertNotIn('<div class="table-responsive">', builder)

	def test_the_dialog_takes_most_of_the_viewport(self):
		self.assertIn(".rp-trip-builder-dialog { max-width: 95vw !important; width: 95vw !important; }",
					  self.canvas)

	def test_the_dialog_class_is_actually_applied(self):
		# A style rule nothing wears is dead CSS.
		self.assertIn(".modal-dialog').addClass('rp-trip-builder-dialog')", self.canvas)

	def test_the_header_stays_put_while_the_legs_scroll(self):
		self.assertIn("position: sticky; top: 0; z-index: 2;", self.canvas)

	def test_the_sticky_header_is_opaque(self):
		# A transparent sticky header shows the rows sliding under it.
		head = self.canvas.split(".rp-leg-table thead th {", 1)[1].split("}", 1)[0]
		self.assertIn("background:", head)


class TestTheColumnWidthsAreBinding(FrappeTestCase):
	"""AC3: tight for numbers and clocks, the rest to the text columns."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_layout_is_fixed(self):
		# With auto layout the widths below are suggestions the content can overrule.
		self.assertIn(".rp-leg-table { table-layout: fixed; width: 100%; margin-bottom: 0; }",
					  self.canvas)

	def test_every_numeric_column_has_a_tight_width(self):
		for selector, width in FIXED_WIDTH_COLUMNS.items():
			self.assertIn(f"{selector} ", self.canvas)
			self.assertIn(f"width: {width}px", self.canvas,
						  f"{selector} should be pinned at {width}px")

	def test_the_numeric_headers_carry_their_classes(self):
		# The width lives on the column, so the header cell needs it too or the first
		# row decides the width instead. Read off the header list the row is built from.
		for label, cls in (("Stop", "rp-leg-num-col"),
						   ("Action", "rp-leg-act-col"),
						   ("QOA", "rp-leg-time-col"),
						   ("Target Arrival", "rp-leg-time-col"),
						   ("On Board", "rp-leg-time-col")):
			self.assertIn(f"['{label}', '{cls}']", self.canvas)

	def test_the_minute_input_fills_its_cell_instead_of_forcing_it_wider(self):
		# A 72px input inside a 74px column is what made these two columns immovable.
		self.assertIn(".rp-leg-min      { width: 100%; min-width: 0;", self.canvas)

	def test_cells_ellipsize_rather_than_wrap_or_push(self):
		self.assertIn("overflow: hidden; text-overflow: ellipsis; white-space: nowrap;",
					  self.canvas)

	def test_the_location_columns_can_be_squeezed(self):
		# max-width:0 is the idiom that lets a fixed-layout cell shrink below its
		# content; without it the text column refuses to give ground.
		self.assertIn(".rp-leg-place { max-width: 0; }", self.canvas)


class TestMultiLocationCells(FrappeTestCase):
	"""AC2: one line, a count, and the whole list on hover."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_there_is_one_renderer_for_every_location_column(self):
		self.assertIn("const placeCell = (value) => {", self.canvas)
		# Accommodation / Stop, Shift Location, Next Stop.
		self.assertEqual(self.canvas.count("${placeCell("), 3)

	def test_a_multi_shift_cell_shows_the_first_and_a_count(self):
		self.assertIn("""<span class="rp-leg-more">+${all.length - 1} ${__('more')}</span>""",
					  self.canvas)

	def test_the_full_list_is_on_the_tooltip(self):
		self.assertIn("const full = esc(all.join(', '));", self.canvas)
		self.assertIn('title="${full}"', self.canvas)

	def test_a_single_location_gets_no_badge(self):
		# "+0 more" on every ordinary stop would be noise.
		self.assertIn("if (all.length === 1) {", self.canvas)

	def test_an_empty_cell_stays_a_dash(self):
		self.assertIn("""if (!all.length) return '<td class="small rp-leg-place">—</td>';""",
					  self.canvas)

	def test_the_list_is_split_on_the_separator_the_server_joins_with(self):
		# get_merge_preview builds shift_location as ", ".join(...).
		self.assertIn(".split(',')", self.canvas)
		server = pathlib.Path(frappe.get_app_path(
			"one_fm", "one_fm", "doctype", "transportation_shipment",
			"transportation_shipment.py")).read_text()
		self.assertIn('", ".join(shift_places)', server)


class TestTheHeadersSayWhatTheyAre(FrappeTestCase):
	"""A column that fits by width shows "Target…", and the reader is left guessing.

	The cells in the location columns have carried their full text on a tooltip since
	AC2; the headers never did, so the one place the ellipsis is GUARANTEED to bite -
	a fixed 76px column holding "Target Arrival" - was the one place with nothing behind
	it. Reported in testing.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()
		cls.headers = cls.canvas.split("const headers = [", 1)[1].split("].map(", 1)[0]

	def test_every_column_is_in_the_list(self):
		for label in ("Stop", "Accommodation / Stop", "Action", "QOA", "Departure",
					  "Buffer (min)", "Transit (min)", "Shift Location", "Next Stop",
					  "Target Arrival", "On Board"):
			self.assertIn(f"'{label}'", self.headers, msg=label)

	def test_the_columns_keep_their_order(self):
		positions = [self.headers.index(f"'{label}'") for label in
					 ("Stop", "Accommodation / Stop", "Action", "QOA", "Departure",
					  "Buffer (min)", "Transit (min)", "Shift Location", "Next Stop",
					  "Target Arrival", "On Board")]
		self.assertEqual(positions, sorted(positions))

	def test_the_tooltip_and_the_label_are_the_same_string(self):
		# The whole reason the row is built from a list. Written out by hand, the title
		# and the text drift the first time somebody renames a column - and a tooltip
		# that disagrees with its header is worse than none.
		self.assertIn('title="${text}">${text}</th>', self.canvas)

	def test_the_label_is_escaped_once_and_reused(self):
		self.assertIn("const text = esc(__(label));", self.canvas)

	def test_the_headers_are_still_translated(self):
		self.assertIn("esc(__(label))", self.canvas)

	def test_no_header_is_hand_written_any_more(self):
		# A leftover hand-written cell would have no tooltip and nothing would say so.
		self.assertNotIn("<th class=\"rp-leg-time-col\">${__(", self.canvas)
		self.assertNotIn("<th>${__(", self.canvas)

	def test_the_row_is_rendered_from_the_list(self):
		self.assertIn("<thead><tr>${headers}</tr></thead>", self.canvas)

	def test_the_cells_still_carry_their_own_tooltips(self):
		# AC2, unchanged - this fix is about the header row only.
		self.assertIn('<td class="small rp-leg-place" title="${full}">', self.canvas)
