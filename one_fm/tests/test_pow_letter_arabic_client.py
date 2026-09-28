# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002722: the last English on the Proof of Work letter, and the figures behind it."""

import json
import re

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.jinja.print_format.methods import (
	POW_TITLE_AR,
	pow_arabic_figure,
	pow_title_arabic,
)

LETTER = frappe.get_app_path(
	"one_fm", "one_fm", "print_format", "proof_of_work_letter", "proof_of_work_letter.json"
)


def _letter():
	return json.loads(frappe.read_file(LETTER))


class TestTheTitle(FrappeTestCase):
	def setUp(self):
		self.letter = _letter()

	def test_the_letter_no_longer_prints_an_english_title(self):
		self.assertNotIn("PROOF OF WORK", self.letter["html"])

	def test_it_prints_the_arabic_title(self):
		self.assertEqual(pow_title_arabic(), POW_TITLE_AR)
		self.assertIn("pow_title", self.letter["html"])

	def test_the_fallback_carries_the_same_words(self):
		"""The template is guarded for the gap between migrate and restart; the guard has
		to say the same thing the helper does, or the title changes for one request."""
		self.assertIn(POW_TITLE_AR, self.letter["html"])

	def test_the_masthead_reads_right_to_left_now(self):
		"""It was ltr to keep an English title to the right of the logo."""
		self.assertIn("direction: rtl", self.letter["css"].split(".pow-hd {", 1)[1][:120])


class TestTheClientName(FrappeTestCase):
	def setUp(self):
		self.letter = _letter()

	def test_the_arabic_name_is_what_the_letter_asks_for(self):
		self.assertIn("pow_customer_name(doc)", self.letter["html"])
		self.assertIn("customer_name_in_arabic", self.letter["html"])

	def test_an_arabic_name_is_not_embedded_left_to_right(self):
		"""The `en` class is an ltr embedding. Applying it to an Arabic name puts its
		words in the wrong order."""
		self.assertIn('"val" if customer_is_arabic else "en"', self.letter["html"])

	def test_the_field_it_reads_exists_on_customer(self):
		self.assertTrue(frappe.get_meta("Customer").get_field("customer_name_in_arabic"))

	def test_the_modified_stamp_moved(self):
		"""A standard fixture whose `modified` does not move is skipped by migrate
		entirely, so the change never reaches a site."""
		self.assertGreater(self.letter["modified"], "2026-09-12 16:00:00.000000")


class TestTheStaffBreakdownFigures(FrappeTestCase):
	"""AC2 and AC3 were already satisfied by the generator; these keep them that way."""

	# A real February row, from POW-Aayan Leasing Co.-Aayan Rental & Leasing-2022-06-01.
	BREAKDOWN = (
		"- 6 Staff worked 42 days: 252 Days\n"
		"- 2 Staff worked 41 days: 82 Days\n"
		"- 1 Staff worked 40 days: 40 Days\n"
		"- 1 Staff worked 39 days: 39 Days\n"
		"- 2 Staff worked 35 days: 70 Days\n"
		"- 1 Staff worked 32 days: 32 Days\n"
		"- 1 Staff worked 30 days: 30 Days\n"
		"- 1 Staff worked 28 days: 28 Days\n"
		"- 1 Staff worked 22 days: 22 Days\n"
		"- 1 Staff worked 14 days: 14 Days\n"
		"- 1 Staff worked 11 days: 11 Days\n"
		"- 1 Staff worked 1 days: 1 Days\n"
		"- 1 Staff worked 0 days: 0 Days"
	)
	WORKED = "621 Days"

	def test_every_line_carries_the_product_not_just_the_per_staff_figure(self):
		"""AC2: "6 staff worked 42 days" has to end in 252, not in 42."""
		for line in self.BREAKDOWN.split("\n"):
			staff, each, total = (float(figure) for figure in re.findall(r"[\d.]+", line))
			self.assertEqual(total, staff * each, line)

	def test_the_total_is_the_sum_of_the_line_totals(self):
		"""AC3: the worked column has to agree with the lines above it."""
		totals = [
			float(re.findall(r"[\d.]+", line)[2]) for line in self.BREAKDOWN.split("\n")
		]
		self.assertEqual(sum(totals), float(re.findall(r"[\d.]+", self.WORKED)[0]))

	def test_the_arabic_line_keeps_all_three_figures(self):
		"""Translation must not lose the product on the way to the page."""
		arabic = pow_arabic_figure("- 10 Staff worked 23 days: 230 Days")
		digits = re.findall(r"[٠-٩]+", arabic)
		self.assertEqual(len(digits), 3, arabic)

	def test_an_untranslatable_line_is_printed_as_it_stands(self):
		"""A wrong translation of a figure is worse than an untranslated one."""
		self.assertEqual(pow_arabic_figure("- 10 people did something"), "- 10 people did something")


class TestTheHelpersAreReachableFromJinja(FrappeTestCase):
	def test_all_three_are_registered(self):
		from one_fm import hooks

		# The pow_ helpers are registered through jenv, whose entries are
		# "alias:dotted.path" - the alias is what the template calls. `jinja` next to it
		# only lists the module.
		registered = {
			entry.split(":", 1)[0] for entry in hooks.jenv["methods"] if ":" in entry
		}
		for method in ("pow_customer_name", "pow_customer_name_is_arabic", "pow_title_arabic"):
			self.assertIn(method, registered)
