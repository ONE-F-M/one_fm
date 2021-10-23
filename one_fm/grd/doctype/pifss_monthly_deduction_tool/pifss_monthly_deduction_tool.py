# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe, erpnext
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from frappe.utils import get_url, getdate, cint,cstr,  flt, date_diff
from frappe.core.doctype.communication.email import make
from frappe import _
import pandas as pd

from one_fm.api.notification import create_notification_log
class PIFSSMonthlyDeductionTool(Document):

	def on_submit(self):
		self.check_flag_for_additional_salary()

	def validate(self):
		self.set_grd_user()

	def set_grd_user(self):
		self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_pifss")

	def on_update(self):
		self.compare_employee_in_months()
		self.check_workflow_status()
	
	def compare_employee_in_months(self):
		"""This method is comparing the pifss monthly deduction of the current and the last months;
		 new kuwaiti employees, left employees and who got changes in their total subscription"""
		if self.old_pifss_monthly_deduction and self.new_pifss_monthly_deduction and not self.pifss_tracking_changes:
			doc_old = frappe.get_doc('PIFSS Monthly Deduction',self.old_pifss_monthly_deduction)#old monthly deduction doctype
			doc_new = frappe.get_doc('PIFSS Monthly Deduction',self.new_pifss_monthly_deduction)#new monthly deduction doctype
			list_of_old=frappe.db.get_list('PIFSS Monthly Deduction Employees',{'parent':doc_old.name},['pifss_id_no','total_subscription'])#deductions table in the old monthly deduction doctype
			list_of_new=frappe.db.get_list('PIFSS Monthly Deduction Employees',{'parent':doc_new.name},['pifss_id_no','total_subscription'])#deductions table in the new monthly deduction doctype
			# Create a list of all values in list of dictionaries
			list_of_old_values = [value for elem in list_of_old for value in elem.values()]
			list_of_new_values = [value for elem in list_of_new for value in elem.values()]
			list_of_changed_values=[]
			table=[]
			for employee_new in doc_new.deductions:# fetching new employee that aren't appearing in the old monthly deduction
				if employee_new.pifss_id_no not in list_of_old_values:
					table.append({
						'employee':frappe.get_value('Employee',{'pifss_id_no':employee_new.pifss_id_no},['name']),
						'pifss_no':employee_new.pifss_id_no,
						'old_value':None,
						'new_value':employee_new.total_subscription,
						'status':"New",
						'delta_amount':None
					})
					print(f"No, Value: '{employee_new.pifss_id_no}' is new")
				elif employee_new.pifss_id_no in list_of_old_values:# fetching employee who got changes in their monthly deduction
					for value in list_of_old:
						if employee_new.pifss_id_no == value.pifss_id_no and employee_new.total_subscription != value.total_subscription:
							if employee_new.pifss_id_no not in list_of_changed_values:
								list_of_changed_values.append(employee_new.pifss_id_no)
								status = sub_total_subscription(employee_new.total_subscription,value.total_subscription)#will return list of status and delta amount like: status = ['Increased',90]
								if status:
									table.append({
									'employee':frappe.get_value('Employee',{'pifss_id_no':employee_new.pifss_id_no},['name']),
									'pifss_no':employee_new.pifss_id_no,
									'old_value':value.total_subscription,
									'new_value':employee_new.total_subscription,
									'status':status[0],
									'delta_amount':status[1]
									})
									print("employee has changes are ",status,"pifss no",employee_new.pifss_id_no)

			
			for employee_old in doc_old.deductions:
				if employee_old.pifss_id_no not in list_of_new_values:# fetching left employee who are not showing in the current monthly deduction
					table.append({
						'employee':frappe.get_value('Employee',{'pifss_id_no':employee_old.pifss_id_no},['name']),
						'pifss_no':employee_old.pifss_id_no,
						'old_value':value.total_subscription,
						'new_value':None,
						'status':"Left",
						'delta_amount':None
					})
					print(f"No, Value: '{employee_old.pifss_id_no}' is left")
					
			if len(table)>0:
				for row in table:
					pifss = self.append('pifss_tracking_changes', {})
					pifss.employee = row['employee']
					pifss.pifss_no = row['pifss_no']
					pifss.old_value = row['old_value']
					pifss.new_value = row['new_value']
					pifss.status = row['status']
					pifss.delta_amount = row['delta_amount']
					pifss.save()
					frappe.db.commit()
	
	def check_workflow_status(self):
		"""This method checks the workflow status and throw the required fields"""
		if self.workflow_state == "Pending By Operator":
			field_list = [{'Old PIFSS Monthly Deduction':'old_pifss_monthly_deduction'},{'New PIFSS Monthly Deduction':'new_pifss_monthly_deduction'}]
			self.set_mendatory_fields(field_list)
			self.check_mandatory_fields()
			self.validate_dates()
			self.add_update_total_supscription()
			self.set_has_tracking_record_flag()

		if self.workflow_state == "Rejected By Supervisor":
			field_list = [{'Reason Of Rejection':'reason_of_rejection'}]
			self.set_mendatory_fields(field_list)
			
	def set_mendatory_fields(self,field_list,idx=None):
		"""The method throw message with the rows that contains missing fields"""
		mandatory_fields = []
		for fields in field_list:
			for field in fields:
				if not self.get(fields[field]):
					mandatory_fields.append(field)
		if len(mandatory_fields) > 0:
			message= 'Mandatory fields required For Employee who has Changes in Total Subscription<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' +'<p>fill missing values in row number {0}</p>'.format(idx)+ mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)

	def check_mandatory_fields(self):
		"""This method setting the mendatory fields"""
		mandatory_fields_list = []
		for row in self.pifss_tracking_changes:#each item in the preparation_record row
			if row.status == "Decreased" or row.status == "Increased":
				if not row.date_of_change or not row.details:
					mandatory_fields_list.append({'idx':row.idx})
			if row.status == "Left":
				if not row.relieving_date:
					mandatory_fields_list.append({'idx':row.idx})

		if len(mandatory_fields_list) > 0:
			message = 'Mandatory fields required in PIFSS Monthly Deduction Tool to Submit<br><br><b style="color:red;">First, You Need to Check <a href="{0}" target="_blank">MGRP Website</a></b><br><ul>'.format(self.mgrp_website)
			for mandatory_field in mandatory_fields_list:
				message += '<li>' +'<p> fill the missing fields in row number {0}</p>''</li>'.format(mandatory_field['idx'])
			message += '</ul>'
			frappe.throw(message)
	
	def validate_dates(self):
		"""This method validate the relieving date and date of change fields, and throw message for Operator to modify the dates"""
		for row in self.pifss_tracking_changes:
			if row.status == "Left" and row.relieving_date:
				if date_diff(row.relieving_date, date.today()) >= 0:
					frappe.throw("Cannot create Additional Salary for Left Employee") 
			if row.status == "Decreased" or row.status == "Increased" and row.date_of_change:
				if date_diff(row.date_of_change, date.today()) >= 0:
					frappe.throw("Future Dates are not Accepted for Employee who has Changes in their Total Subscription") 

	def add_update_total_supscription(self):
		"""This method is additing new total supscription based on the value in the date_of_change field"""
		for row in self.pifss_tracking_changes:
			if row.status == "Decreased" or row.status == "Increased":
				number_of_months = self.set_update_total_subscription(row.date_of_change)
				print("number_of_months=>",number_of_months)
				row.updated_total_subscription = number_of_months*flt(row.new_value)
				row.save()
				frappe.db.commit()

	def set_update_total_subscription(self,date_input):
		"""This method will return the number of months from the input date value"""
		month_of_pifss = date.today()#end date
		date_of_change = getdate(date_input)#start date
		num_of_months = (month_of_pifss.year - date_of_change.year) * 12 + (month_of_pifss.month - date_of_change.month)#calculating the months between 2 dates
		if num_of_months >0:
			return num_of_months
		if num_of_months == 0:
			return 1

	def set_has_tracking_record_flag(self):
		"""This method will set the flag per employee in the pifss monthly deduction doctype
		   based on if they have record in the pifss monthly deduction tool doctype"""
		list_of_employee=[cint(row.pifss_no) for row in self.pifss_tracking_changes]#creating list of pifss_id for all employee in the tracking table, convert pifss_id to int because it will be fetched from monthly deduction table as an integer
		monthly_doc = frappe.get_doc('PIFSS Monthly Deduction',self.new_pifss_monthly_deduction)

		#fetch child table for pifss monthly deduction for all employee
		for row in monthly_doc.deductions:
			if frappe.db.exists("Employee", {"pifss_id_no": row.pifss_id_no}):
				if row.pifss_id_no in list_of_employee:#if employee in the tracking system get their updated total subscription
					row.has_tracking_record = 1
					row.save()
		frappe.db.commit()

	def check_flag_for_additional_salary(self):
		""" This method checks the (has tracking record) flag filed in pifss monthly deduction, 
		if flag is 1, the total subscription will be taken from the pifss monthly deduction tool
		 otherwise it will be taken from the pifss monthly deduction record to create the additional salary"""
		list_of_id_and_total=[{cint(row.pifss_no):row.updated_total_subscription} for row in self.pifss_tracking_changes if row.status != "Left"]#creating list of pifss_id for all employee in the tracking table,convert pifss_id to int because it will be fetched from monthly deduction table as an integer
		employee_contribution_percentage = flt(frappe.get_value("PIFSS Settings", "PIFSS Settings", "employee_contribution"))#fetch contribution from pifss settings
		monthly_doc = frappe.get_doc('PIFSS Monthly Deduction',self.new_pifss_monthly_deduction)
		for row in monthly_doc.deductions:#fetch child table for pifss monthly deduction for all employee	
				
			employee_name = frappe.db.get_value("Employee", {"pifss_id_no": row.pifss_id_no})
			if employee_name:
				if row.has_tracking_record == 1:#if employee in the tracking system get their update subscription
					for value in list_of_id_and_total:
						amount = flt(value[cint(row.pifss_id_no)] * (employee_contribution_percentage / 100), precision=3)
						create_additional_salary(employee_name,amount)#create additional salary
						break #exit the loop after getting the new total subscription for the employee with the pifss_id 
				if row.has_tracking_record == 0:#if employee not in the tracking system get their total subscription from deductions table
					amount = flt(cint(row.pifss_id_no) * (employee_contribution_percentage / 100), precision=3)
					create_additional_salary(employee_name,amount)#create additional salary

	

def sub_total_subscription(new_value,old_value):
	"""This method checks the status of the total subscription between last 2 months and return the status with delta amount"""
	if new_value and old_value:
		value = round(new_value-old_value,3)
		if value > 0:
			return ["Increased",value]
		if value < 0:
			return ["Decreased",value]

def create_additional_salary(employee, amount):
	"""Create Additional Salary For employee and set the deduction amount"""
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

#this method has been called from pifss monthly deduction js file
@frappe.whitelist()
def track_pifss_changes(pifss_monthly_deduction_name):
	"""This method is fetching the two csv files of current and previous month,
		and listing employee who got increase or decrease in their total subscription and whose are the new and left kuwaiti employees.
		It returns list to pifss monthly deduction; name of the record and list of pifss number of employee got tracked"""
	# pifss_no_list=[]
	# table=[] #PIFSS Monthly Deduction Tool Table
	if not frappe.db.exists('PIFSS Monthly Deduction Tool',{'new_pifss_monthly_deduction':pifss_monthly_deduction_name}):
		print("Inside")
		first_day_in_previous_month = date.today().replace(day=1) + relativedelta(months=-1)#calculate first date in pervious month
		# new_pifss_doc = frappe.get_doc('PIFSS Monthly Deduction',pifss_monthly_deduction_name)# current pmd record
		pifss_previous_doc_name = frappe.get_value('PIFSS Monthly Deduction',{'deduction_month':first_day_in_previous_month},['name'])#fetch name of previous month record
		if pifss_previous_doc_name:
			
			# old_pifss_doc = frappe.get_doc('PIFSS Monthly Deduction',pifss_previous_doc_name)
			pmd_tool = frappe.new_doc('PIFSS Monthly Deduction Tool')
			pmd_tool.old_pifss_monthly_deduction= pifss_previous_doc_name
			pmd_tool.new_pifss_monthly_deduction=pifss_monthly_deduction_name
			pmd_tool.insert()
			
			return pmd_tool
	elif frappe.db.exists('PIFSS Monthly Deduction Tool',{'new_pifss_monthly_deduction':pifss_monthly_deduction_name}):
		name = frappe.db.get_value('PIFSS Monthly Deduction Tool',{'new_pifss_monthly_deduction':pifss_monthly_deduction_name},['name'])
		return name
	
			# return pmd_tool

# 			send_notification_to_grd(pmd_tool)#notifiy grd operator with the tracking record

# 			return pmd_tool
	
# def send_notification_to_grd(create_record):
# 	"""This method to inform GRD to check the auto created Tracking Table """
# 	operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_pifss")
# 	supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
# 	page_link = get_url("/desk#Form/PIFSS Monthly Deduction Tool/" + create_record.name)
# 	message = "<p>Please Review the list of Employees in the PIFSS Monthly Deduction Tool. <br>Make sure to set the Month of Change field / Relieving Date if required. <a href='{1}'>{0}</a></p>".format(create_record.name,page_link)
# 	subject=_('Review the list of Employees in the PIFSS Monthly Deduction Tool for {0}.').format(create_record.name)
# 	if not frappe.db.exists("Notification Log",{'subject':subject}):
# 		create_notification_log(subject, message, [operator,supervisor], create_record)

