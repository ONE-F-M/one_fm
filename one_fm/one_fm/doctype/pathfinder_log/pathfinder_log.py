# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class PathfinderLog(Document):
	def validate(self):
		self.validate_single_active_log()

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

			if last_log and last_log.state == old_doc.status and not last_log.end_time:
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