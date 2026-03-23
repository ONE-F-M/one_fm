# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days, date_diff, today
import datetime
import json

class EventStaff(Document):
	def validate(self):
		self.validate_date()
		self.validate_staffing_requirement()
		self.validate_overlapping_event_staff()

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

	def on_submit(self):
		client_event_state = frappe.db.get_value("Client Event", self.client_event, "workflow_state")
		if client_event_state == "Approved":
			self.process_employee_schedules()

	def process_employee_schedules(self, start_date=None):
		start_date = getdate(start_date) if start_date else getdate(self.start_date)
		end_date = getdate(self.end_date)
		existing_schedules = get_existing_schedules(self.employee, start_date, end_date)
		
		# Group by date
		schedules_by_date = {}
		for d in existing_schedules:
			date_key = frappe.utils.getdate(d.date)
			if date_key not in schedules_by_date:
				schedules_by_date[date_key] = []
			schedules_by_date[date_key].append(d)

		number_of_days = date_diff(end_date, start_date) + 1

		for i in range(number_of_days):
			current_date = add_days(start_date, i)
			start_end_datetime = self.get_event_start_end_date_time(current_date)
			employee_schedule_data = self.get_schedule_data(start_end_datetime, current_date)

			new_start_dt = frappe.utils.get_datetime(start_end_datetime.get("start_datetime"))
			new_end_dt = frappe.utils.get_datetime(start_end_datetime.get("end_datetime"))

			day_schedules = schedules_by_date.get(current_date, [])

			overlap_found = False
			schedule_to_update = None

			for existing in day_schedules:
				existing_start_dt = frappe.utils.get_datetime(existing.start_datetime) if existing.start_datetime else None
				existing_end_dt = frappe.utils.get_datetime(existing.end_datetime) if existing.end_datetime else None
				
				is_overlapping = False
				if existing_start_dt and existing_end_dt:
					if existing_start_dt < new_end_dt and existing_end_dt > new_start_dt:
						is_overlapping = True
				else:
					is_overlapping = True

				if existing.roster_type == self.roster_type:
					overlap_found = True
					schedule_to_update = existing.name
					break
				elif is_overlapping:
					if existing.roster_type == "Basic" and self.roster_type == "Over-Time":
						frappe.throw(f"Validation Error: The designated Overtime Event Staff schedule overlaps with an existing Basic Employee Schedule ({existing.name}) for {self.employee}.")
					else:
						frappe.throw(f"Validation Error: The Event Staff schedule overlaps with an existing Employee Schedule ({existing.name}) for {self.employee}.")

			if overlap_found and schedule_to_update:
				schedule_doc = frappe.get_doc("Employee Schedule", schedule_to_update)
				schedule_doc.update(employee_schedule_data)
				schedule_doc.save(ignore_permissions=True)
			else:
				new_schedule = frappe.new_doc("Employee Schedule")
				new_schedule.update(employee_schedule_data)
				new_schedule.insert(ignore_permissions=True)
			frappe.msgprint(f"Employee Schedule for {current_date} processed.", alert=True)

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

	def get_schedule_data(self, start_end_datetime, current_date):
		return {
			"employee": self.employee,
			"date": current_date,
			"employee_availability": "Client Event",
			"is_event_schedule": 1,
			"event_staff": self.name,
			"shift": self.operations_shift,
			"shift_type": self.shift_type,
			"project": self.project,
			"site": self.site,
			"start_datetime": start_end_datetime.get("start_datetime"),
			"end_datetime": start_end_datetime.get("end_datetime"),
			"designation": self.designation,
			"roster_type": self.roster_type,
			"day_off_ot": self.day_off_ot,
			"client_event": self.client_event,
			"event_location": self.event_location,
			"reference_doctype": "Event Staff",
			"reference_docname": self.name,
			"operations_role": None,
			"post_abbrv": None,
		}

	def before_update_after_submit(self):
		if self.has_value_changed("end_date"):
			if getdate(self.end_date) < getdate(today()):
				frappe.throw("Past dates cannot be provided in End Date field.")

			if getdate(self.end_date) < getdate(self.start_date):
				frappe.throw("End Date cannot be before Start Date.")

			# Sync the date portion of end_datetime to the new end_date,
			# keeping the original time component intact.
			if self.end_datetime:
				original_time = frappe.utils.get_datetime(self.end_datetime).time()
				new_end_datetime = datetime.datetime.combine(getdate(self.end_date), original_time)
				self.end_datetime = new_end_datetime

	def on_update_after_submit(self):
		client_event_state = frappe.db.get_value("Client Event", self.client_event, "workflow_state")
		if client_event_state != "Approved":
			return
		old_doc = self.get_doc_before_save()
		if getdate(self.end_date) < getdate(old_doc.end_date):
			self.delete_employee_schedules(self.end_date)
		elif getdate(self.end_date) > getdate(old_doc.end_date):
			new_start_date = add_days(getdate(old_doc.end_date), 1)
			conflicting_dates = get_conflicting_dates(self.employee, new_start_date, self.end_date)
			if conflicting_dates:
				frappe.throw(f"Cannot extend the event as there are conflicting schedules on the following dates: {', '.join(conflicting_dates)}")

			self.process_employee_schedules(start_date=new_start_date)

	def delete_employee_schedules(self, date):
		frappe.db.delete(
			"Employee Schedule",
			{
				"event_staff": self.name,
				"date": [">", getdate(date)]
			}
		)
		frappe.msgprint("Employee Schedules linked to the staff event beyond the new End Date have been deleted.", alert=True)

	def on_cancel(self):
		self.cleanup_employee_schedules_on_cancel()

	def cleanup_employee_schedules_on_cancel(self):
		"""
		Deletes Employee Schedules linked to this cancelled Event Staff
		only if they have no associated Shift Assignments.
		"""
		employee_schedules = get_existing_schedules(event_staff=self.name)
		if not employee_schedules:
			return

		deleted_count = 0
		preserved_count = 0

		for schedule in employee_schedules:
			schedule_name = schedule.get("name")
			has_shift_assignment = frappe.db.exists("Shift Assignment", {"employee_schedule": schedule_name})
			if not has_shift_assignment:
				try:
					frappe.delete_doc("Employee Schedule", schedule_name, ignore_permissions=True)
					deleted_count += 1
				except Exception as e:
					frappe.log_error(
						message=f"Failed to delete Employee Schedule {schedule_name} for Event Staff {self.name}: {frappe.get_traceback()}",
						title="Event Staff Cancellation Error"
					)
			else:
				preserved_count += 1

		if deleted_count or preserved_count:
			message = f"Event Staff cancelled. {deleted_count} unused Employee Schedule(s) deleted."
			if preserved_count:
				message += f" {preserved_count} schedule(s) preserved as they are linked to Shift Assignments."
			frappe.msgprint(message)

@frappe.whitelist()
def get_conflicting_dates(employee, start_date, end_date):
	if not employee or not start_date or not end_date:
		return []

	conflicting_schedules = get_existing_schedules(employee, start_date, end_date)

	return [schedule.get("date").strftime("%Y-%m-%d") for schedule in conflicting_schedules]

def get_existing_schedules(employee=None, start_date=None, end_date=None, event_staff=None):
	if not event_staff and not (employee and start_date and end_date):
		return []

	filters = {"docstatus": 0}

	# Handle employee parameter - could be a list, JSON string, or simple string
	if isinstance(employee, str):
		# Try to parse as JSON first (for list of employees)
		try:
			employee = json.loads(employee)
		except (json.JSONDecodeError, ValueError):
			# If JSON parsing fails, it's a simple employee ID string
			pass

	if event_staff:
		filters["event_staff"] = event_staff
		filters["is_event_schedule"] = 1
	else:
		if isinstance(employee, list):
			filters["employee"] = ["in", employee]
		else:
			filters["employee"] = employee
		filters["date"] = ["between", [start_date, end_date]]

	return frappe.get_all(
		"Employee Schedule",
		filters=filters,
		fields=["name", "date", "start_datetime", "end_datetime", "roster_type"]
	)