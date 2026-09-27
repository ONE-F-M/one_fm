# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002768: how many people a PAM licence carries."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details import pam_license_details as module
from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	WATCHED_EMPLOYEE_FIELDS,
	count_license_employees,
	recount_license_total,
)

FIELDNAME = "total_number_of_employees"


class _Counter:
	def __init__(self, count=0, licenses=()):
		self.count = count
		self.licenses = list(licenses)
		self.counted = []
		self.written = []

	def db_count(self, doctype, filters=None):
		self.counted.append((doctype, filters))
		return self.count

	def exists(self, doctype, name):
		return name in self.licenses

	def set_value(self, doctype, name, fieldname, value, update_modified=None):
		self.written.append((doctype, name, fieldname, value, update_modified))


class TestWhoIsCounted(FrappeTestCase):
	def _count(self, license_name, rows=7):
		counter = _Counter(count=rows)
		original = module.frappe.db.count
		module.frappe.db.count = counter.db_count
		try:
			return count_license_employees(license_name), counter
		finally:
			module.frappe.db.count = original

	def test_it_counts_the_employees_on_the_licence(self):
		total, counter = self._count("ONE FM Private")
		self.assertEqual(total, 7)
		self.assertEqual(counter.counted[0][0], "Employee")

	def test_it_counts_only_those_under_the_company_residency(self):
		"""That is what the licence IS: somebody off it is not on the licence, whatever
		their employment status says."""
		_total, counter = self._count("ONE FM Private")
		self.assertEqual(
			counter.counted[0][1],
			{"pam_file": "ONE FM Private", "under_company_residency": 1},
		)

	def test_it_counts_off_the_link_and_not_the_copied_number(self):
		"""pam_file_number is read-only and fetched from pam_file, and a fetch only runs
		when the employee is saved. Move somebody to another licence without saving them
		again, or edit a licence's civil ID, and the copy still names the old one - counted
		by the number, that employee lands on no licence at all. It is also the field the
		Employee list filters on, so the figure and the list answer the same question."""
		_total, counter = self._count("ONE FM Private")
		self.assertIn("pam_file", counter.counted[0][1])
		self.assertNotIn("pam_file_number", counter.counted[0][1])

	def test_it_does_not_ask_for_a_pam_designation(self):
		"""The sector counts join the designation to know which row somebody belongs to.
		This is every employee on the licence, including the ones whose designation has
		not been set - leaving those out would make the total smaller than PAM's own."""
		_total, counter = self._count("ONE FM Private")
		self.assertNotIn("one_fm_pam_designation", counter.counted[0][1])

	def test_a_licence_with_no_name_carries_nobody(self):
		"""Not "everybody": an unconfigured licence must not read as the whole company."""
		counter = _Counter(count=999)
		original = module.frappe.db.count
		module.frappe.db.count = counter.db_count
		try:
			self.assertEqual(count_license_employees(None), 0)
			self.assertEqual(count_license_employees(""), 0)
		finally:
			module.frappe.db.count = original
		self.assertEqual(counter.counted, [])


class TestHowItIsWritten(FrappeTestCase):
	def _recount(self, licenses, count=12, name="ONE FM Private"):
		counter = _Counter(count=count, licenses=licenses)
		originals = (module.frappe.db.count, module.frappe.db.exists, module.frappe.db.set_value)
		module.frappe.db.count = counter.db_count
		module.frappe.db.exists = counter.exists
		module.frappe.db.set_value = counter.set_value
		try:
			recount_license_total(name)
		finally:
			module.frappe.db.count, module.frappe.db.exists, module.frappe.db.set_value = originals
		return counter

	def test_it_writes_the_figure_onto_the_licence(self):
		counter = self._recount(["ONE FM Private"])
		self.assertEqual(
			counter.written, [("PAM License Details", "ONE FM Private", FIELDNAME, "12", False)]
		)

	def test_it_writes_a_whole_number_as_text(self):
		"""The field is Data; "12.0" beside the sector figures would read as a different
		kind of number."""
		self.assertEqual(self._recount(["ONE FM Private"]).written[0][3], "12")

	def test_it_writes_to_the_one_licence_the_employees_name(self):
		"""Not every licence sharing a civil ID: the employees are counted by the link, so
		the figure belongs to the record they point at."""
		counter = self._recount(["ONE FM Private", "T4"])
		self.assertEqual([row[1] for row in counter.written], ["ONE FM Private"])

	def test_it_does_not_bump_modified(self):
		"""Nobody edited the licence; somebody was transferred."""
		self.assertIs(self._recount(["ONE FM Private"]).written[0][4], False)

	def test_a_licence_that_is_not_there_writes_nothing(self):
		self.assertEqual(self._recount([]).written, [])


class TestWhenItIsRecounted(FrappeTestCase):
	def setUp(self):
		self.source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "grd", "doctype", "pam_license_details", "pam_license_details.py"
			)
		)

	def test_a_transfer_moves_the_total_as_well_as_the_sector(self):
		self.assertIn("recount_license_total(license_name)", self.source)

	def test_the_total_is_recounted_from_the_licence_the_employee_names(self):
		"""_license_and_sector gives up on an employee with no PAM designation. The sector
		figures can afford that; the licence total cannot."""
		block = self.source.split("def update_counts_from_employee", 1)[1]
		self.assertIn('doc.get("pam_file")', block)

	def test_the_fields_that_trigger_a_recount_are_the_ones_counted_on(self):
		"""pam_file_number is not among them: nothing counts off it any more, and a fetch
		refreshing the copy has moved nobody."""
		self.assertIn("pam_file", WATCHED_EMPLOYEE_FIELDS)
		self.assertIn("under_company_residency", WATCHED_EMPLOYEE_FIELDS)
		self.assertNotIn("pam_file_number", WATCHED_EMPLOYEE_FIELDS)

	def test_saving_a_licence_derives_it_too(self):
		"""So a licence opened and saved shows the figure without waiting for a transfer."""
		self.assertIn("self.set_total_number_of_employees()", self.source)


class TestTheFieldIsDerived(FrappeTestCase):
	def test_it_is_left_writable_as_the_ba_site_has_it(self):
		"""The figure is derived on every save, so a typed value does not survive - but the
		field is not marked read-only. It is not read-only on the BA site this was migrated
		from, and a migration copies the configuration it is given."""
		definition = json.loads(
			frappe.read_file(
				frappe.get_app_path(
					"one_fm",
					"grd",
					"doctype",
					"pam_license_details",
					"pam_license_details.json",
				)
			)
		)
		field = next(f for f in definition["fields"] if f["fieldname"] == FIELDNAME)
		self.assertNotIn("read_only", field)


class TestTheFiguresAreRestated(FrappeTestCase):
	"""The figure was counted off pam_file_number and is counted off pam_file now, so every
	figure already stored was worked out the old way."""

	def test_the_patch_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.recount_pam_licences_by_file_link", patches)

	def test_it_restates_every_licence(self):
		"""Not only the ones an employee has moved on or off since: every stored figure was
		counted the old way. Both sets of them - the total and the sector rows read the
		same employees and moved to the link together."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "recount_pam_licences_by_file_link.py"
			)
		)
		self.assertIn('frappe.get_all("PAM License Details", pluck="name")', source)
		self.assertIn("recount_license_total(license_name)", source)
		self.assertIn("recount_license(license_name)", source)

	def test_every_stored_figure_matches_the_employees_on_the_licence(self):
		"""The restatement itself, asserted against the live site once it has run."""
		wrong = []
		for licence in frappe.get_all("PAM License Details", fields=["name", FIELDNAME]):
			counted = frappe.db.count(
				"Employee", {"pam_file": licence.name, "under_company_residency": 1}
			)
			if str(licence.get(FIELDNAME) or "") != str(counted):
				wrong.append((licence.name, licence.get(FIELDNAME), counted))
		self.assertEqual(wrong, [], f"{len(wrong)} licences carry a stale headcount")
