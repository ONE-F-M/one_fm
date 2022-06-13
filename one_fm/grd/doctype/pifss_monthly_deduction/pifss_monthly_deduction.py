# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document
from frappe.utils import flt, getdate,cint, cstr
import pandas as pd
import math
from datetime import date
from dateutil.relativedelta import relativedelta
from frappe.utils import today, add_days, get_url
from frappe.utils.user import get_users_with_role
from frappe.permissions import has_permission
from one_fm.api.notification import create_notification_log
from one_fm.grd.doctype.pifss_monthly_deduction_tool import pifss_monthly_deduction_tool
from frappe import _

class PIFSSMonthlyDeduction(Document):

	def after_insert(self):
		if self.attach_report and self.additional_attach_report:
			self.update_file_link()
			self.update_additional_file_link()

	def update_file_link(self):
		"""This function set `PIFSS Monthly Deduction` name into the file records of csv file `attach_report`"""
		file_doc = frappe.get_value("File", {"file_url": self.attach_report})
		frappe.set_value("File", file_doc, "attached_to_name", self.name)

	def update_additional_file_link(self):
		"""This function set `PIFSS Monthly Deduction` name into the file records of additional csv file `additional_attach_report`"""
		file_doc = frappe.get_value("File", {"file_url": self.additional_attach_report})
		frappe.set_value("File", file_doc, "attached_to_name", self.name)

	def on_update(self):
		self.check_attachment_status()
		self.check_workflow_states()
		self.set_total_values()

	def set_total_values(self):
		"""This method adding all columns in the deductions table and setting total value per column in the its total amount field"""
		total_contribution=0.0
		company_contribution=0.0
		employee_contribution=0.0

		for i in self.deductions:
			total_contribution += i.total_contribution
			company_contribution += i.company_contribution
			employee_contribution += i.employee_contribution

		self.total_contribution = total_contribution
		self.company_contribution = company_contribution
		self.employee_contribution = employee_contribution



	def check_workflow_states(self):
		"""
		This function throw the mandatory fields `set_mandatory_fields` upon each `workflow_state`
		"""
		if self.workflow_state == "Pending By Supervisor":# Check the previous workflow (DRAFT) required fields
			field_list = [
							{'Attach Monthly Deduction Report':'attach_report'},
							# {'Attach Manual Report':'attach_manual_report'},
							# {'Attach Employee Additional Monthly Report':'additional_attach_report'},
							# {'Attach PDF Report':'attach_pdf_report'},
							# {'Basic Insurance':'basic_insurance'},{'Supplementary Insurance':'supplementary_insurance'},
							# {'Fund Increase':'fund_increase'},{'Unemployment Insurance':'unemployment_insurance'},
							# {'Compensation':'compensation'},{'Total Amount':'total'}
							]

			message_detail = '<b style="color:red; text-align:center;">First, Scan the Manual Report and Download csv files from <a href="{0}" target="_blank">PIFSS Website</a></b>'.format(self.pifss_website)
			self.set_mandatory_fields(field_list,message_detail)
			self.set_total_payment_required_for_finance()
			self.notify_grd_supervisor()# Notify supervisor to check the document before sending it finance.

		if self.workflow_state == "Pending By Finance":
			pass
			# field_list = [{'Total Payment Required':'total_payment_required'}]
			# self.set_mandatory_fields(field_list)
			# create_payment_request(self.total_payment_required,self.name, self.attach_manual_report)
			# self.notify_finance()# Notify finance with the created payment request.

		if self.workflow_state == "Completed":
			field_list = [{'Attach Invoice':'attach_invoice'}]
			message_detail = '<b style="color:red; text-align:center;">First, Scan the Receipt</b>'
			# self.set_mandatory_fields(field_list,message_detail)

	def set_mandatory_fields(self,field_list,message_detail=None):
		mandatory_fields = []
		for fields in field_list:
			for field in fields:
				if not self.get(fields[field]):
						mandatory_fields.append(field)

		if len(mandatory_fields) > 0:
			if message_detail:
				message = message_detail
				message += '<br>Mandatory fields required in PIFSS Monthly Deduction <br><br><ul>'
			else:
				message= 'Mandatory fields required in PIFSS PIFSS Monthly Deduction<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)

	def set_total_payment_required_for_finance(self):
		if self.total:
			self.db_set('total_payment_required',self.total)

	def check_attachment_status(self):
		"""
		This function runs `on_update` and it deletes the data stored in child table `deductions` once attachments got deleted,
		so it clears all child table and fields that are filled according to the attachments.
		"""
		if not self.attach_report or not self.attach_report:
			# Delete child table values from frontend and db
			frappe.db.sql("""delete from `tabPIFSS Monthly Deduction Employees`
            where parent = %s""", self.name)
			self.set("deductions", [])
			# Delete values from frontend and db
			frappe.db.sql("""update `tabPIFSS Monthly Deduction`
			set total_sub=0 and total_additional_deduction=0 and basic_insurance_in_csv=0 and supplementary_insurance_in_csv=0 and fund_increase_in_csv=0 and unemployment_insurance_in_csv=0 and compensation_in_csv=0
            where name = %s""", self.name)
			fields = ['total_sub','total_additional_deduction','basic_insurance_in_csv','supplementary_insurance_in_csv','fund_increase_in_csv','unemployment_insurance_in_csv','compensation_in_csv']
			for field in fields:
				self.set(field,0)

	def notify_grd_supervisor(self):
		if self.workflow_state == "Pending By Supervisor":
			email = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
			subject = _("Attention: PIFSS Monthly Deduction Is Ready to Be Reviewed")
			message = "<p>You are requested to review PIFSS Monthly Deduction</p><br>"
			create_notification_log(subject, message, [email], self)

	def notify_finance(self):
		if self.workflow_state == "Pending By Finance":
			finance_email = []
			users = get_users_with_role("Finance User")
			if len(users)>0:
				for user in users:
					finance_email.append(user)
			if finance_email and len(finance_email) > 0:
				email = finance_email
				subject = _("PIFSS Monthly Deduction Payments for {0}").format(self.name)
				message = _("Kindly, prepare Total Payment Required Amount and transfer it to GRD account.<br>Please transfer it within 2 days.")
				payment_request = frappe.get_doc('Payment Request',{'reference_name':self.name},self.name)
				if not frappe.db.exists("Notification Log",{'subject':subject}):# This will restrict notification to be send once
					create_notification_log(subject,message,email,payment_request)


	def on_submit(self):
		self.create_additional_salary()
		frappe.msgprint("Addtional Salaries has been creeated.")

	def create_additional_salary(self):
		for row in self.deductions:
			try:
				if not frappe.db.exists("Additional Salary", {'pifss_monthly_deduction':row.parent, 'employee':row.employee}):
					additional_salary = frappe.new_doc("Additional Salary")
					additional_salary.employee = row.employee
					additional_salary.salary_component = "Social Security"
					additional_salary.amount = row.employee_contribution
					additional_salary.payroll_date = self.deduction_month
					additional_salary.company = erpnext.get_default_company()
					additional_salary.overwrite_salary_structure_amount = 1
					additional_salary.notes = "Social Security Deduction"
					additional_salary.pifss_monthly_deduction = row.parent
					additional_salary.insert()
					additional_salary.submit()
				else:
					frappe.throw(f" Something is not right on <b class='text-danger'>row {row.idx}, {row.employee_name}</b>. Please check Employee records or Additional Salary Slip.")
			except Exception as e:
				frappe.throw(f"{str(e)} <b class='text-danger'>row {row.idx}, {row.employee_name}</b>")


	def before_cancel(self):
		self.cancel_additional_salary()

	def cancel_additional_salary(self):
		additional_salaries = frappe.db.get_list("Additional Salary", {'pifss_monthly_deduction':self.name})
		for row in addtional_salaries:
			print('cancelling', row.employee, row.name, row.amount)
			additional_salary = frappe.get_doc("Additional Salary", row.name)
			if(additional_salary.docstatus==1):
				additional_salary.cancel()

	def notify_payroll(self, employee_list):
		email = frappe.get_value("HR Settings", "HR Settings", "payroll_notifications_email")
		subject = _("Urgent Attention Needed")
		missing_list =  '<br> '.join(['{}'.format(value) for value in employee_list])
		message = _("Employees linked to the list of PIFSS ID numbers below could not be found. <br> {0}".format(missing_list))
		create_notification_log(subject,message,[email], self)

	def create_legal_investigation(self):
		"""
		This method sends the sum of all additional amounts fields as penalty amount and create legal investigation record.
		"""

		penalty_amount = self.basic_extra_amounts+self.additional_supplementary_amounts+self.additional_amounts_increase+self.additional_unemployment_supplement+self.additional_amounts_of_end_of_service_gratuity+self.special_installments_and_exchange+self.additional_amounts_special_installments_and_replacement+self.supplementary_insurance_before_1297
		if penalty_amount > 0.0:
			legal_record = frappe.new_doc('Legal Investigation')
			legal_record.reference_doctype = "PIFSS Monthly Deduction"
			legal_record.reference_docname = self.name
			legal_record.start_date = today()
			legal_record.investigation_subject = "Investigate the cause of the {0} KWD Additional Amount In PIFSS".format(penalty_amount)
			legal_record.insert()
			legal_record.save()


def create_payment_request(total_payment_required, name, report):
	"""
	This function creates Payment request to finance with the total payment amount for this month.

	Param:
	------

	total_payment_required: total payment amunt
	name: Object name
	report: manual attachments that has the payment amount as reference for finance
	"""
	if not frappe.db.exists("Payment Request", {"reference_doctype":"PIFSS Monthly Deduction","reference_name": name}):
		subject = _("PIFSS Monthly Deduction Payments")
		message = "Hello,\n Requesting payment against PIFSS Monthly Deduction {0}\n\n If you have any questions, please get back to GRD.\n\n Please transfer the Amount within 2 days.".format(name)
		payment_request = frappe.new_doc('Payment Request')
		payment_request.payment_request_type = "Outward"
		payment_request.reference_doctype = "PIFSS Monthly Deduction"
		payment_request.reference_name = name
		payment_request.party_type = "Customer"
		payment_request.party = "Public Institution for Social Security"
		payment_request.grand_total = total_payment_required
		payment_request.email_to = "finance@one-fm.com"
		payment_request.message = message
		payment_request.one_fm_manual_report = report
		payment_request.subject = subject
		payment_request.payment_channel = "Email"
		payment_request.mode_of_payment = "Cheque"
		payment_request.status = "Requested"
		payment_request.insert()

# This method set in a cron at 8 am on the first day of each month
def auto_create_pifss_monthly_deduction_record():
	create_pifss_mothly_dedution_record()

# Create a record in `PIFSS Monthly Deduction` and set `dedution_month` (required for the autonaming of the record) and notifiy PRO
def create_pifss_mothly_dedution_record():
	today = date.today()
	first_day_in_month = today.replace(day=1) + relativedelta(months=0)
	pifss_mothly_dedution = frappe.new_doc("PIFSS Monthly Deduction")
	pifss_mothly_dedution.deduction_month = first_day_in_month
	pifss_mothly_dedution.save()
	notify_pro(pifss_mothly_dedution)

def notify_pro(pifss_mothly_dedution):
	doc = frappe.get_doc("PIFSS Monthly Deduction",pifss_mothly_dedution.name)
	if doc:
		page_link = get_url(doc.get_url())
		email = frappe.db.get_single_value("GRD Settings", "default_grd_operator_pifss")
		subject = _("PIFSS Monthly Deduction record is created")
		message = _("PIFSS Monthly Deduction record is created: {0}").format(page_link)
		create_notification_log(subject,message,[email], doc)

@frappe.whitelist()
def import_deduction_data(doc_name):
	"""

	- This function read the attched csv file (contain all kuwaiti employee registered in social security) and store its content in a dictionary list `table_data` (eg: [{'pifss_id_no': row[12],'civil_id':civil_id,'total_subscription': flt(row[1]), 'compensation_amount':row[2], 'unemployment_insurance':row[3],'fund_increase':row[4],'supplementary_insurance':row[5],'basic_insurance':row[6],'employee_deduction':employee_amount,'additional_deduction':0}] ),
	- Then, fetch the second csv file (conyain only kuwaiti employee who has additional payment amount in social security) for additional deduction records and store its content in a dictionary list `additional_table` (eg: [{'civil_id': cstr(row[7]), 'additional_deduction': additional_amount}])

	In the first list: `table_data` there is `additional_deduction` which has a default value (zero) for all employee.
	In the second list: `additional_table` has the actual additional value for the employee.

	- After that, looping in the first list `table_data` and set the actual additional value for employees who are listed in the second list `additional_table`
	- Finally, return the updated list `table_data` and its length to be set in the child table `deductions`

	Param:
	-------

	doc_name: PIFSS Monthly Deduction name (eg: 2021-12-01) naming series is first date of each month

	Return:
	--------

	table_data: dictionary list combines two csv attached files
	number: length of `table_data`

	"""
	doc = frappe.get_doc('PIFSS Monthly Deduction',doc_name)
	file_url_1 = doc.attach_report

	# Read the attched csv file and store its content in a dictionary list `table_data`
	if file_url_1:
		url_1 = frappe.get_site_path() + file_url_1
		table_data = []
		civil_id = ""
		employee = ""
		pifss_id_no = ""
		df_1 = pd.read_csv(url_1, encoding='utf-8', skiprows = 0)
		for index, row in df_1.iterrows():
			# print(row[0])
			if frappe.db.exists("Employee", {"one_fm_civil_id": row[0]}):
				employee_detail = frappe.db.get_value('Employee',{'one_fm_civil_id':row[0]},['pifss_id_no', 'one_fm_civil_id', 'name'])
				pifss_id_no = employee_detail[0]
				civil_id = employee_detail[1]
				employee_pk = employee_detail[2]
				table_data.append({
				'employee': employee_pk, 'pifss_id_no': pifss_id_no, 'civil_id':civil_id, 'employee_name_in_arabic': row[1],
				'actual_salary': flt(row[2]), 'social_security_salary':flt(row[3]), 'employee_contribution':flt(row[4]),
				'company_contribution':flt(row[5]),'total_contribution':flt(row[6]),
				})

			else:
				civil_id = ' '
				table_data.append({
				'employee': '', 'pifss_id_no': '', 'civil_id':row[0], 'employee_name_in_arabic': row[1],
				'actual_salary': flt(row[2]), 'social_security_salary':flt(row[3]), 'employee_contribution':flt(row[4]),
				'company_contribution':flt(row[5]),'total_contribution':flt(row[6]),
				})
			# employee_amount = flt(row[1] * (47.730/ 100))
	#
	# Fetch the second csv file for additional deduction records and store its content in a dictionary list `additional_table`
	# additional_table = {}
	# if doc.additional_attach_report:
	# 	file_url_2 = doc.additional_attach_report
	# 	url_2 = frappe.get_site_path() + file_url_2
	# 	df_2 = pd.read_csv(url_2, encoding='utf-8')
	# 	for index, row in df_2.iterrows():
	# 		if frappe.db.exists("Employee", {"one_fm_civil_id": row[7]}):
	# 			additional_amount = flt(row[1], precision=3)
	# 			additional_table[cstr(row[7])] = {'civil_id': cstr(row[7]),'additional_deduction': additional_amount}
	#
	# # Looping in the first list `table_data` and set the actual additional value for employees who are listed in the second list `additional_table`
	# list_additional_values = [value for elem in additional_table for value in elem.values()]# Convert `additional_table` dictionary list into list of [civil_id, additional_value] (eg: list_additional_values=['288020300233', 30.0] )
	# for employee in table_data:
	# 	if additional_table.get(employee['civil_id']):
	# 		employee.update({
	# 			'additional_deduction':additional_table.get(employee['civil_id'])
	# 		})

	return table_data,len(table_data)
