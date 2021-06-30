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
		print("===> ",self.attach_report)
		if not self.attach_report and not self.additional_attach_report and not self.attach_manual_report and not self.attach_pdf_report:
			frappe.throw("The following attaches are compulsory to submit.<br><ol><li>Attach Monthly Deduction Report</li><li>Attach Additional Monthly Deduction Report</li><li>Attach PDF Report</li><li>Attach Manual Report</li>")
		self.notify_finance()
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
	
	def notify_finance(self):
		email = finance@one-fm.com
		subject = _("PIFSS Monthly Deduction Payments")
		message = _("Kindly, prepare total payment amount: {0} and transfer it to GRD account.<br>Please transfer it within 2 days.").format(round(self.total_payments,3))
		create_notification_log(subject,message,[email],self)

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
		employee_amount = flt(row[1] * (47.72/ 100))
		table_data.append({'pifss_id_no': row[12],'civil_id':civil_id,'total_subscription': flt(row[1]), 'employee_deduction':employee_amount})
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
