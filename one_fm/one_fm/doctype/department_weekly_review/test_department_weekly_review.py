# Copyright (c) 2025, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.department import get_department_custom_fields


class TestDepartmentWeeklyReview(FrappeTestCase):
	@patch("one_bpmn.one_bpmn.trigger.on_doc_event")
	def test_review_carries_the_department_head(self, _trigger):
		create_custom_fields(get_department_custom_fields(), update=True)
		employee = frappe.get_all(
			"Employee",
			filters={"status": "Active", "user_id": ["is", "set"], "department": ["is", "set"]},
			fields=["name", "user_id", "department", "company"],
			limit=1,
		)[0]
		frappe.db.set_value("Department", employee.department, "custom_department_head", employee.user_id)

		review = frappe.get_doc({
			"doctype": "Department Weekly Review",
			"department": employee.department,
			"week": 1,
			"year": frappe.get_all("Fiscal Year", limit=1, pluck="name")[0],
			"company": employee.company,
			"attendees": [{"employee": employee.name}],
		}).insert()

		self.assertEqual(review.department_head, employee.user_id)
