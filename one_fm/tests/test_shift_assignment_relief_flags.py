"""Shift Assignments copy the relief flags and covered leave from their Employee Schedule."""
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.api import tasks

TEST_DATE = "2099-01-05"
DEFAULT_SHIFT_NAME = '"Standard|Morning|08:00:00-17:00:00|9 hours"'


def make_schedule(employee, **flags):
	return frappe._dict({
		"name": f"{employee}-sched",
		"doctype": "Employee Schedule",
		"employee": employee,
		"employee_name": employee,
		"shift_type": "_Test Relief Shift Type",
		"department": "",
		"roster_type": "Basic",
		"employee_availability": "Working",
		**flags,
	})


class TestRawInsertReliefFlags(FrappeTestCase):
	def run_create(self, roster):
		original_get_doc = frappe.get_doc
		default_shift = MagicMock()
		default_shift.as_dict.return_value = frappe._dict(
			name=DEFAULT_SHIFT_NAME, shift_type="Standard",
			start_datetime=f"{TEST_DATE} 08:00:00", end_datetime=f"{TEST_DATE} 17:00:00",
		)

		def get_doc(*args, **kwargs):
			if args[:2] == ("Shift Type", DEFAULT_SHIFT_NAME):
				return default_shift
			return original_get_doc(*args, **kwargs)

		with patch.object(frappe.db, "commit"), \
			patch("frappe.get_doc", side_effect=get_doc), \
			patch.object(tasks, "sendemail"), \
			patch.object(tasks, "get_today_leaves", return_value=[]):
			tasks.create_shift_assignment(roster, TEST_DATE, "AM")

	def get_assignment(self, employee):
		return frappe.db.get_value(
			"Shift Assignment", f"HR-SHA-{TEST_DATE}-{employee}",
			["custom_is_day_off_reliever", "custom_is_weekend_reliever",
				"custom_is_annual_leave_reliever", "custom_leave_application"],
			as_dict=True,
		)

	def test_annual_leave_reliever_carries_flag_and_leave(self):
		self.run_create([make_schedule("_T-RLF-AL", is_annual_leave_reliever=1, leave_application="_T-LEAVE-1")])
		row = self.get_assignment("_T-RLF-AL")
		self.assertEqual(row.custom_is_annual_leave_reliever, 1)
		self.assertEqual(row.custom_leave_application, "_T-LEAVE-1")
		self.assertEqual(row.custom_is_day_off_reliever, 0)

	def test_day_off_and_weekend_relievers(self):
		self.run_create([
			make_schedule("_T-RLF-DO", is_day_off_reliever=1),
			make_schedule("_T-RLF-WE", is_weekend_reliever=1),
		])
		self.assertEqual(self.get_assignment("_T-RLF-DO").custom_is_day_off_reliever, 1)
		self.assertEqual(self.get_assignment("_T-RLF-WE").custom_is_weekend_reliever, 1)

	def test_unflagged_schedule_gives_zeros(self):
		self.run_create([make_schedule("_T-RLF-NONE")])
		row = self.get_assignment("_T-RLF-NONE")
		self.assertEqual(
			(row.custom_is_day_off_reliever, row.custom_is_weekend_reliever,
				row.custom_is_annual_leave_reliever, row.custom_leave_application or ""),
			(0, 0, 0, ""),
		)

	def test_upsert_refreshes_flags(self):
		self.run_create([make_schedule("_T-RLF-UP")])
		self.run_create([make_schedule("_T-RLF-UP", is_weekend_reliever=1)])
		self.assertEqual(self.get_assignment("_T-RLF-UP").custom_is_weekend_reliever, 1)


class TestOrmPathsReliefFlags(FrappeTestCase):
	def stub_assignment(self):
		stub = frappe._dict()
		stub.insert = MagicMock()
		stub.submit = MagicMock()
		return stub

	def test_overtime_path_carries_flags(self):
		stub = self.stub_assignment()
		schedule = make_schedule("_T-RLF-OT", roster_type="Over-Time", is_annual_leave_reliever=1, leave_application="_T-LEAVE-2")
		with patch("frappe.new_doc", return_value=stub):
			tasks.create_overtime_shift_assignment(schedule, TEST_DATE)
		stub.submit.assert_called_once()
		self.assertEqual(stub.custom_is_annual_leave_reliever, 1)
		self.assertEqual(stub.custom_leave_application, "_T-LEAVE-2")
		self.assertEqual(stub.custom_is_day_off_reliever, 0)

	def test_overtime_from_shift_request_gives_zeros(self):
		stub = self.stub_assignment()
		request = frappe._dict(make_schedule("_T-RLF-SR"), doctype="Shift Request")
		with patch("frappe.new_doc", return_value=stub):
			tasks.create_overtime_shift_assignment(request, TEST_DATE)
		stub.submit.assert_called_once()
		self.assertEqual(stub.custom_is_weekend_reliever, 0)
		self.assertIsNone(stub.custom_leave_application)

	def test_rambo_path_carries_flags(self):
		stub = self.stub_assignment()
		schedule = make_schedule(
			"_T-RLF-RB", is_day_off_reliever=1,
			start_datetime=f"{TEST_DATE} 08:00:00", end_datetime=f"{TEST_DATE} 17:00:00",
		)
		with patch.object(frappe.db, "commit"), \
			patch("frappe.new_doc", return_value=stub), \
			patch.object(tasks, "get_today_leaves", return_value=[]), \
			patch.object(tasks, "_handle_existing_shifts_for_rambo", return_value=False):
			tasks.process_rambo_shift_assignment([schedule], TEST_DATE)
		stub.submit.assert_called_once()
		self.assertEqual(stub.custom_is_day_off_reliever, 1)
