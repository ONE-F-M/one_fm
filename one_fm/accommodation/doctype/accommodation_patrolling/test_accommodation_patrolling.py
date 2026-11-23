# Copyright (c) 2026, ONE FM and contributors
# See license.txt

from unittest.mock import patch

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


CHECKLIST_ROW = {
	"is_the_corridor_clear": "Yes",
	"add_a_picture_of_the_corridor_captured_with_floor_number": "/files/corridor.png",
	"is_the_right_side_stair_clear": "Yes",
	"add_a_picture_of_the_right_side_stair": "/files/right.png",
	"is_the_left_side_stair_clear": "Yes",
	"add_a_picture_of_the_left_side_stair": "/files/left.png",
	"number_of_incidents": "No",
	"observations_and_incidents": "None",
	"presence_of_unauthorized_persons": "No",
	"overall_summary_of_patrol": "All clear",
	"new_arrivals": "No",
}


def get_floor(number):
	name = frappe.db.get_value("Floor", {"floor": number}, "name")
	if name:
		return name
	return frappe.get_doc({"doctype": "Floor", "floor": number, "floor_name": f"Test Floor {number}"}).insert().name


def get_accommodation():
	if not frappe.db.exists("Accommodation Type", "Test Acc Type"):
		frappe.get_doc({"doctype": "Accommodation Type", "accommodation_type": "Test Acc Type"}).insert()
	name = frappe.db.get_value("Accommodation", {"accommodation": "Test Patrol Building"}, "name")
	if not name:
		name = frappe.get_doc(
			{
				"doctype": "Accommodation",
				"accommodation": "Test Patrol Building",
				"type": "Test Acc Type",
				"status": "Active",
				"total_no_of_floor": 5,
			}
		).insert().name
	return name


def make_patrolling(floor=1, checklist=None, **kwargs):
	doc = frappe.get_doc(
		{
			"doctype": "Accommodation Patrolling",
			"accommodation_buildingarea_covered": get_accommodation(),
			"floor_number": get_floor(floor) if floor is not None else None,
			"condition_of_entryexit_points": "Secured",
			**kwargs,
		}
	)
	for row in checklist if checklist is not None else [{}]:
		doc.append("accommodation_patrolling_checklist", {**CHECKLIST_ROW, **row})
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
		doc = make_patrolling(floor=None)
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_incidents_yes_requires_observations(self):
		doc = make_patrolling(checklist=[{"number_of_incidents": "Yes", "observations_and_incidents": ""}])
		self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_ba_mandatory_fields(self):
		for fieldname in ("accommodation_buildingarea_covered", "condition_of_entryexit_points"):
			doc = make_patrolling(**{fieldname: None})
			self.assertRaises(frappe.MandatoryError, doc.insert)
		self.assertRaises(frappe.MandatoryError, make_patrolling(checklist=[]).insert)
		for fieldname in CHECKLIST_ROW:
			doc = make_patrolling(checklist=[{fieldname: None}])
			self.assertRaises(frappe.MandatoryError, doc.insert)

	def test_floor_is_a_link_filtered_by_building_floors(self):
		meta = frappe.get_meta("Accommodation Patrolling")
		df = meta.get_field("floor_number")
		self.assertEqual((df.fieldtype, df.options), ("Link", "Floor"))
		self.assertIn("doc.total_no_of_floor", df.link_filters)
		self.assertEqual(meta.get_field("total_no_of_floor").fetch_from, "accommodation_buildingarea_covered.total_no_of_floor")
		doc = make_patrolling().insert()
		self.assertEqual(doc.total_no_of_floor, 5)

	def test_unknown_floor_is_refused(self):
		doc = make_patrolling()
		doc.floor_number = "No Such Floor"
		self.assertRaises(frappe.LinkValidationError, doc.insert)

	def test_workflow_state_field(self):
		df = frappe.get_meta("Accommodation Patrolling").get_field("workflow_state")
		self.assertEqual((df.fieldtype, df.options, df.hidden), ("Link", "Workflow State", 1))

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

	def test_number_of_patrolling_field(self):
		df = frappe.get_meta("Accommodation Patrolling").get_field("number_of_patrolling")
		self.assertEqual(df.fieldtype, "Int")
		self.assertTrue(df.read_only)
		self.assertTrue(df.no_copy)


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

		doc.floor_number = get_floor(2)
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


class TestNumberOfPatrolling(FrappeTestCase):
	def setUp(self):
		for day in ("2026-11-18", "2026-11-19"):
			frappe.db.delete("Series", {"name": f"ACC-PATROL-{day}"})

	def insert_at(self, timestamp, **kwargs):
		with patch(
			"one_fm.accommodation.doctype.accommodation_patrolling.accommodation_patrolling.now_datetime",
			return_value=get_datetime(timestamp),
		):
			return make_patrolling(**kwargs).insert()

	def test_daily_sequence_restarts_next_day(self):
		numbers = [
			self.insert_at(f"2026-11-18 {time}").number_of_patrolling for time in ("05:00", "15:00", "17:00")
		]
		self.assertEqual(numbers, [1, 2, 3])
		self.assertEqual(self.insert_at("2026-11-19 05:00").number_of_patrolling, 1)

	def test_resave_keeps_number(self):
		doc = self.insert_at("2026-11-18 05:00")
		doc.floor_number = get_floor(3)
		doc.save()
		doc.reload()
		self.assertEqual(doc.number_of_patrolling, 1)

	def test_failed_insert_does_not_use_a_number(self):
		self.insert_at("2026-11-18 05:00")
		# A failed request rolls back; the savepoint stands in for that here.
		frappe.db.savepoint("failed_patrol")
		self.assertRaises(frappe.MandatoryError, self.insert_at, "2026-11-18 06:00", floor=None)
		frappe.db.rollback(save_point="failed_patrol")
		self.assertEqual(self.insert_at("2026-11-18 07:00").number_of_patrolling, 2)
