from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.employee_checkin import (
	auto_checkin_employee_query,
	create_checkin_record,
	process_list,
)

MODULE = "one_fm.overrides.employee_checkin"
DATE = "2026-11-24"


class TestAutoCheckinEmployeeQuery(FrappeTestCase):
	"""The generated check-in job must not even look at employees who have left."""

	def setUp(self):
		self.sql = auto_checkin_employee_query(DATE).get_sql()

	def test_only_auto_attendance_employees(self):
		self.assertIn("`auto_attendance`=1", self.sql.replace(" ", ""))

	def test_excludes_employees_who_are_not_active(self):
		self.assertIn("`status`='Active'", self.sql.replace(" ", ""))

	def test_excludes_employees_relieved_before_the_shift_date(self):
		compact = self.sql.replace(" ", "")
		self.assertIn("`relieving_date`ISNULL", compact)
		self.assertIn(f"`relieving_date`>='{DATE}'", compact)


class TestCreateCheckinRecord(FrappeTestCase):
	"""The generated record skips validate(), so the guards run explicitly."""

	def test_relieved_employee_gets_no_generated_checkin(self):
		checkin = frappe.new_doc("Employee Checkin")
		checkin.save = MagicMock()
		with (
			patch(f"{MODULE}.frappe.new_doc", return_value=checkin),
			patch(f"{MODULE}.frappe.db.get_value", return_value="2026-11-20"),
		):
			with self.assertRaises(frappe.ValidationError) as context:
				create_checkin_record("HR-EMP-TEST", "IN", "2026-11-24 08:00:00", "SA-TEST")

		self.assertIn("you cannot check in after it", str(context.exception))
		checkin.save.assert_not_called()

	def test_inactive_employee_gets_no_generated_checkin(self):
		checkin = frappe.new_doc("Employee Checkin")
		checkin.save = MagicMock()
		with (
			patch(f"{MODULE}.frappe.new_doc", return_value=checkin),
			patch(f"{MODULE}.frappe.db.get_value", return_value=None),
			patch(f"{MODULE}.validate_active_employee", side_effect=frappe.ValidationError("Inactive")),
		):
			with self.assertRaises(frappe.ValidationError):
				create_checkin_record("HR-EMP-TEST", "IN", "2026-11-24 08:00:00", "SA-TEST")

		checkin.save.assert_not_called()

	def test_eligible_employee_is_still_saved(self):
		checkin = frappe.new_doc("Employee Checkin")
		checkin.save = MagicMock()
		checkin.db_set = MagicMock()
		with (
			patch(f"{MODULE}.frappe.new_doc", return_value=checkin),
			patch(f"{MODULE}.frappe.db.get_value", return_value=None),
			patch(f"{MODULE}.validate_active_employee"),
			patch(f"{MODULE}.frappe.db.commit"),
		):
			create_checkin_record("HR-EMP-TEST", "IN", "2026-11-24 08:00:00", "SA-TEST")

		checkin.save.assert_called_once()
		self.assertTrue(checkin.flags.ignore_validate)


class TestProcessList(FrappeTestCase):
	"""A rejected employee must not cost the rest of the batch their check-ins."""

	def test_a_rejected_employee_is_logged_and_the_batch_continues(self):
		expected = frappe.utils.get_datetime("2026-11-24 08:00:00")
		employee_list = [
			frappe._dict({"ename": "HR-EMP-REJECTED", "sname": "SA-1", "start_datetime": expected, "end_datetime": None}),
			frappe._dict({"ename": "HR-EMP-OK", "sname": "SA-2", "start_datetime": expected, "end_datetime": None}),
		]

		def create(employee, *args, **kwargs):
			if employee == "HR-EMP-REJECTED":
				raise frappe.ValidationError("relieved")

		with (
			patch(f"{MODULE}.create_checkin_record", side_effect=create) as created,
			patch(f"{MODULE}.frappe.db.rollback"),
			patch(f"{MODULE}.frappe.log_error") as logged,
		):
			process_list(employee_list, expected)

		self.assertEqual(created.call_count, 2)
		self.assertEqual(logged.call_count, 1)
		self.assertIn("HR-EMP-REJECTED", logged.call_args.kwargs["title"])
