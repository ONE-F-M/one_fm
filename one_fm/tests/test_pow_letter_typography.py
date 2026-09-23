# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002723: the faces the Proof of Work letter is typeset in, and how they reach the PDF."""

import json
import os
import struct

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.jinja.print_format.methods import POW_FONT_FILES, pow_font_faces

LETTER = frappe.get_app_path(
	"one_fm", "one_fm", "print_format", "proof_of_work_letter", "proof_of_work_letter.json"
)
FONT_FOLDER = os.path.join(frappe.get_app_path("one_fm"), "public", "fonts", "pow")

ARABIC_ALEF = 0x0627


def _letter():
	return json.loads(frappe.read_file(LETTER))


def _covers(path, codepoint):
	"""Does this TTF's cmap carry the codepoint?

	Read here rather than trusted, because Google Fonts serves a Latin-only subset by
	default and a Latin-only Arabic font draws every word on this letter as an empty box.
	"""
	data = open(path, "rb").read()
	for index in range(struct.unpack(">H", data[4:6])[0]):
		offset = 12 + index * 16
		if data[offset : offset + 4] != b"cmap":
			continue
		cmap = struct.unpack(">I", data[offset + 8 : offset + 12])[0]
		for table in range(struct.unpack(">H", data[cmap + 2 : cmap + 4])[0]):
			record = cmap + 4 + table * 8
			sub = cmap + struct.unpack(">I", data[record + 4 : record + 8])[0]
			if struct.unpack(">H", data[sub : sub + 2])[0] != 4:
				continue
			seg_x2 = struct.unpack(">H", data[sub + 6 : sub + 8])[0]
			ends = [
				struct.unpack(">H", data[sub + 14 + i * 2 : sub + 16 + i * 2])[0]
				for i in range(seg_x2 // 2)
			]
			starts_at = sub + 16 + seg_x2
			starts = [
				struct.unpack(">H", data[starts_at + i * 2 : starts_at + 2 + i * 2])[0]
				for i in range(seg_x2 // 2)
			]
			if any(start <= codepoint <= end for start, end in zip(starts, ends)):
				return True
	return False


class TestTheFontsAreShipped(FrappeTestCase):
	def test_every_declared_file_exists(self):
		for _family, _weight, filename in POW_FONT_FILES:
			self.assertTrue(os.path.exists(os.path.join(FONT_FOLDER, filename)), filename)

	def test_every_file_can_draw_arabic(self):
		"""Google Fonts serves a Latin-only subset by default; a Latin-only Arabic font
		renders every word on this letter as an empty box."""
		for _family, _weight, filename in POW_FONT_FILES:
			self.assertTrue(
				_covers(os.path.join(FONT_FOLDER, filename), ARABIC_ALEF), filename
			)

	def test_the_licence_travels_with_them(self):
		self.assertTrue(os.path.exists(os.path.join(FONT_FOLDER, "OFL.txt")))

	def test_the_two_families_the_spec_names_are_both_here(self):
		self.assertEqual({family for family, _w, _f in POW_FONT_FILES}, {"Cairo", "Readex Pro"})

	def test_readex_pro_ships_the_three_weights_the_spec_uses(self):
		weights = {weight for family, weight, _f in POW_FONT_FILES if family == "Readex Pro"}
		# Bold for headings, Regular for body, Light for the English framework's body.
		self.assertEqual(weights, {300, 400, 700})


class TestTheFacesReachThePdf(FrappeTestCase):
	def setUp(self):
		self.css = pow_font_faces()

	def test_one_rule_per_file(self):
		self.assertEqual(self.css.count("@font-face"), len(POW_FONT_FILES))

	def test_the_files_are_inlined_not_fetched(self):
		"""wkhtmltopdf would fetch a URL over HTTP from get_url(), which fails outright in
		the background job the PDFs are built in - what pow_logo_src() exists to avoid."""
		self.assertIn("data:font/truetype", self.css)
		self.assertNotIn("http://", self.css)
		self.assertNotIn("https://", self.css)

	def test_every_declared_weight_is_in_the_rules(self):
		for family, weight, _filename in POW_FONT_FILES:
			self.assertIn(f"font-family: '{family}'; font-style: normal; font-weight: {weight};", self.css)

	def test_the_template_emits_them(self):
		self.assertIn("pow_font_faces()", _letter()["html"])

	def test_a_missing_file_does_not_stop_the_letter_printing(self):
		"""A letter in the wrong font beats a letter that does not print."""
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "jinja", "print_format", "methods.py")
		)
		body = source.split("def pow_font_faces", 1)[1].split("\ndef ", 1)[0]
		self.assertIn("except OSError:", body)
		self.assertIn("continue", body)


class TestTheTypography(FrappeTestCase):
	def setUp(self):
		self.css = _letter()["css"]

	def test_the_title_is_cairo_bold_italic_at_36pt_in_black(self):
		rule = self.css.split(".pow-letter .pow-hd-title {", 1)[1].split("}", 1)[0]
		self.assertIn("'Cairo'", rule)
		self.assertIn("font-size: 36pt", rule)
		self.assertIn("font-weight: 700", rule)
		self.assertIn("font-style: italic", rule)
		self.assertIn("color: #000", rule)

	def test_the_title_rule_outweighs_the_reset(self):
		"""`.pow-letter *` is more specific than a bare `.pow-hd-title`, so on its own the
		title would silently keep the body face."""
		self.assertIn(".pow-letter .pow-hd-title {", self.css)
		self.assertNotIn("\n.pow-hd-title {", self.css)

	def test_the_body_is_readex_pro_regular_at_10pt_in_black(self):
		reset = self.css.split(".pow-letter, .pow-letter * {", 1)[1].split("}", 1)[0]
		self.assertIn("'Readex Pro'", reset)
		self.assertIn("font-weight: 400", reset)

		body = self.css.split(".pow-letter { direction: rtl;", 1)[1].split("}", 1)[0]
		self.assertIn("font-size: 10pt", body)
		self.assertIn("color: #000", body)

	def test_headings_and_table_headers_are_bold(self):
		rule = self.css.split(".pow-letter .sched-title, .pow-letter .nm-title, .pow-letter .pow-tbl th {", 1)[1].split("}", 1)[0]
		self.assertIn("font-weight: 700", rule)

	def test_the_english_framework_uses_the_light_weight(self):
		"""Scenario 1.2, scoped to this document: the only Latin run it can carry is a
		client whose Full Name in Arabic has not been filled in yet."""
		rule = self.css.split(".pow-letter .en {", 1)[1].split("}", 1)[0]
		self.assertIn("font-weight: 300", rule)

	def test_arial_is_gone(self):
		"""There is no Arial on the print server; fontconfig answered it with a face that
		carries no Arabic glyphs at all."""
		self.assertNotIn("Arial", self.css)

	def test_an_arabic_capable_fallback_is_still_listed(self):
		"""If a font file goes missing the rules are skipped, and an unknown family
		resolves to Liberation Sans, which draws no Arabic."""
		reset = self.css.split(".pow-letter, .pow-letter * {", 1)[1].split("}", 1)[0]
		self.assertIn("Noto Sans Arabic", reset)

	def test_the_modified_stamp_moved(self):
		"""A standard fixture whose `modified` does not move is skipped by migrate."""
		self.assertGreater(_letter()["modified"], "2026-09-23 12:00:00.000000")
