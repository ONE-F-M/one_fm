# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document
from frappe.utils import flt, getdate
import pandas as pd
from one_fm.api.notification import create_notification_log
from frappe import _

class PIFSSMonthlyDeduction(Document):

	def after_insert(self):
		self.update_file_link()
		self.update_additional_file_link()

	def update_file_link(self):
		file_doc = frappe.get_value("File", {"file_url": self.attach_report})
		frappe.set_value("File", file_doc, "attached_to_name", self.name)

	def update_additional_file_link(self):#Additional deduction file
		file_doc = frappe.get_value("File", {"file_url": self.additional_attach_report})
		frappe.set_value("File", file_doc, "attached_to_name", self.name)


	def on_submit(self):
		missing_list = []
		for row in self.deductions:
			if frappe.db.exists("Employee", {"pifss_id_no": row.pifss_id_no}):
				employee = frappe.db.get_value("Employee", {"pifss_id_no": row.pifss_id_no})
				employee_contribution_percentage = flt(frappe.get_value("PIFSS Settings", "PIFSS Settings", "employee_contribution"))
				amount = flt(row.total_subscription * (employee_contribution_percentage / 100), precision=3)
				extra = row.additional_deduction
				create_additional_salary(employee, amount, "Social Security")
				if(extra > 0):
					create_additional_salary(employee, extra,  "Extra Social Security")
			else:
				missing_list.append(row.pifss_id_no)
		
		self.notify_payroll(missing_list)

	def notify_payroll(self, employee_list):
		email = frappe.get_value("HR Settings", "HR Settings", "payroll_notifications_email")
		subject = _("Urgent Attention Needed")
		missing_list =  '<br> '.join(['{}'.format(value) for value in employee_list])
		message = _("Employees linked to the list of PIFSS ID numbers below could not be found. <br> {0}".format(missing_list))
		create_notification_log(subject,message,[email], self)
		
		
def create_additional_salary(employee, amount, component):
	additional_salary = frappe.new_doc("Additional Salary")
	additional_salary.employee = employee
	additional_salary.salary_component = component
	additional_salary.amount = amount
	additional_salary.payroll_date = getdate()
	additional_salary.company = erpnext.get_default_company()
	additional_salary.overwrite_salary_structure_amount = 1
	additional_salary.notes = component+ " Deduction"
	additional_salary.insert()
	additional_salary.submit()
	
@frappe.whitelist()
def import_deduction_data(file_url):
	url = frappe.get_site_path() + file_url
	data = {}
	table_data = []
	df = pd.read_csv(url, encoding='utf-8', skiprows = 3)
	for index, row in df.iterrows():
		employee_amount = flt(row[1] * (47.72/ 100))#employee_amount
		table_data.append({'pifss_id_no': row[12], 'total_subscription': flt(row[1]), 'employee_deduction':employee_amount})
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
			civi_id = row[7]
			table_data.append({'pifss_id_no': employee.pifss_id_no, 'additional_deduction': additional_amount})
	data.update({'table_data': table_data})
	return data