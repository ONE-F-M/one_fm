# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, today, getdate
import json

class ClientEvent(Document):
	def validate(self):
		self.set_approver()
		self.validate_workflow_transition()

	def set_approver(self):
		"""Name the Operations Manager when no Project Manager stands behind the event.

		WI-002184: the Project Manager arrives by fetch_from off the Project, so an event
		with no project - or with a project whose manager is not set - has nobody to route
		to. The assignment rule reads a field, not a fallback, so the fallback has to be
		written onto the document: without it the event reaches Pending Operations Manager
		assigned to nobody, and says nothing about it.

		Only filled in, never overwritten: an operations manager named by hand on the event
		is a deliberate choice and outranks the site default.
		"""
		# Read through get(): a Document raises AttributeError for a field its meta does
		# not carry, so a site that has not migrated yet would fail on save rather than
		# simply not having a project manager.
		if self.get("project_manager_user") or self.get("operations_manager"):
			return

		self.operations_manager = frappe.db.get_single_value(
			"Operation Settings", "default_operation_manager"
		)

	def validate_workflow_transition(self):
		if self.is_new():
			return
		if not self.has_value_changed("workflow_state"):
			return
		if self.workflow_state == "Approved":
			return

		# Only act on transitions away from a pending state
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

		# An event that is under way when it is rejected or cancelled keeps its staff until
		# today. The Client Event Lifecycle process refuses the decisions an event's dates do
		# not allow before it applies the state ("Validate Client Event Decision").
		if not self.start_date or not self.end_date:
			return

		today_date = getdate(today())
		event_started = today_date >= getdate(self.start_date)
		event_finished = today_date > getdate(self.end_date)

		if event_started and not event_finished and self.workflow_state in ("Rejected", "Cancelled"):
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


@frappe.whitelist()
def create_client_event_extension(source_name: str):
	"""Create a new Client Event as an extension of the source event.
	Copies all fields except date/datetime fields which must be set by the user.
	"""
	source_doc = frappe.get_doc("Client Event", source_name)

	# Ensure only Approved events can be extended
	if source_doc.workflow_state != "Approved":
		frappe.throw("Only Approved Client Events can be extended.")

	# Prevent duplicate extensions
	existing_extension = frappe.db.exists(
		"Client Event",
		{
			"original_client_event": source_name,
			"docstatus": ["<", 2]
		}
	)
	if existing_extension:
		frappe.throw(
			f"An extension request already exists for this Client Event: {existing_extension}"
		)

	# Fields to exclude from copying (date/datetime fields + system fields)
	exclude_fields = {
		"start_date", "end_date", "event_start_datetime", "event_end_datetime",
		"name", "creation", "modified", "modified_by", "owner",
		"docstatus", "amended_from", "workflow_state",
		"is_extension_request", "original_client_event"
	}

	new_doc = frappe.new_doc("Client Event")

	# Copy all fields from source except excluded ones
	for field in source_doc.meta.fields:
		if field.fieldname not in exclude_fields and field.fieldtype not in ("Section Break", "Column Break"):
			value = source_doc.get(field.fieldname)
			if value is not None:
				new_doc.set(field.fieldname, value)

	# Copy child table rows (staffing_requirements)
	if source_doc.staffing_requirements:
		new_doc.staffing_requirements = []
		for row in source_doc.staffing_requirements:
			new_row = new_doc.append("staffing_requirements", {})
			for field in row.meta.fields:
				if field.fieldname not in {"name", "creation", "modified", "modified_by", "owner", "parent", "parentfield", "parenttype", "idx"}:
					new_row.set(field.fieldname, row.get(field.fieldname))

	# Set extension fields
	new_doc.is_extension_request = 1
	new_doc.original_client_event = source_name

	return new_doc


@frappe.whitelist()
def get_extensible_client_events(doctype, txt, searchfield, start, page_len, filters):
	"""Return Approved Client Events that don't already have an extension."""
	return frappe.db.sql(
		"""
		SELECT ce.name, ce.event_name
		FROM `tabClient Event` ce
		WHERE ce.workflow_state = 'Approved'
		AND ce.docstatus = 1
		AND ce.name NOT IN (
			SELECT original_client_event
			FROM `tabClient Event`
			WHERE original_client_event IS NOT NULL
			AND original_client_event != ''
			AND docstatus < 2
		)
		AND (ce.name LIKE %(txt)s OR ce.event_name LIKE %(txt)s)
		ORDER BY ce.modified DESC
		LIMIT %(start)s, %(page_len)s
		""",
		{"txt": f"%{txt}%", "start": start, "page_len": page_len}
	)
