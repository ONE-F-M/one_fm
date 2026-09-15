# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Every field roster.js asks the server for has to exist on the doctype.

The OT modal asked Operations Shift for double_shift_ot_allowed. WI-001425 added that
field; the revert of #6413 removed it three days before this code was written, and only
the table column survived. Server-side lookups still worked - the column is there - but
the browser goes through reportview, which checks the doctype's fields and refuses the
whole query with "Field not permitted in query". So Site and Project were never filled
in either, and the warning the field guarded was never once shown.

Nothing else would notice: the page has no tests, the JS throws inside a promise, and
the only visible sign is a dialog that flashes and goes.
"""

import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

ROSTER_JS = os.path.join(os.path.dirname(__file__), "roster.js")

# frappe.db.get_value("DocType", <anything>, ["a", "b"]) - literal doctype, literal fields.
GET_VALUE = re.compile(
	r"""frappe\.db\.get_value\(\s*["']([^"']+)["']\s*,[^,\[]*,\s*\[([^\]]*)\]""",
	re.VERBOSE,
)


class TestRosterClientQueries(FrappeTestCase):
	def test_every_field_it_asks_for_exists(self):
		with open(ROSTER_JS) as handle:
			source = handle.read()

		calls = GET_VALUE.findall(source)
		self.assertTrue(calls, "no frappe.db.get_value calls found - has the pattern changed?")

		for doctype, raw_fields in calls:
			if not frappe.db.exists("DocType", doctype):
				continue  # a doctype from another app, or built at runtime
			meta = frappe.get_meta(doctype)
			for field in re.findall(r"""["']([A-Za-z_][A-Za-z0-9_]*)["']""", raw_fields):
				with self.subTest(doctype=doctype, field=field):
					self.assertTrue(
						meta.get_field(field) or field in frappe.model.default_fields,
						f"roster.js asks {doctype} for {field!r}, which the doctype does not "
						"have - reportview refuses the whole query, so the other fields in it "
						"come back empty too",
					)
