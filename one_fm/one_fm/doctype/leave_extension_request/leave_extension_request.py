# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, add_to_date, add_days
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_number_of_leave_days


class LeaveExtensionRequest(Document):
	def validate(self):
		self.validate_resumption_date()
		self.calculate_leave_days()

	def on_submit(self):
		try:
			total_leave_days = self.additional_leave_days
			unpaid_leave_days = self.leave_without_pay
			paid_leave_days = total_leave_days - unpaid_leave_days

			if paid_leave_days > 0:
				self.create_leave_application(from_date=self.paid_leave_start_date, to_date=self.paid_leave_end_date, is_paid=True)

			if unpaid_leave_days > 0:
				self.create_leave_application(from_date=self.unpaid_leave_start_date, to_date=self.unpaid_leave_end_date, is_paid=False)
		except:
			frappe.log_error(message=frappe.get_traceback(), title="Error while creating leave application from leave extension request")
			raise

	def validate_resumption_date(self):
		if getdate(self.new_resumption_date) <= getdate(self.expected_resumption_date):
			frappe.throw(_("New resumption date must be after the expected resumption date."))

	def calculate_leave_days(self):
		holiday_list = frappe.db.get_value("Employee", self.employee, "holiday_list")

		leave_start_date = getdate(self.expected_resumption_date)
		leave_end_date = getdate(add_to_date(self.new_resumption_date, days=-1))

		total_leave_days = int(get_number_of_leave_days(
			employee=self.employee,
			from_date=leave_start_date,
			to_date=leave_end_date,
			leave_type=self.leave_type,
			holiday_list=holiday_list
		))

		current_leave_balance = int(get_leave_balance_on(
			employee=self.employee,
			date=leave_start_date,
			to_date=leave_end_date,
			leave_type=self.leave_type,
			consider_all_leaves_in_the_allocation_period=True,
			for_consumption=True
		).get("leave_balance"))

		leave_days_without_pay = max(0, total_leave_days - current_leave_balance) if current_leave_balance > 0 else total_leave_days

		self.additional_leave_days = total_leave_days
		self.current_leave_balance = current_leave_balance
		self.leave_without_pay = leave_days_without_pay

		holidays = frappe.get_all("Holiday", filters={"parent": holiday_list}, fields=["holiday_date"])
		holiday_set = {getdate(h["holiday_date"]) for h in holidays}

		paid_days = 0
		unpaid_days = 0
		current_date = leave_start_date

		paid_leave_start_date = None
		paid_leave_end_date = None
		unpaid_leave_start_date = None
		unpaid_leave_end_date = None

		while current_date <= leave_end_date:
			if current_date not in holiday_set:
				if paid_days < current_leave_balance:
					if not paid_leave_start_date:
						paid_leave_start_date = current_date
					paid_leave_end_date = current_date
					paid_days += 1
				else:
					if not unpaid_leave_start_date:
						unpaid_leave_start_date = current_date
					unpaid_leave_end_date = current_date
					unpaid_days += 1

			current_date = getdate(add_days(current_date, 1))

		self.paid_leave_start_date = paid_leave_start_date
		self.paid_leave_end_date = paid_leave_end_date
		self.unpaid_leave_start_date = unpaid_leave_start_date
		self.unpaid_leave_end_date = unpaid_leave_end_date

	def create_leave_application(self, from_date, to_date, is_paid):
		custom_reliever_, custom_reliever_name = frappe.db.get_value("Leave Application", self.leave_application, ["custom_reliever_", "custom_reliever_name"])

		leave_application = frappe.new_doc("Leave Application")
		leave_application.employee = self.employee
		leave_application.leave_type = self.leave_type if is_paid else "Leave Without Pay"
		leave_application.custom_is_paid = is_paid
		leave_application.from_date = from_date
		leave_application.to_date = to_date
		leave_application.resumption_date = add_to_date(to_date, days=1)
		leave_application.leave_approver = self.approver
		leave_application.leave_approver_name = self.approver_name
		leave_application.custom_reliever_ = custom_reliever_
		leave_application.custom_reliever_name = custom_reliever_name
		leave_application.custom_leave_extension_request = self.name

		leave_application.flags.ignore_permissions = True
		leave_application.insert()
		leave_application.submit()
