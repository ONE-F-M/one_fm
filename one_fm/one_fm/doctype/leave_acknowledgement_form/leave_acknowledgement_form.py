# Copyright (c) 2025, omar jaber and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
from frappe.utils import now_datetime






class LeaveAcknowledgementForm(Document):
	

	def on_submit(self):
		self.set_previous_records_inactive()

	
	def set_previous_records_inactive(self):
		query = """ 
				UPDATE `tabLeave Acknowledgement Form`
				SET is_active = 0
				WHERE employee = %s
				AND is_active = 1
				AND NOT name = %s 
				"""
		frappe.db.sql(query, (self.employee, self.name))




def get_employees_with_cf_leaves_over_threshold():
	try:
		date = now_datetime().date()
		threshold = frappe.db.get_single_value("HR Settings", "annual_leave_threshold") or 60
		leave_type = "Annual Leave"

		excluded_employees = frappe.db.get_list(
			"Leave Acknowledgement Form",
			{"is_active": True},
			pluck="employee"
		)

		Ledger = DocType("Leave Ledger Entry")
		LeaveAllocation = DocType("Leave Allocation")

		query = (
			frappe.qb.from_(Ledger)
			.inner_join(LeaveAllocation).on(Ledger.transaction_name == LeaveAllocation.name)
			.select(Ledger.employee, Sum(Ledger.leaves).as_("cf_leaves"))
			.where(
				(Ledger.from_date <= date)
				& (Ledger.docstatus == 1)
				& (Ledger.transaction_type == "Leave Allocation")
				& (Ledger.is_expired == 0)
				& (Ledger.is_lwp == 0)
				& (Ledger.is_carry_forward == 1)
				& (Ledger.to_date.between(LeaveAllocation.from_date, LeaveAllocation.to_date))
				& (LeaveAllocation.from_date <= date)
				& (date <= LeaveAllocation.to_date)
			)
		)

		if leave_type:
			query = query.where(Ledger.leave_type == leave_type)

		if excluded_employees:
			query = query.where(Ledger.employee.notin(excluded_employees))

		query = query.groupby(Ledger.employee)
		query = query.having(Sum(Ledger.leaves) >= threshold)

		results = query.run(as_dict=True)

		employee_details = frappe.get_all(
			"Employee",
			filters={"name": ["in", [row.employee for row in results]]},
			fields=["name", "custom_civil_id_assurance_level"]
		)

		return {
			emp["name"]: emp.get("custom_civil_id_assurance_level", "")
			for emp in employee_details
		}

	except Exception:
		frappe.log_error(frappe.get_traceback(), "Error fetching employees with leaves more than the threshold")
		return {}
		



def generate_leave_acknowledgement():
	employees = get_employees_with_cf_leaves_over_threshold()

	if employees:
		for emp in employees.keys():
			doc = frappe.get_doc({
				"doctype": "Leave Acknowledgement Form",
				"employee": emp
			})
			doc.insert(ignore_permissions=True)

			new_state = "Pending Confirmation" if employees.get(emp) == "High" else "Pending HR"
			frappe.db.set_value("Leave Acknowledgement Form", doc.name, "workflow_state", new_state)

		frappe.db.commit()

