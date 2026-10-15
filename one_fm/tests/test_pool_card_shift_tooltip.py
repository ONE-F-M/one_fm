# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-003503: the full shift name shows on hover of an unassigned pool card.

The shift name on a pool card is cut with an ellipsis so long names do not widen the
sidebar. The element had no title, so nothing revealed the rest. These tests pin:

* **A Vue binding, not a template string.** The template lives inside a JS template
  literal, so ``title="${...}"`` would be interpolated by JS, unescaped; ``:title`` is
  escaped by Vue.
* **The ellipsis CSS stays.** Dropping overflow or text-overflow lets long names widen
  the sidebar cards.
"""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

CANVAS = pathlib.Path(frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_schedule", "transportation_schedule.js"
))


class TestPoolCardShiftTooltip(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.canvas = CANVAS.read_text()

	def test_the_shift_name_has_a_bound_title(self):
		self.assertIn(
			'class="rp-card-shift" :title="card.shift_name">{{ card.shift_name }}</div>',
			self.canvas,
		)

	def test_the_title_is_not_a_template_string(self):
		self.assertNotIn('class="rp-card-shift" title=', self.canvas)

	def test_the_ellipsis_css_is_kept(self):
		rule = self.canvas.split(".rp-card-shift {", 1)[1].split("}", 1)[0]
		for declaration in ("white-space: nowrap;", "overflow: hidden;",
							"text-overflow: ellipsis;"):
			self.assertIn(declaration, rule)
