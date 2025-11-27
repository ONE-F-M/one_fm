# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days, date_diff, today
import datetime

class EventStaff(Document):
	def validate(self):
		self.validate_date()
		self.validate_staffing_requirement()
		self.validate_overlapping_event_staff()
		self.validate_overlapping_schedules()

	def validate_date(self):
		if getdate(self.end_date) < getdate(self.start_date):
			frappe.throw("End Date cannot be before Start Date.")
		if not self.start_datetime or not self.end_datetime:
			frappe.throw("Start DateTime and End DateTime are mandatory.")
		if frappe.utils.get_datetime(self.end_datetime) <= frappe.utils.get_datetime(self.start_datetime):
			frappe.throw("End DateTime must be after Start DateTime.")

	def validate_staffing_requirement(self):
		if not self.client_event or not self.designation:
			return
		requirements = self.get_event_staffing_requirement()
		if not requirements:
			return
		filters = {
			"client_event": self.client_event,
			"designation": self.designation,
			"docstatus": ["<", 2]
		}
		assigned_count = frappe.db.count("Event Staff", filters)
		if assigned_count > requirements:
			frappe.throw(f"The number of assigned staff for Designation {self.designation} exceeds the required count {requirements}.")

	def get_event_staffing_requirement(self):
		if not self.client_event or not self.designation:
			return 0
		requirement = frappe.db.get_value(
			"Client Event Staff Requirement",
			{
				"parent": self.client_event,
				"parenttype": "Client Event",
				"designation": self.designation
			},
			"count"
		)
		return requirement or 0

	def validate_overlapping_event_staff(self):
		if not self.employee or not self.client_event or not self.start_date or not self.end_date or not self.designation:
			return
		overlapping = frappe.db.sql(
			"""
			SELECT
				name, start_date, end_date FROM `tabEvent Staff`
			WHERE
				employee = %(employee)s AND docstatus < 2 AND name != %(name)s
				AND (
					(start_date <= %(end_date)s AND end_date >= %(start_date)s)
				)
			""",
			{
				"employee": self.employee,
				"start_date": self.start_date,
				"end_date": self.end_date,
				"name": self.name or ""
			},
			as_dict=True
		)
		if overlapping:
			msg = f"{self.employee} already assigned to {self.designation} from {overlapping[0]['start_date']} to {overlapping[0]['end_date']}."
			frappe.throw(msg)

	def validate_overlapping_schedules(self):
		if not self.employee or not self.start_date or not self.end_date:
			return
		overlapping_schedules = frappe.get_all(
			"Employee Schedule",
			filters={
				"employee": self.employee,
				"docstatus": 1,
				"date": ["between", [self.start_date, self.end_date]]
			}
		)
		if overlapping_schedules:
			frappe.throw(f"{self.employee} already scheduled during the selected date range")

	def on_submit(self):
		self.create_employee_schedule()

	def create_employee_schedule(self):
		start_date = getdate(self.start_date)
		end_date = getdate(self.end_date)
		number_of_days = date_diff(end_date, start_date) + 1
		
		for i in range(number_of_days):
			date = add_days(start_date, i)
			start_end_datetime = self.get_event_start_end_date_time(date)
			
			existing_schedule = frappe.db.exists(
				"Employee Schedule",
				{
					"employee": self.employee,
					"date": date,
					"roster_type": self.roster_type
				}
			)
			
			if existing_schedule:
				employee_schedule = frappe.get_doc("Employee Schedule", existing_schedule)
				employee_schedule.shift = self.operations_shift
				employee_schedule.shift_type = self.shift_type
				employee_schedule.employee_availability = 'Working'
				employee_schedule.site = self.site
				employee_schedule.project = self.project
				employee_schedule.reference_doctype = self.doctype
				employee_schedule.reference_docname = self.name
				employee_schedule.is_event_schedule = 1
				employee_schedule.event_staff = self.name
				employee_schedule.day_off_ot = self.day_off_ot
				employee_schedule.start_datetime = start_end_datetime.get("start_datetime")
				employee_schedule.end_datetime = start_end_datetime.get("end_datetime")
				employee_schedule.save(ignore_permissions=True)
			else:
				employee_schedule = frappe.get_doc(
					{
						"doctype": "Employee Schedule",
						"employee": self.employee,
						"date": date,
						"shift": self.operations_shift,
						"shift_type": self.shift_type,
						"employee_availability": 'Working',
						"roster_type": self.roster_type,
						"site": self.site,
						"project": self.project,
						"reference_doctype": self.doctype,
						"reference_docname": self.name,
						"is_event_schedule": 1,
						"event_staff": self.name,
						"day_off_ot": self.day_off_ot,
						"start_datetime": start_end_datetime.get("start_datetime"),
						"end_datetime": start_end_datetime.get("end_datetime")
					}
				)
				employee_schedule.insert(ignore_permissions=True)

	def get_event_start_end_date_time(self, date=None):
		start_time = frappe.utils.get_datetime(self.start_datetime).time()
		end_time = frappe.utils.get_datetime(self.end_datetime).time()
		start_datetime = datetime.datetime.combine(getdate(date), start_time)
		if end_time < start_time:
			end_date = add_days(getdate(date), 1)
		else:
			end_date = getdate(date)
		end_datetime = datetime.datetime.combine(end_date, end_time)
		return {
			"start_datetime": start_datetime,
			"end_datetime": end_datetime
		}

	def on_update_after_submit(self):
		old_doc = self.get_doc_before_save()
		if getdate(self.end_date) < getdate(old_doc.end_date):
			self.delete_employee_schedules(self.end_date)

	def delete_employee_schedules(self, date):
		frappe.db.delete(
			"Employee Schedule",
			{
				"event_staff": self.name,
				"date": [">", getdate(date)]
			}
		)

	def on_cancel(self):
		self.delete_employee_schedules(today())
