# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe import _

class MGRP(Document):

	def validate(self):
		self.set_resignation_attachment()

	

	def on_update(self):
		self.check_workflow_states()

	def set_resignation_attachment(self):
		attach = frappe.db.get_value('PIFSS Form 103',{'civil_id':self.civil_id},['attach_resignationtermination'])
		self.db_set('end_of_service_attachment',attach)

	def check_workflow_states(self):
		
		if self.workflow_state == "Awaiting Response" and self.flag == 0:#check the previous workflow (DRAFT) required fields 
			message_detail = "<b>First, You Need to Apply on MGRP Website for <a href='{0}'>{1}</a></b>".format(self.mgrp_website,self.first_name)
			frappe.msgprint(message_detail)
			self.db_set('flag',1)

		if self.workflow_state == "Completed":
			field_list = [{'Attach MGRP Approval':'attach_mgrp_approval'}]
			message_detail = "<b>First, You Need to Take Screenshot of Acceptance from MGRP Website <a href='{0}'>{1}</a></b>".format(self.mgrp_website,self.first_name)
			self.set_mendatory_fields(field_list,message_detail)

	def set_mendatory_fields(self,field_list,message_detail=None):
		mandatory_fields = []
		for fields in field_list:
			for field in fields:
				if not self.get(fields[field]):
						mandatory_fields.append(field)

		if len(mandatory_fields) > 0:
			if message_detail:
				message = message_detail
				message += '<br>Mandatory fields required in PIFSS 103 form<br><br><ul>'
			else:
				message= 'Mandatory fields required in PIFSS 103 form<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)

