# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document
from frappe.utils import flt, getdate
import pandas as pd
import math
from datetime import date
from dateutil.relativedelta import relativedelta
from frappe.utils import today, add_days, get_url
from frappe.utils.user import get_users_with_role
from frappe.permissions import has_permission
from one_fm.api.notification import create_notification_log
from frappe import _

class PIFSSMonthlyDeduction(Document):
		

	def after_insert(self):
		if self.attach_report or self.additional_attach_report:
			self.update_file_link()
			self.update_additional_file_link()

	def update_file_link(self):
		file_doc = frappe.get_value("File", {"file_url": self.attach_report})
		frappe.set_value("File", file_doc, "attached_to_name", self.name)

	def update_additional_file_link(self):#Additional deduction file
		file_doc = frappe.get_value("File", {"file_url": self.additional_attach_report})
		frappe.set_value("File", file_doc, "attached_to_name", self.name)


	def on_submit(self):
		self.mendatory_fields()
		if not self.attach_report and not self.additional_attach_report and not self.attach_manual_report and not self.attach_pdf_report:
			frappe.throw("The following attaches are compulsory to submit.<br><ol><li>Attach Monthly Deduction Report</li><li>Attach Additional Monthly Deduction Report</li><li>Attach PDF Report</li><li>Attach Manual Report</li>")
		
		self.notify_finance()
		self.create_legal_investigation()
		missing_list = []
		for row in self.deductions:
			if frappe.db.exists("Employee", {"pifss_id_no": row.pifss_id_no}):
				employee = frappe.db.get_value("Employee", {"pifss_id_no": row.pifss_id_no})
				employee_contribution_percentage = flt(frappe.get_value("PIFSS Settings", "PIFSS Settings", "employee_contribution"))
				amount = flt(row.total_subscription * (employee_contribution_percentage / 100), precision=3)
				create_additional_salary(employee, amount)
			else:
				missing_list.append(row.pifss_id_no)
		
		self.notify_payroll(missing_list)

	def notify_payroll(self, employee_list):
		email = frappe.get_value("HR Settings", "HR Settings", "payroll_notifications_email")
		subject = _("Urgent Attention Needed")
		missing_list =  '<br> '.join(['{}'.format(value) for value in employee_list])
		message = _("Employees linked to the list of PIFSS ID numbers below could not be found. <br> {0}".format(missing_list))
		create_notification_log(subject,message,[email], self)

	def mendatory_fields(self):
		field_list = [{'Attach Monthly Deduction Report':'attach_report'},{'Attach Manual Report':'attach_manual_report'},{'Attach Additional Monthly Deduction Report':'additional_attach_report'},
		{'Attach PDF Report':'attach_pdf_report'},{'Basic Extra Amounts':'basic_extra_amounts'},{'Additional Supplementary Amounts':'additional_supplementary_amounts'},{'Additional Amounts Increase':'additional_amounts_increase'},{'Additional Unemployment Supplement':'additional_unemployment_supplement'},{'Additional amounts of end of service gratuity':'additional_amounts_of_end_of_service_gratuity'},{'Supplementary insurance before 12/97':'supplementary_insurance_before_1297'},{'Special Installments and Exchange':'special_installments_and_exchange'},{'Additional amounts Special Installments and Replacement':'additional_amounts_special_installments_and_replacement'},
		{'Total':'total'},{'Optional Supplemental Insurance':'optional_supplemental_insurance'},{'Optional Supplementary Additional Amounts':'optional_supplementary_additional_amounts'}]
		mandatory_fields = []
		for fields in field_list:
			for field in fields:
				if not self.get(fields[field]):
						mandatory_fields.append(field)

		if len(mandatory_fields) > 0:
			message = 'Mandatory fields required in PIFSS 103 form<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)

	def notify_finance(self):
		finance_email = []
		users = get_users_with_role("Finance User")
		if len(users)>0:
			for user in users:
				finance_email.append(user)
		if finance_email and len(finance_email) > 0: 		
			email = finance_email
			subject = _("PIFSS Monthly Deduction Payments")
			message = _("Kindly, prepare total payment amount and transfer it to GRD account.<br>Please transfer it within 2 days.")
			create_notification_log(subject,message,email,self)

	def create_legal_investigation(self):
		"""
		This method will be sending the sum of additional amounts as penality amount.
		Define to whom the peality will be asgined to.
		create legal investigation.
		"""
		if self.basic_extra_amounts and self.additional_supplementary_amounts and self.additional_amounts_increase and self.additional_unemployment_supplement \
		 and self.additional_amounts_of_end_of_service_gratuity and self.supplementary_insurance_before_1297 and self.special_installments_and_exchange and self.additional_amounts_special_installments_and_replacement:
		 penality_amount = self.basic_extra_amounts+self.additional_supplementary_amounts+self.additional_amounts_increase+self.additional_unemployment_supplement+self.additional_amounts_of_end_of_service_gratuity+self.special_installments_and_exchange+self.additional_amounts_special_installments_and_replacement+self.supplementary_insurance_before_1297
		 print(penality_amount)

def create_additional_salary(employee, amount):
	additional_salary = frappe.new_doc("Additional Salary")
	additional_salary.employee = employee
	additional_salary.salary_component = "Social Security"
	additional_salary.amount = amount
	additional_salary.payroll_date = getdate()
	additional_salary.company = erpnext.get_default_company()
	additional_salary.overwrite_salary_structure_amount = 1
	additional_salary.notes = "Social Security Deduction"
	additional_salary.insert()
	additional_salary.submit()
	
def auto_create_pifss_monthly_deduction_record():# call this method at 8 am of first day of each month
	create_pifss_mothly_dedution_record()	

def create_pifss_mothly_dedution_record():
	today = date.today()
	first_day_in_month = today.replace(day=1) + relativedelta(months=1)
	pifss_mothly_dedution = frappe.new_doc("PIFSS Monthly Deduction")
	pifss_mothly_dedution.deduction_month = first_day_in_month
	pifss_mothly_dedution.save()
	notify_pro(pifss_mothly_dedution)
	
def notify_pro(pifss_mothly_dedution):
	doc = frappe.get_doc("PIFSS Monthly Deduction",pifss_mothly_dedution.name)
	if doc:
		email = frappe.db.get_single_value("GRD Settings", "default_grd_operator_pifss")
		subject = _("PIFSS Monthly Deduction record is created")
		message = _("PIFSS Monthly Deduction record is created. <br>Kindly proceed with it.")
		create_notification_log(subject,message,[email], doc)


@frappe.whitelist()
def import_deduction_data(file_url):
	url = frappe.get_site_path() + file_url
	data = {}
	table_data = []
	civil_id = ""
	df = pd.read_csv(url, encoding='utf-8', skiprows = 3)
	for index, row in df.iterrows():
		if frappe.db.exists("Employee", {"pifss_id_no": row[12]}):
			employee = frappe.get_doc('Employee', {'pifss_id_no':row[12]})
			civil_id = employee.one_fm_civil_id
			print(row[7],row[8],row[9],row[10],row[11],row[12],row[13])
		employee_amount = flt(row[1] * (47.72/ 100))
		table_data.append({'pifss_id_no': row[12],'civil_id':civil_id,'total_subscription': flt(row[1]), 'compensation':row[2], 'unemployment_insurance_amount':row[3],'fund_increase_amount':row[4],'supplementary_insurance_amount':row[5],'basic_insurance_amount':row[6],'employee_deduction':employee_amount})
	data.update({'table_data': table_data})
	return data


@frappe.whitelist()
def import_additional_deduction_data(file_url):
	url = frappe.get_site_path() + file_url
	data = {}	
	table_data = []
	df = pd.read_csv(url, encoding='utf-8')
	for index, row in df.iterrows():
		if frappe.db.exists("Employee", {"one_fm_civil_id": row[7]}):
			employee = frappe.get_doc('Employee', {'one_fm_civil_id':row[7]})
			additional_amount = flt(row[1], precision=3)#employee_amount
			table_data.append({'pifss_id_no': employee.pifss_id_no, 'additional_deduction': additional_amount})
	data.update({'table_data': table_data})
	return data
