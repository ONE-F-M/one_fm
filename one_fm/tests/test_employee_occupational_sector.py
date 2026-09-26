# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002745: the Employee carries the occupational sector of the PAM designation it holds."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.employee import get_employee_custom_fields

FIELDNAME = "custom_occupational_sector"
SOURCE = "one_fm_pam_designation.occupational_sector"


def _field(fieldname):
	for fields in get_employee_custom_fields().values():
		for field in fields:
			if field["fieldname"] == fieldname:
				return field
	raise AssertionError(f"{fieldname} is not in the Employee custom field set")


class TestTheField(FrappeTestCase):
	def setUp(self):
		self.field = _field(FIELDNAME)

	def test_it_is_fetched_from_the_pam_designation(self):
		"""The sector is not on the employee - it is on the designation they hold - so a
		change of designation has to move it."""
		self.assertEqual(self.field["fetch_from"], SOURCE)

	def test_it_sits_beside_the_designation_it_comes_from(self):
		self.assertEqual(self.field["insert_after"], "one_fm_pam_designation")

	def test_it_points_at_the_sector_record(self):
		"""A Link, not the Data the BA site carries. The sector is a record - the
		designation points at one and the licence figures are grouped by one - so a copy
		held as loose text is the one place on the chain where a sector could read as
		something that is not an Occupational Sector."""
		self.assertEqual(self.field["fieldtype"], "Link")
		self.assertEqual(self.field["options"], "Occupational Sector")

	def test_every_sector_a_designation_can_supply_is_a_real_one(self):
		"""The fetch writes the designation's value straight into a Link, so a designation
		naming a sector that is not a record would leave a broken link on the employee."""
		values = {
			d.occupational_sector
			for d in frappe.get_all(
				"PAM Designation List",
				filters={"occupational_sector": ["is", "set"]},
				fields=["occupational_sector"],
				limit_page_length=0,
			)
		}
		missing = sorted(v for v in values if not frappe.db.exists("Occupational Sector", v))
		self.assertEqual(missing, [])

	def test_it_is_always_visible(self):
		"""The BA site's copy hides it unless Under Company Residency is ticked, which
		WI-002823 removes from every field on this form."""
		self.assertEqual(self.field.get("depends_on", ""), "")

	def test_it_is_labelled_the_way_pam_names_it(self):
		self.assertEqual(self.field["label"], "Occupational Sector")


class TestTheSourceItReads(FrappeTestCase):
	def test_the_designation_carries_an_occupational_sector(self):
		"""A fetch_from naming a field that does not exist copies nothing, silently."""
		field = frappe.get_meta("PAM Designation List").get_field("occupational_sector")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Occupational Sector")

	def test_the_designation_field_it_hangs_off_exists_on_employee(self):
		designation = _field("one_fm_pam_designation")
		self.assertEqual(designation["options"], "PAM Designation List")

	def test_the_two_halves_of_the_fetch_path_agree(self):
		"""`a.b` only works when `a` is the Link on Employee and `b` is a field on what it
		points at."""
		link, target = SOURCE.split(".")
		self.assertEqual(_field(link)["fieldname"], link)
		self.assertTrue(frappe.get_meta("PAM Designation List").get_field(target))


class TestItAgreesWithTheLicenceCounts(FrappeTestCase):
	def test_the_sector_is_still_reached_through_the_designation_for_counting(self):
		"""WI-002091 counts a licence's workers by joining Employee to PAM Designation
		List. This field is a copy for the form to show, not a second source of truth -
		the count must not start reading it, or a stale copy would change a headcount."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "grd", "doctype", "pam_license_details", "pam_license_details.py"
			)
		)
		self.assertIn("Designation.occupational_sector == sector", source)
		self.assertNotIn(FIELDNAME, source)


class TestThePatchIsWiredUp(FrappeTestCase):
	"""The definition in custom_field/employee.py is only applied by after_install, so a
	new entry in it never reaches a site that is already installed. Without the patch the
	field exists in the repository and nowhere on the form."""

	def setUp(self):
		self.source = frappe.read_file(
			frappe.get_app_path("one_fm", "patches", "v15_0", "add_employee_occupational_sector.py")
		)

	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.add_employee_occupational_sector", patches)

	def test_it_applies_the_whole_employee_set(self):
		self.assertIn("create_custom_fields(get_employee_custom_fields(), update=True)", self.source)

	def test_it_syncs_the_table_whatever_create_custom_fields_decided(self):
		"""create_custom_fields only syncs the table when it inserted or changed a Custom
		Field. A row that is already there and already correct leaves the schema alone - so
		if that row's own ALTER failed earlier, and MariaDB's implicit commit on DDL left
		the Custom Field behind without its column, nothing would ever add the column and
		every save of an Employee dies on "Unknown column ... in 'SET'"."""
		self.assertIn('frappe.db.updatedb("Employee")', self.source)

	def test_the_field_has_a_column_behind_it(self):
		"""The failure this patch exists to prevent, asserted against the live site."""
		if frappe.db.exists("Custom Field", "Employee-custom_occupational_sector"):
			self.assertTrue(frappe.db.has_column("Employee", FIELDNAME))


class TestTheRoomIsMadeForIt(FrappeTestCase):
	"""tabEmployee carries 115 varchar(140) columns and sits at 65,182 of InnoDB's 65,535
	byte row limit. The next varchar(140) needs 562 and there are 353 left, so adding the
	field fails outright with "(1118, 'Row size too large...')" and takes the migrate with
	it. Three columns left behind by removed Custom Fields are dropped to make the room."""

	def setUp(self):
		self.source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "drop_empty_orphan_employee_columns.py"
			)
		)

	def test_it_runs_before_the_field_is_added(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt")).splitlines()
		drop = next(i for i, line in enumerate(patches) if "drop_empty_orphan_employee_columns" in line)
		add = next(i for i, line in enumerate(patches) if "add_employee_occupational_sector" in line)
		self.assertLess(drop, patches.index("[post_model_sync]"))
		self.assertLess(drop, add)

	def test_it_only_drops_the_three_columns_it_names(self):
		"""A column is dropped for good, so the list is written out rather than discovered."""
		self.assertIn(
			'COLUMNS = ("one_fm_work_permit", "pam_authorized_signatory", "pam_visa")', self.source
		)

	def test_it_checks_before_it_drops(self):
		"""No field claims it, it is there, and every row is empty - a column that has come
		back into use or turns out to hold data is left alone and the migrate still passes."""
		self.assertIn("if column in claimed:", self.source)
		self.assertIn('if not frappe.db.has_column("Employee", column):', self.source)
		self.assertIn("IS NOT NULL AND", self.source)
		self.assertEqual(self.source.count("continue"), 3)

	def test_the_columns_it_names_are_not_fields_on_the_employee(self):
		claimed = {df.fieldname for df in frappe.get_meta("Employee").fields}
		for column in ("one_fm_work_permit", "pam_authorized_signatory", "pam_visa"):
			with self.subTest(column=column):
				self.assertNotIn(column, claimed)


class TestTheBackfill(FrappeTestCase):
	"""A fetch runs when the form is saved, so the field arrives empty on every record that
	already exists and stays empty until somebody opens it."""

	def setUp(self):
		self.source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "backfill_employee_occupational_sector.py"
			)
		)

	def test_it_runs_after_the_field_is_added(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt")).splitlines()
		add = next(i for i, line in enumerate(patches) if "add_employee_occupational_sector" in line)
		fill = next(
			i for i, line in enumerate(patches) if "backfill_employee_occupational_sector" in line
		)
		self.assertGreater(fill, add)

	def test_it_waits_for_the_column(self):
		"""The column arrives with the patch before it; without the guard a site part way
		through the migrate fails on a column that is about to exist."""
		self.assertIn('if not frappe.db.has_column("Employee", FIELDNAME):', self.source)

	def test_it_groups_by_sector_not_by_designation(self):
		"""Three thousand designations, nine sectors between them, and no index on the
		column - one statement per designation would scan the employee table three
		thousand times over."""
		self.assertIn("designations_by_sector", self.source)
		self.assertIn("Employee.one_fm_pam_designation.isin(designations)", self.source)

	def test_it_does_not_save_the_employees(self):
		"""Every Employee controller hook would fire for a figure none of them read."""
		self.assertNotIn("get_doc", self.source)
		self.assertNotIn(".save(", self.source)

	def test_it_clears_a_sector_the_designation_no_longer_says(self):
		"""A value left behind by an earlier designation would read as fact."""
		self.assertIn(f'.set(Employee[FIELDNAME], None)', self.source)

	def test_every_employee_with_a_designation_carries_its_sector(self):
		"""The backfill itself, asserted against the live site once it has run."""
		if not frappe.db.has_column("Employee", FIELDNAME):
			self.skipTest("the field's own patch has not run on this site yet")

		sectors = {
			d.name: d.occupational_sector
			for d in frappe.get_all(
				"PAM Designation List",
				filters={"occupational_sector": ["is", "set"]},
				fields=["name", "occupational_sector"],
				limit_page_length=0,
			)
		}
		wrong = [
			e.name
			for e in frappe.get_all(
				"Employee",
				filters={"one_fm_pam_designation": ["is", "set"]},
				fields=["name", "one_fm_pam_designation", FIELDNAME],
				limit_page_length=0,
			)
			if e.one_fm_pam_designation in sectors
			and e.get(FIELDNAME) != sectors[e.one_fm_pam_designation]
		]
		self.assertEqual(
			len(wrong), 0, f"{len(wrong)} employees are missing their sector, e.g. {wrong[:5]}"
		)
