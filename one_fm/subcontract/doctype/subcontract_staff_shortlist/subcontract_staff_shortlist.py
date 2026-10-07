# Copyright (c) 2023, ONE FM and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from one_fm.utils import (workflow_approve_reject)


class SubcontractStaffShortlist(Document):
	def on_update(self):
		last_doc = self.get_doc_before_save()
		if self.workflow_state in ["Draft","Rejected",'Approved']:
			if last_doc and last_doc.get('workflow_state') != self.workflow_state:
				if self.workflow_state =='Draft':
					workflow_approve_reject(self,message = f"Your Subcontract Staff Shortlist {self.name} has been returned to Draft Workflow State. Click '<a href='{self.get_url()}'>Here</a>' to view")
				else:
					workflow_approve_reject(self)
