# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from one_fm.api.notification import get_employee_user_id, create_notification_log
from frappe import _

class CheckpointAssignmentScan(Document):
	def after_insert(self):
		print("Called")
		if self.has_assignment == "NO" or self.same_assignment == "NO" or self.within_distance == "NO":
			site_supervisor = frappe.get_value("Operations Site", self.site, "account_supervisor")
			supervisor_user = get_employee_user_id(site_supervisor)
			print(supervisor_user)
			create_notification_log(_("Review Checkpoint Scan"), _("Please review Checkpoint Scan and comment."), [supervisor_user], self)
