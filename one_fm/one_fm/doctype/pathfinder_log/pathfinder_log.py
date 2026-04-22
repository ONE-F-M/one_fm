# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class PathfinderLog(Document):
	def validate(self):
		self._validate_active_status_conditions()
		self.validate_process_classification()
		self.validate_single_active_log()

	def _validate_active_status_conditions(self):
		"""Block saving with status 'Active' when any classification prerequisite is unmet.

		Blocking conditions:
		  1. The selected process has 'Is Generic' checked.
		  2. The Process Folder Link is not set.
		  3. The Epic is not set.
		"""
		if self.status != "Active":
			return

		errors = []

		if self.process_is_generic:
			errors.append(
				_('The selected process "{0}" is marked as <b>Generic</b>. '
				  "Please ensure the actual (non-generic) process has been selected."
				  ).format(self.process_name)
			)

		if not self.epic:
			errors.append(_(
				"The <b>Epic</b> must be set before marking this log as Active."
			))

		if not self.process_folder_link:
			errors.append(_(
				"The <b>Process Folder Link</b> must be set before marking this log as Active."
			))

		if errors:
			frappe.throw(
				"<br>".join(errors),
				title=_("Cannot Set Status to Active"),
			)

	def validate_process_classification(self):
		"""Block transition from 'Pending Process Classification' when a generic process is selected."""
		if self.is_new():
			return

		old_doc = self.get_doc_before_save()
		if not old_doc or old_doc.status != "Pending Process Classification":
			return

		# Only check when the status is actually changing away from
		# "Pending Process Classification".
		if self.status == old_doc.status:
			return

		is_generic = frappe.db.get_value("Process", self.process_name, "is_generic")
		if is_generic:
			frappe.throw(
				_('The selected process "{0}" is marked as generic. '
				  "Please ensure that the actual process has been created "
				  "and selected before moving out of Pending Process Classification."
				  ).format(self.process_name)
			)

	def validate_single_active_log(self):
		existing = frappe.db.exists(
			"Pathfinder Log",
			{
				"process_name": self.process_name,
				"status": "Active",
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(_("Only 1 active Pathfinder Log is allowed"))

	def before_save(self):
		self.set_initial_time_log()
		self.update_time_log()

	def set_initial_time_log(self):
		if not self.is_new():
			return
		self.time_log = []
		self.add_time_log()

	def update_time_log(self):
		if self.is_new():
			return
		old_doc = self.get_doc_before_save()
		if old_doc and old_doc.status != self.status:
			last_log = None
			if self.time_log:
				last_log = self.time_log[-1]

			# Close the last open row regardless of state label match.
			# Legacy rows may contain old workflow_state values (e.g.
			# "In Development") that won't match the migrated status.
			if last_log and not last_log.end_time:
				last_log.end_time = now_datetime()
				last_log.duration = frappe.utils.time_diff_in_seconds(
					last_log.end_time, last_log.start_time
				)

			if self.status != "Deployed":
				self.add_time_log()

	def add_time_log(self):
		self.append(
			"time_log",
			{
				"state": self.status,
				"start_time": now_datetime()
			}
		)


@frappe.whitelist()
def get_open_change_requests(pathfinder_log: str) -> int:
	"""Fetch open Process Change Requests for the same process and append them.

	Finds all Process Change Request documents that:
	- belong to the same Process as the Pathfinder Log
	- have status "Open"
	- are not already present in the Pathfinder Log's change_requests child table

	Appends matching requests, saves the document, and returns the count added.
	"""
	doc = frappe.get_doc("Pathfinder Log", pathfinder_log)
	doc.check_permission("write")

	# Collect change requests already linked in this Pathfinder Log
	existing_cr_names = {
		row.process_change_request for row in (doc.change_requests or [])
	}

	# Fetch open PCRs for the same process
	open_pcrs = frappe.get_all(
		"Process Change Request",
		filters={
			"process_name": doc.process_name,
			"status": "Open",
		},
		fields=["name", "request_date", "requirement_summary", "hd_ticket"],
		order_by="request_date asc",
	)

	# Filter out those already in the child table
	new_pcrs = [pcr for pcr in open_pcrs if pcr.name not in existing_cr_names]

	if not new_pcrs:
		frappe.msgprint(_("No new change requests found."))
		return 0

	for pcr in new_pcrs:
		doc.append("change_requests", {
			"process_change_request": pcr.name,
			"request_date": pcr.request_date,
			"hd_ticket": pcr.hd_ticket,
			"requirement_summary": pcr.requirement_summary,
		})

	doc.flags.ignore_mandatory = True
	doc.save()

	frappe.msgprint(_("{0} new change requests added.").format(len(new_pcrs)))
	return len(new_pcrs)