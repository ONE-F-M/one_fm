# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document
from frappe.utils import flt, getdate, today
import pandas as pd
from one_fm.api.notification import create_notification_log
from frappe import _
from one_fm.api.notification import create_notification_log
from frappe.utils import today, add_days, get_url, date_diff
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta, datetime
import calendar
class PIFSSMonthlyDeduction(Document):
	def validate(self):
		self.set_grd_values()
		#self.notify_grd_to_collect_reports()
		# self.notify_finance_department()
	
	# def on_update(self):
	# 	self.save()
	# 	# self.notify_finance()
		# self.check_payment()
	
	def set_grd_values(self):
	# if not self.grd_supervisor:
	# 	self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
		if not self.grd_operator:
			self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")

	# if date_diff(first_day,today()) == 7:
	# 	if datetime.today().weekday() == 4 or datetime.today().weekday() == 5:
	# print(datetime.today().weekday())
#mon 0, Tue 1, wen 2, Thur 3, Fri 4, Sat 5, Sun 6
	# print(date_diff(first_day,today))


	def notify_finance_department(self):#finance@one-fm.com
		if self.notify_finance == 1:
			self.notify_finance = "amnaalshawa96@gmail.com"
			page_link = get_url("/desk#Form/PIFSS Monthly Deduction/" + self.name)
			message = "<p>Please Prepare Total Payment Amount for PIFSS<a href='{0}'>{1}</a>.</p>".format(page_link, self.name)
			subject = 'Please Prepare Total Payment Amount for PIFSS for'.format(self.name)
			#send_email(self, [self.notify_finance], message, subject)
			create_notification_log(subject, message, [self.notify_finance], self)

	def check_payment(self):
		if self.payment_done == 1:
			page_link = get_url("/desk#Form/PIFSS Monthly Deduction/" + self.name)
			message = "<p>Payment Is Done for {0} By {1}<a href='{2}'></a>.</p>".format(self.name,self.notify_finance,page_link)
			subject = 'Finance Closed the Total payment Amount'.format(self.notify_finance)
			#send_email(self, [self.notify_finance], message, subject)
			create_notification_log(subject, message, [self.grd_operator], self)

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

def send_email(doc, recipients, message, subject):
	frappe.sendmail(
		recipients= recipients,
		subject=subject,
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)
def notify_grd_to_collect_reports():#will be called everyday
	today = date.today()
	first_day = today.replace(day=1) + relativedelta(months=1)
	seven_days_before = first_day - timedelta(days=21)
	# print(date_diff(first_day,today))
	if calendar.day_name[seven_days_before.weekday()] == "Friday": 
		day_to_notify_first = seven_days_before - timedelta(days=1)#notify on thursday
		send_notification_before_one_week(first_day,day_to_notify_first)
	if calendar.day_name[seven_days_before.weekday()] == "Saturday":
		day_to_notify_first = seven_days_before - timedelta(days=2)#notify on thursday
		send_notification_before_one_week(first_day,day_to_notify_first)
	elif calendar.day_name[seven_days_before.weekday()] == "Sunday" or calendar.day_name[seven_days_before.weekday()] == "Monday" or calendar.day_name[seven_days_before.weekday()] == "Tuesday" or calendar.day_name[seven_days_before.weekday()] == "Wednesday" or calendar.day_name[seven_days_before.weekday()] == "Thursday":
		print("send noti1")
		day_to_notify_first = today
		send_notification_before_one_week(first_day,day_to_notify_first)
		print("send noti2")
	else:
		frappe.msgprint("Do nothing")
	
	
def send_notification_before_one_week(first_day,day_to_notify_first):
	doc = frappe.new_doc('PIFSS Monthly Deduction')
	doc.deduction_month = first_day
	doc.save()
	pifss_record = frappe.db.get_list('PIFSS Monthly Deduction',{'docstatus': 0,'reminder_before_one_week':0},['grd_operator','deduction_month'])
	# pifss_record = frappe.get_doc('PIFSS Monthly Deduction',doc)
	print(pifss_record)
	for pifss in pifss_record:
		if pifss.deduction_month == first_day:
			print("Hi")
	# if pifss_record.reminder_before_one_week == 0:
		message = "<p>Reminder: Collect PIFSS report at the begining of the next month.</p>"
		subject = 'Reminder: Collect PIFSS report at the begining of the next month'
		# email = frappe.get_value("HR Settings", "HR Settings", "payroll_notifications_email")
		#send_email(pifss, [pifss.grd_operator], message, subject)
		create_notification_log(subject, message, [pifss.grd_operator], pifss)

@frappe.whitelist()
def import_deduction_data(file_url):
	url = frappe.get_site_path() + file_url
	data = {}
	table_data = []
	df = pd.read_csv(url, encoding='utf-8', skiprows = 3)
	for index, row in df.iterrows():
		if frappe.db.exists("Employee", {"pifss_id_no": row[12]}):
			employee = frappe.get_doc('Employee', {'pifss_id_no':row[12]})
			civil_id = employee.one_fm_civil_id
		else:
			civil_id = None
		employee_amount = flt(row[1] * (47.7272/ 100))#employee_amount
		employee_amount = (employee_amount * 1000 )/1000
		#employee_amount = flt(row[1] * (52.2727/ 100))

		table_data.append({'pifss_id_no': row[12], 'total_subscription': flt(row[1]), 'employee_deduction':employee_amount,'civil_id':civil_id})
	data.update({'table_data': table_data})
	# print(employeer_amount)
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
			# civi_id = row[7]
			table_data.append({'pifss_id_no': employee.pifss_id_no, 'additional_deduction': additional_amount})
	data.update({'table_data': table_data})
	return data

@frappe.whitelist()
def highlight_employee_registered_during_last_month():
	today = date.today()
	data = {}	
	table_data = []
	regestered_employee = frappe.db.get_list('PIFSS Form 103',{'status':'Accepted','request_type':'Registration'},['date_of_registeration','civil_id'])
	print(regestered_employee)
	if regestered_employee:
		for employee in regestered_employee:
			if today.month - employee.date_of_registeration.month == 1 and today.year == employee.date_of_registeration.year:
				table_data.append({'pifss_id_no':employee.pifss_id_no,'civil_id':employee.one_fm_civil_id})
		data.update({'table_data': table_data})
	# print(data)
	return data
			# print(today.month - employee.date_of_registeration.month)# == 9
			# print(employee.date_of_registeration)
			# print(employee.date_of_registeration.month,employee.date_of_registeration.year)
			# print(today.month,today.year) 
			
def create_notification_log(subject, message, for_users, reference_doc):
    for user in for_users:
        doc = frappe.new_doc('Notification Log')
        doc.subject = subject
        doc.email_content = message
        doc.for_user = user
        doc.document_type = reference_doc.doctype
        doc.document_name = reference_doc.name
        doc.from_user = reference_doc.modified_by