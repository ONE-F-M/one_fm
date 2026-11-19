# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime, now_datetime

AUTO_FIELDS = (
	"patrolling_date_and_time",
	"name_of_security_officer",
	"email_address",
	"patrol_shift",
	"shift_time",
	"shift_end_time",
)


def make_patrolling(floor_number="1", checklist=None, **kwargs):
	doc = frappe.get_doc({"doctype": "Accommodation Patrolling", "floor_number": floor_number, **kwargs})
	for row in checklist if checklist is not None else [{"number_of_incidents": "No"}]:
		doc.append("accommodation_patrolling_checklist", row)
	return doc


def get_officer():
	"""An existing user whose Employee record has a valid Shift Allocation."""
	Employee = frappe.qb.DocType("Employee")
	OperationsShift = frappe.qb.DocType("Operations Shift")
	rows = (
		frappe.qb.from_(Employee)
		.join(OperationsShift)
		.on(OperationsShift.name == Employee.shift)
		.select(
			Employee.user_id,
			Employee.shift,
			OperationsShift.start_time,
			OperationsShift.end_time,
		)
		.where(Employee.status == "Active")
		.where(Employee.user_id.isnotnull())
		.limit(1)
	).run(as_dict=True)
	return rows[0] if rows else None


class TestAccommodationPatrolling(FrappeTestCase):
	def test_insert_and_submit(self):
		doc = make_patrolling()
		doc.insert()
		doc.submit()
		self.assertEqual(doc.docstatus, 1)

	def test_missing_floor_number_raises(self):
		doc = make_patrolling(floor_number=None)
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_incidents_yes_requires_observations(self):
		doc = make_patrolling(checklist=[{"number_of_incidents": "Yes"}])
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_doctypes_are_not_custom(self):
		for name in ("Accommodation Patrolling", "Accommodation Patrolling Checklist"):
			self.assertEqual(frappe.get_meta(name).custom, 0)

	def test_checklist_has_all_ba_fields(self):
		fieldnames = [df.fieldname for df in frappe.get_meta("Accommodation Patrolling Checklist").fields]
		self.assertEqual(len(fieldnames), 11)
		for fieldname in ("is_the_corridor_clear", "presence_of_unauthorized_persons", "new_arrivals"):
			self.assertIn(fieldname, fieldnames)

	def test_auto_fields_are_read_only(self):
		meta = frappe.get_meta("Accommodation Patrolling")
		for fieldname in AUTO_FIELDS:
			self.assertTrue(meta.get_field(fieldname).read_only, fieldname)
		self.assertEqual(meta.get_field("patrol_shift").options, "Operations Shift")


class TestAccommodationPatrollingAutoFetch(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.officer = get_officer()

	def setUp(self):
		if not self.officer:
			self.skipTest("No active Employee with a user and a valid Shift Allocation on this site")

	def insert_as_officer(self, **kwargs):
		with self.set_user(self.officer.user_id):
			return make_patrolling(**kwargs).insert(ignore_permissions=True)

	def test_officer_details_are_fetched_on_insert(self):
		doc = self.insert_as_officer()
		self.assertLess(abs((now_datetime() - get_datetime(doc.patrolling_date_and_time)).total_seconds()), 60)
		self.assertEqual(doc.name_of_security_officer, self.officer.user_id)
		self.assertEqual(doc.email_address, frappe.db.get_value("User", self.officer.user_id, "email"))
		self.assertEqual(doc.patrol_shift, self.officer.shift)
		self.assertEqual(str(doc.shift_time), str(self.officer.start_time))
		self.assertEqual(str(doc.shift_end_time), str(self.officer.end_time))

	def test_payload_values_are_overwritten(self):
		doc = self.insert_as_officer(
			patrolling_date_and_time="2020-01-01 00:00:00",
			name_of_security_officer="Administrator",
			email_address="someone@example.com",
		)
		self.assertNotEqual(get_datetime(doc.patrolling_date_and_time).year, 2020)
		self.assertEqual(doc.name_of_security_officer, self.officer.user_id)
		self.assertNotEqual(doc.email_address, "someone@example.com")

	def test_later_save_by_another_user_keeps_details(self):
		doc = self.insert_as_officer()
		before = {fieldname: doc.get(fieldname) for fieldname in AUTO_FIELDS}

		doc.floor_number = "2"
		doc.save()  # as Administrator
		doc.reload()

		for fieldname, value in before.items():
			self.assertEqual(str(doc.get(fieldname)), str(value), fieldname)

	def test_user_without_employee_gets_empty_shift(self):
		doc = make_patrolling().insert()  # Administrator has no Employee
		self.assertEqual(doc.name_of_security_officer, "Administrator")
		self.assertFalse(doc.patrol_shift)
		self.assertFalse(doc.shift_time)
		self.assertFalse(doc.shift_end_time)
