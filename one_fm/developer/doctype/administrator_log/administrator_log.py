# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today
from one_fm.utils import get_approver

class AdministratorLog(Document):
	
	def before_insert(self):
		self.approver = get_approver(self.employee)
		self.approver_name = frappe.db.get_value('Employee', self.approver, 'employee_name')
		if not self.date:self.date=today()

	def after_insert(self):
		# send email to approver

		message=f"""
			Administrator Log has been registered for {self.employee} - {self.employee_name}
			on {self.date}.
		"""
		frappe.sendmail(
			recipients=[frappe.db.get_value('Employee', self.approver, 'user_id')],
			subject=_('Administrator Log by {employee_name}'.format(employee_name=self.employee_name)),
			template = 'default_email',
			args=dict(
					message=message,
					header=_('Administrator Log')
			),
			attachments=[frappe.attach_print(self.doctype, self.name, file_name=self.name)]
		)