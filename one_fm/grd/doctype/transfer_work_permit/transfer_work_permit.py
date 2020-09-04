# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today

class TransferWorkPermit(Document):
	def validate(self):
		if not self.grd_supervisor:
			self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")

	def on_submit(self):
		self.validate_mandatory_fields_on_submit()
		self.db_set('work_permit_submitted', 'Yes')
		self.db_set('work_permit_submitted_by', frappe.session.user)
		self.db_set('work_permit_submitted_on', today())

	def on_update_after_submit(self):
		if self.work_permit_approved == 'Yes' and self.work_permit_status == 'Draft':
			self.db_set('work_permit_status', 'Submitted')
			self.db_set('work_permit_approved_by', frappe.session.user)
			self.db_set('work_permit_approved_on', today())

	def get_required_documents(self):
		from one_fm.grd.doctype.work_permit.work_permit import set_required_documents
		return set_required_documents(self)

	def validate_mandatory_fields_on_submit(self):
		field_list = [{"Company Trade Name in Arabic":"company_trade_name_arabic"}, {"Contract File Number":"contract_file_number"},
			{"Authorized Signatory Name in Arabic":"authorized_signatory_name_arabic"}, {"PAM File Number":"pam_file_number"},
			{"Issuer Number":"issuer_number"}, {"First Name":"first_name"}, {"First Name in Arabic":"first_name_in_arabic"},
			{"Last Name":"last_name"}, {"Last Name in Arabic":"last_name_in_arabic"}, {'Date of Birth':'date_of_birth'},
			{'Gender':'gender'}, {'Religion':'religion'}, {'Marital Status':'marital_status'}, {'Nationality':'nationality'},
			{'Passport Type':'passport_type'}, {'Passport Number':'passport_number'}, {'Pratical Qualification':'pratical_qualification'}, {'Religion':'religion'},
			{'CIVIL ID':'civil_id'}, {'PAM Designation':'pam_designation'}, {'Salary':'salary'}, {'Salary Type':'religion'},
			{'Duration of Work Permit':'duration_of_work_permit'}, {'Visa Reference Number':'visa_reference_number'},
			{'Date of Issuance of Visa':'date_of_issuance_of_visa'}, {'Date of Entry in Kuwait':'date_of_entry_in_kuwait'},
			{'Documents Required':'documents_required'}]

		if self.second_name and not self.second_name_in_arabic:
			field_list.extend({'Second Name in Arabic': 'second_name_in_arabic'})
		if self.third_name and not self.third_name_in_arabic:
			field_list.extend({'Third Name in Arabic': 'third_name_in_arabic'})

		mandatory_fields = []
		for fields in field_list:
			for field in fields:
				if not self.get(fields[field]):
					mandatory_fields.append(field)

		if len(mandatory_fields) > 0:
			message = 'Mandatory fields required in Transfer Work Permit to Submit<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)
