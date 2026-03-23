# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime, today, getdate
import json

class ClientEvent(Document):
	def validate(self):
		self.validate_date_time()
		self.validate_workflow_transition()

	def validate_date_time(self):
		if not self.is_new() and self.workflow_state not in ("Pending Operations Manager", None):
			return
		if self.workflow_state == "Approved":
			return
		today_date = getdate(today())

		# Rule 1: Start Date or Start Datetime must be current or future date
		if self.start_date and getdate(self.start_date) < today_date:
			frappe.throw("The scheduled event time must be current or future date/time. Please adjust the event details.")
		if self.event_start_datetime and getdate(self.event_start_datetime) < today_date:
			frappe.throw("The scheduled event time must be current or future date/time. Please adjust the event details.")

		# Rule 2: End Date or End Datetime must be current or future date
		if self.end_date and getdate(self.end_date) < today_date:
			frappe.throw("The scheduled end date/time must be current or future date/time. Please adjust the event details.")
		if self.event_end_datetime and getdate(self.event_end_datetime) < today_date:
			frappe.throw("The scheduled end date/time must be current or future date/time. Please adjust the event details.")

		# Rule 3: End must be after Start
		if self.start_date and self.end_date and get_datetime(self.end_date) < get_datetime(self.start_date):
			frappe.throw("The scheduled end date/time must be later than Start Date or Start Datetime. Please adjust the event details.")
		if self.event_start_datetime and self.event_end_datetime and get_datetime(self.event_end_datetime) < get_datetime(self.event_start_datetime):
			frappe.throw("The scheduled end date/time must be later than Start Date or Start Datetime. Please adjust the event details.")

	def validate_workflow_transition(self):
		if self.is_new():
			return
		if not self.has_value_changed("workflow_state"):
			return
		if self.workflow_state == "Approved":
			return

		# Only act on transitions away from Pending Operations Manager
		if self.workflow_state not in ("Draft", "Rejected", "Cancelled"):
			return

		# 1. Cancel all submitted Event Staff
		cancelled_count = self.cancel_submitted_event_staff()

		# 2. Delete all draft Event Staff
		deleted_count = self.delete_draft_event_staff()

		if cancelled_count or deleted_count:
			parts = []
			if cancelled_count:
				parts.append(f"{cancelled_count} submitted Event Staff record(s) cancelled")
			if deleted_count:
				parts.append(f"{deleted_count} draft Event Staff record(s) deleted")
			frappe.msgprint(
				"Workflow transition: " + " and ".join(parts) + ".",
				alert=True
			)

		# Preserve date-based guards for events already in progress or finished
		if not self.start_date or not self.end_date:
			return

		today_date = getdate(today())
		start_date = getdate(self.start_date)
		end_date = getdate(self.end_date)

		event_started = today_date >= start_date
		event_finished = today_date > end_date

		if event_finished:
			if self.workflow_state in ("Draft", "Rejected"):
				frappe.throw(
					f"You are unable to {self.workflow_state.lower()} this client event as the event has already taken place. Please approve."
				)
			elif self.workflow_state == "Cancelled":
				frappe.throw(
					"You are unable to cancel this client event as the event has already taken place."
				)
		elif event_started:
			if self.workflow_state == "Draft":
				frappe.throw(
					"You are unable to return this client event to draft as the event has already started. Please approve."
				)
			elif self.workflow_state in ("Rejected", "Cancelled"):
				self.handle_ongoing_event_cancellation()

	def cancel_submitted_event_staff(self):
		"""Cancel submitted Event Staff in the background to avoid timeout."""
		submitted_count = frappe.db.count("Event Staff", {"client_event": self.name, "docstatus": 1})
		if submitted_count > 0:
			frappe.enqueue(
				"one_fm.one_fm.doctype.client_event.client_event.cancel_event_staff_background",
				client_event=self.name,
				queue="long",
				timeout=1500
			)
		return submitted_count

	def delete_draft_event_staff(self):
		"""Delete all draft Event Staff linked to this Client Event using fast SQL deletion."""
		draft_count = frappe.db.count("Event Staff", {"client_event": self.name, "docstatus": 0})
		if draft_count > 0:
			# Fast SQL delete bypassing validation
			frappe.db.delete("Event Staff", {"client_event": self.name, "docstatus": 0})
		return draft_count

	def handle_ongoing_event_cancellation(self, event_started=True):
		# Update end_date for all related Event Staff records
		event_staffs = frappe.get_all(
			"Event Staff",
			filters={"client_event": self.name, "docstatus": 1},
			fields=["name"]
		)
		if not event_staffs:
			return
		for event_staff in event_staffs:
			event_staff_doc = frappe.get_doc("Event Staff", event_staff.name)
			if not event_started:
				event_staff_doc.cancel()
			else:
				event_staff_doc.end_date = getdate(today())
				event_staff_doc.save(ignore_permissions=True)
		frappe.msgprint("All related Event Staff records have been updated due to changes in the status of this client event.", alert=True)

	def on_cancel(self):
		self.validate_workflow_transition()

	def on_submit(self):
		if self.workflow_state == "Approved":
			self.generate_employee_schedules()

	def on_update_after_submit(self):
		self.validate_workflow_transition()
		if self.has_value_changed("workflow_state") and self.workflow_state == "Approved":
			self.generate_employee_schedules()

	def generate_employee_schedules(self):
		event_staffs = frappe.get_all(
			"Event Staff",
			filters={"client_event": self.name, "docstatus": 1},
			fields=["name"]
		)
		if not event_staffs:
			return
		for event_staff in event_staffs:
			event_staff_doc = frappe.get_doc("Event Staff", event_staff.name)
			event_staff_doc.process_employee_schedules()

	@frappe.whitelist()
	def add_event_staff(self, staff):
		staff_data = json.loads(staff)
		for record in staff_data:
			doc = frappe.new_doc("Event Staff")
			doc.client_event = self.name
			doc.employee = record.get("employee")
			doc.operations_role = record.get("operations_role")
			doc.roster_type = record.get("roster_type")
			doc.day_off_ot = record.get("day_off_ot")
			doc.operations_shift = record.get("operations_shift")
			# Explicitly copy date/datetime fields (no longer auto-fetched)
			doc.start_date = self.start_date
			doc.end_date = self.end_date
			doc.start_datetime = self.event_start_datetime
			doc.end_datetime = self.event_end_datetime
			doc.save(ignore_permissions=True)
			doc.submit()
		return True

def cancel_event_staff_background(client_event):
	"""Background job to cancel all submitted Event Staff for a given Client Event."""
	frappe.db.commit() # Ensure any pending transactions are committed before starting
	submitted = frappe.get_all(
		"Event Staff",
		filters={"client_event": client_event, "docstatus": 1},
		fields=["name"]
	)
	
	for es in submitted:
		try:
			doc = frappe.get_doc("Event Staff", es.name)
			doc.cancel()
		except Exception as e:
			frappe.log_error(title="Event Staff Cancellation Error", message=frappe.get_traceback())
			
	# Commit after cancellation block to save progress
	frappe.db.commit()
