# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url_to_form


class RamboAssignment(Document):
	def after_insert(self):
		self.send_shift_supervisor_notification()

	def send_shift_supervisor_notification(self):
		"""Send email notification to the Shift Supervisor when a Rambo Assignment is created."""
		if not self.shift_supervisor_user:
			return

		context = {
			"date": self.date,
			"original_employee": self.original_employee or "",
			"original_employee_name": self.original_employee_name or "",
			"employee": self.employee or "",
			"employee_name": self.employee_name or "",
			"operations_site": self.operations_site or "",
			"operations_shift": self.operations_shift or "",
			"operations_role": self.operations_role or "",
			"project": self.project or "",
			"start_time": self.start_time or "",
			"end_time": self.end_time or "",
			"transportation_manifest": self.transportation_manifest or "",
			"manifest_url": get_url_to_form(
				"Transportation Manifest", self.transportation_manifest
			),
		}

		message = frappe.render_template(
			"one_fm/templates/emails/rambo_assignment_notification.html",
			context
		)

		subject = _("Rambo Assignment Alert: Reliever Assigned for Manifest {0}").format(
			self.transportation_manifest
		)

		try:
			from one_fm.processor import sendemail
			sendemail(
				recipients=[self.shift_supervisor_user],
				subject=subject,
				header=[_("Rambo Assignment Alert: {0}").format(self.name)],
				message=message,
			)
		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title=_("Rambo Assignment Email Error for {0}").format(self.name)
			)
