# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002091: the actual national and expatriate headcounts on a licence's sector rows."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	WATCHED_EMPLOYEE_FIELDS,
	count_workers,
	recount_license,
	recount_sector,
	update_counts_from_employee,
)

LICENSE = "_Test Counted License"
LICENSE_NUMBER = "_TEST-PAM-9001"
SECTOR = "_Test Sector Technicians"
OTHER_SECTOR = "_Test Sector Managers"
# A sector the licence carries no row for - what a new employee lands in when nobody has
# configured that half of the licence yet.
UNCONFIGURED_SECTOR = "_Test Sector Salespeople"


def _a_sector(name):
	if not frappe.db.exists("Occupational Sector", name):
		frappe.get_doc({"doctype": "Occupational Sector", "occupational_sector_type": name}).insert(
			ignore_permissions=True
		)
	return name


def _a_designation(name, sector):
	"""A PAM designation in a sector - what puts an employee in that sector."""
	if frappe.db.exists("PAM Designation List", name):
		frappe.db.set_value("PAM Designation List", name, "occupational_sector", sector)
		return name

	designation = frappe.get_doc({
		"doctype": "PAM Designation List",
		"designation_name_english": name,
		# The record is named after the Arabic name, so it cannot be left out.
		"designation_name_arabic": name,
		"designation_code": name,
		"occupational_sector": sector,
	})
	designation.flags.ignore_permissions = True
	designation.insert()
	return designation.name


class TestPAMLicenseWorkerCounts(FrappeTestCase):
	def setUp(self):
		self.sector = _a_sector(SECTOR)
		self.other_sector = _a_sector(OTHER_SECTOR)
		self.designation = _a_designation("_Test PAM Technician", self.sector)
		self.other_designation = _a_designation("_Test PAM Manager", self.other_sector)
		# What each borrowed employee looked like before the test pointed it at the licence.
		# Restored explicitly in tearDown: one_fm's Employee override commits mid-save, so
		# nothing here can rely on FrappeTestCase's rollback to undo an employee.
		self.borrowed = {}
		self.license = self._a_license()

	def tearDown(self):
		for name, before in self.borrowed.items():
			frappe.db.set_value("Employee", name, before, update_modified=False)
		if frappe.db.exists("PAM License Details", LICENSE):
			frappe.delete_doc("PAM License Details", LICENSE, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _a_license(self):
		"""Rebuilt each run rather than reused: one_fm's Employee override commits, so a
		test that touches an employee cannot rely on the rollback to clear this away."""
		if frappe.db.exists("PAM License Details", LICENSE):
			frappe.delete_doc("PAM License Details", LICENSE, force=True, ignore_permissions=True)

		license = frappe.get_doc({
			"doctype": "PAM License Details",
			"label_name": LICENSE,
			"civil_id_number_for_licensing": LICENSE_NUMBER,
			"license_name": LICENSE,
			"classification": "Commercial",
			"status": "Not suspended",
			"pam_license_stats": [
				{"occupational_sector": self.sector},
				{"occupational_sector": self.other_sector},
			],
		})
		license.flags.ignore_permissions = True
		license.insert()
		return license

	def _an_employee(self, nationality, designation=None, status="Active"):
		"""An employee on the test licence.

		Re-pointed rather than created: Employee sits at MariaDB's row-size limit here and a
		fixture would need a Company, a Fiscal Year and a Designation before it inserted.
		Written with db.set_value, which the rollback does undo.
		"""
		name = frappe.db.get_value(
			"Employee",
			{
				"pam_file_number": ["!=", LICENSE_NUMBER],
				"name": ["not in", list(self.borrowed) or ["__none__"]],
			},
			"name",
			order_by="creation asc",
		)
		if not name:
			self.skipTest("No spare Employee on this site to point at the test licence")

		self.borrowed[name] = frappe.db.get_value(
			"Employee",
			name,
			["pam_file_number", "one_fm_pam_designation", "one_fm_nationality", "status", "employee_name"],
			as_dict=True,
		)
		frappe.db.set_value("Employee", name, {
			"pam_file_number": LICENSE_NUMBER,
			"one_fm_pam_designation": designation or self.designation,
			"one_fm_nationality": nationality,
			"status": status,
		}, update_modified=False)
		return name

	def _row(self, sector):
		license = frappe.get_doc("PAM License Details", self.license.name)
		return next(row for row in license.pam_license_stats if row.occupational_sector == sector)

	# ── counting ──────────────────────────────────────────────────────────────────

	def test_an_empty_sector_counts_nobody(self):
		self.assertEqual(count_workers(LICENSE_NUMBER, self.sector), (0, 0))

	def test_kuwaitis_count_as_nationals_and_everyone_else_as_expatriates(self):
		self._an_employee("Kuwaiti")
		self._an_employee("Indian")
		self._an_employee("Nepali")

		self.assertEqual(count_workers(LICENSE_NUMBER, self.sector), (1, 2))

	def test_someone_who_has_left_is_not_on_the_licence(self):
		self._an_employee("Kuwaiti")
		self._an_employee("Kuwaiti", status="Left")

		self.assertEqual(count_workers(LICENSE_NUMBER, self.sector), (1, 0))

	def test_a_sector_counts_only_its_own_designations(self):
		self._an_employee("Kuwaiti")
		self._an_employee("Indian", designation=self.other_designation)

		self.assertEqual(count_workers(LICENSE_NUMBER, self.sector), (1, 0))
		self.assertEqual(count_workers(LICENSE_NUMBER, self.other_sector), (0, 1))

	def test_another_licence_is_counted_separately(self):
		self._an_employee("Kuwaiti")

		self.assertEqual(count_workers("_TEST-PAM-NOBODY", self.sector), (0, 0))

	# ── writing the counts onto the row ───────────────────────────────────────────

	def test_recounting_writes_both_figures(self):
		self._an_employee("Kuwaiti")
		self._an_employee("Indian")

		recount_sector(LICENSE_NUMBER, self.sector)

		row = self._row(self.sector)
		self.assertEqual(row.national_number_of_workers, "1")
		self.assertEqual(row.expatriate_number_of_workers, "1")

	def test_recounting_a_licence_covers_every_sector(self):
		self._an_employee("Kuwaiti")
		self._an_employee("Indian", designation=self.other_designation)

		recount_license(self.license.name)

		self.assertEqual(self._row(self.sector).national_number_of_workers, "1")
		self.assertEqual(self._row(self.other_sector).expatriate_number_of_workers, "1")

	def test_a_licence_number_nobody_holds_leaves_the_row_alone(self):
		recount_sector("_TEST-PAM-NOBODY", self.sector)

		self.assertFalse(self._row(self.sector).national_number_of_workers)

	# ── the hook ──────────────────────────────────────────────────────────────────
	#
	# Driven directly rather than through Employee.save(): one_fm's Employee override
	# commits mid-save, which would take the fixtures out of the rollback's reach.

	def _edit(self, name, **changed):
		"""Apply an edit to an employee and hand the handler the document as a save would.

		The before-state is captured before the write and the after-state read back after
		it, which is the order that makes has_value_changed answer honestly.
		"""
		before = frappe.get_doc("Employee", name)
		frappe.db.set_value("Employee", name, changed, update_modified=False)

		doc = frappe.get_doc("Employee", name)
		doc._doc_before_save = before
		update_counts_from_employee(doc)

	def test_a_changed_nationality_moves_the_employee_between_the_two_counts(self):
		employee = self._an_employee("Kuwaiti")
		recount_license(self.license.name)
		self.assertEqual(self._row(self.sector).national_number_of_workers, "1")

		self._edit(employee, one_fm_nationality="Indian")

		row = self._row(self.sector)
		self.assertEqual(row.national_number_of_workers, "0")
		self.assertEqual(row.expatriate_number_of_workers, "1")

	def test_moving_sector_empties_the_row_left_behind(self):
		"""Recounting only where they landed would leave the old row carrying them for good."""
		employee = self._an_employee("Indian")
		recount_license(self.license.name)
		self.assertEqual(self._row(self.sector).expatriate_number_of_workers, "1")

		self._edit(employee, one_fm_pam_designation=self.other_designation)

		self.assertEqual(self._row(self.sector).expatriate_number_of_workers, "0")
		self.assertEqual(self._row(self.other_sector).expatriate_number_of_workers, "1")

	def _insert(self, name):
		"""Hand the handler an employee shaped the way an insert leaves it.

		Not a document with no before-state, which is what an insert looks like in stock
		Frappe: one_fm's after_insert reloads the employee, and after_insert runs before
		on_update, so the before-state the handler is given is the row that was just written.
		"""
		doc = frappe.get_doc("Employee", name)
		doc._doc_before_save = frappe.get_doc("Employee", name)
		doc.flags.in_insert = True
		update_counts_from_employee(doc)

	def test_a_new_employee_is_counted_though_nothing_reads_as_changed(self):
		"""Why no new employee was ever counted: every watched field equals itself on an
		insert, so the has_value_changed guard skipped the recount every time."""
		employee = self._an_employee("Indian")
		recount_license(self.license.name)
		# Stale on purpose - only a recount that actually runs will correct it.
		frappe.db.set_value(
			"PAM License Stats", self._row(self.sector).name, "expatriate_number_of_workers", "0",
			update_modified=False,
		)

		doc = frappe.get_doc("Employee", employee)
		doc._doc_before_save = frappe.get_doc("Employee", employee)
		self.assertFalse(any(doc.has_value_changed(f) for f in WATCHED_EMPLOYEE_FIELDS))

		doc.flags.in_insert = True
		update_counts_from_employee(doc)

		self.assertEqual(self._row(self.sector).expatriate_number_of_workers, "1")

	def test_a_save_that_touches_nothing_relevant_is_skipped(self):
		"""Employee is saved constantly; a recount on every save would be a query per save."""
		employee = self._an_employee("Kuwaiti")
		recount_license(self.license.name)

		# Stale on purpose: if the handler ran it would correct this back to "1".
		frappe.db.set_value(
			"PAM License Stats", self._row(self.sector).name, "national_number_of_workers", "99",
			update_modified=False,
		)

		self._edit(employee, employee_name="Renamed Only")

		self.assertEqual(self._row(self.sector).national_number_of_workers, "99")

	# ── a sector the licence has no row for yet ───────────────────────────────────

	def _in_an_unconfigured_sector(self, nationality):
		sector = _a_sector(UNCONFIGURED_SECTOR)
		designation = _a_designation("_Test PAM Salesperson", sector)
		return sector, self._an_employee(nationality, designation=designation)

	def test_an_employee_in_an_unconfigured_sector_gets_the_licence_a_row(self):
		"""WI-002091's second criterion. The sector an employee belongs to is decided by their
		PAM designation, so a licence that has never carried anybody in it has no row to
		update - and without one the employee is counted against nothing."""
		sector, _employee = self._in_an_unconfigured_sector("Indian")

		recount_sector(LICENSE_NUMBER, sector)

		row = self._row(sector)
		self.assertEqual(row.expatriate_number_of_workers, "1")
		self.assertEqual(row.national_number_of_workers, "0")

	def test_a_sector_nobody_is_in_does_not_grow_the_table(self):
		"""The recount runs for the sector an employee has just left as well, and a row added
		there would grow the table every time anybody changed designation."""
		sector = _a_sector(UNCONFIGURED_SECTOR)

		recount_sector(LICENSE_NUMBER, sector)

		license = frappe.get_doc("PAM License Details", self.license.name)
		self.assertEqual([row.occupational_sector for row in license.pam_license_stats],
			[self.sector, self.other_sector])

	def test_a_new_employee_reaches_the_child_table_through_the_hook(self):
		sector, employee = self._in_an_unconfigured_sector("Kuwaiti")

		self._insert(employee)

		self.assertEqual(self._row(sector).national_number_of_workers, "1")

	def test_the_added_row_sits_after_the_ones_already_there(self):
		sector, _employee = self._in_an_unconfigured_sector("Indian")

		recount_sector(LICENSE_NUMBER, sector)

		license = frappe.get_doc("PAM License Details", self.license.name)
		self.assertEqual(license.pam_license_stats[-1].occupational_sector, sector)

	def test_the_watched_fields_all_exist_on_employee(self):
		"""A typo here would silently stop the recount ever firing."""
		meta = frappe.get_meta("Employee")
		for fieldname in WATCHED_EMPLOYEE_FIELDS:
			with self.subTest(fieldname=fieldname):
				self.assertIsNotNone(meta.get_field(fieldname), fieldname)
