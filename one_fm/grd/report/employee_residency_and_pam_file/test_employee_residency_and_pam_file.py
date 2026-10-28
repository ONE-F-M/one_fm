# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import json
import os
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from one_fm.grd.report.employee_residency_and_pam_file import (
	employee_residency_and_pam_file as report,
)

EXPECTED_FIELDNAMES = [
	"name",
	"employee_name",
	"under_company_residency",
	"pam_file",
	"pam_file_number",
	"one_fm_nationality",
	"one_fm_civil_id",
]

GET_LIST = "one_fm.grd.report.employee_residency_and_pam_file.employee_residency_and_pam_file.frappe.get_list"


class TestEmployeeResidencyAndPAMFile(FrappeTestCase):
	def test_column_fieldnames_and_order(self):
		columns = report.get_columns()
		self.assertEqual([c["fieldname"] for c in columns], EXPECTED_FIELDNAMES)

	def test_column_labels_and_types(self):
		columns = {c["fieldname"]: c for c in report.get_columns()}
		self.assertEqual(columns["name"]["options"], "Employee")
		self.assertEqual(columns["under_company_residency"]["fieldtype"], "Check")
		self.assertEqual(columns["pam_file"]["options"], "PAM License Details")
		self.assertEqual(columns["one_fm_nationality"]["options"], "Nationality")

	def test_pam_file_filter_reaches_get_list_as_pam_file(self):
		with patch(GET_LIST, return_value=[]) as get_list:
			report.execute({"pam_file": "PAM-1"})
		kwargs = get_list.call_args.kwargs
		self.assertEqual(kwargs["filters"], {"pam_file": "PAM-1"})
		self.assertNotIn("pam_file_number", kwargs["filters"])
		self.assertEqual(get_list.call_args.args[0], "Employee")
		self.assertEqual(kwargs["fields"], EXPECTED_FIELDNAMES)
		self.assertEqual(kwargs["order_by"], "employee_name asc")

	def test_nationality_filter_passes_through(self):
		with patch(GET_LIST, return_value=[]) as get_list:
			report.execute({"one_fm_nationality": "Kuwaiti"})
		self.assertEqual(get_list.call_args.kwargs["filters"], {"one_fm_nationality": "Kuwaiti"})

	def test_empty_filters_give_no_filters(self):
		for empty in (None, {}, {"pam_file": "", "one_fm_nationality": None}):
			with patch(GET_LIST, return_value=[]) as get_list:
				report.execute(empty)
			self.assertEqual(get_list.call_args.kwargs["filters"], {})

	def test_unknown_keys_are_dropped(self):
		with patch(GET_LIST, return_value=[]) as get_list:
			report.execute({"pam_file_number": "123", "status": "Active", "pam_file": "PAM-1"})
		self.assertEqual(get_list.call_args.kwargs["filters"], {"pam_file": "PAM-1"})

	def test_execute_returns_rows_from_get_list(self):
		rows = [{"name": "HR-EMP-1", "employee_name": "A"}]
		with patch(GET_LIST, return_value=rows):
			columns, data = report.execute({})
		self.assertEqual(data, rows)
		self.assertEqual(len(columns), 7)

	def test_report_json_is_standard_employee_report(self):
		path = os.path.join(os.path.dirname(__file__), "employee_residency_and_pam_file.json")
		with open(path) as f:
			doc = json.load(f)
		self.assertEqual(doc["ref_doctype"], "Employee")
		self.assertEqual(doc["is_standard"], "Yes")
		self.assertEqual(doc["report_type"], "Script Report")
		self.assertEqual(doc["module"], "GRD")
