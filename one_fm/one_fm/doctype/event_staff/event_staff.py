# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt
"""An employee assigned to a Client Event.

The Event Staff Lifecycle map submits it, writes its Employee Schedules (Create Event Staff
Schedules), and on cancel deletes the unused ones (Release Event Staff Schedules). The rules
live in those scripts. The hooks below only refuse invalid date edits and run the same rules.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today

from one_fm.one_fm.processa_rules import run_rule

CREATE_SCRIPT = "Create Event Staff Schedules"
RELEASE_SCRIPT = "Release Event Staff Schedules"


class EventStaff(Document):
	def before_update_after_submit(self):
		if self.has_value_changed("end_date"):
			if getdate(self.end_date) < getdate(today()):
				frappe.throw(_("Past dates cannot be provided in End Date field."))
			if getdate(self.end_date) < getdate(self.start_date):
				frappe.throw(_("End Date cannot be before Start Date."))

		if self.has_value_changed("start_date"):
			client_event_start = frappe.db.get_value("Client Event", self.client_event, "start_date")
			if client_event_start and getdate(self.start_date) < getdate(client_event_start):
				frappe.throw(_("Start Date cannot be before the linked Client Event's Start Date."))
			if getdate(self.start_date) > getdate(self.end_date):
				frappe.throw(_("Start Date cannot be after End Date."))

		run_rule(CREATE_SCRIPT, "sync_datetimes", self)

	def on_update_after_submit(self):
		if frappe.db.get_value("Client Event", self.client_event, "workflow_state") != "Approved":
			return
		old = self.get_doc_before_save()
		self.validate_new_days_are_free(old)
		run_rule(CREATE_SCRIPT, "apply_date_change", self, old)

	def validate_new_days_are_free(self, old):
		"""Refuse moving the Start Date back or the End Date on onto days the employee is already scheduled."""
		if getdate(self.start_date) < getdate(old.start_date):
			conflicting = get_conflicting_dates(self.employee, self.start_date, add_days(getdate(old.start_date), -1))
			if conflicting:
				frappe.throw(_("Cannot move Start Date back as there are conflicting schedules on: {0}").format(", ".join(conflicting)))
		if getdate(self.end_date) > getdate(old.end_date):
			conflicting = get_conflicting_dates(self.employee, add_days(getdate(old.end_date), 1), self.end_date)
			if conflicting:
				frappe.throw(_("Cannot extend the event as there are conflicting schedules on the following dates: {0}").format(", ".join(conflicting)))



def cancel_event_staff(event_staff, reason):
	"""Cancel a submitted Event Staff for its Client Event, then release its schedules.

	The engine refuses a native cancel on a doctype Processa runs, even once a record's process
	has ended, so this cancels any live process and cancels the record the way the engine does.
	"""
	from one_fm.grd.processa import cancel_document

	cancel_document(event_staff, reason)
	run_rule(RELEASE_SCRIPT, "release_schedules", event_staff)


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
