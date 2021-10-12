# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from frappe.utils import get_url, getdate, cint, flt, date_diff
from frappe.core.doctype.communication.email import make
from frappe import _
from one_fm.api.notification import create_notification_log
class PIFSSMonthlyDeductionTool(Document):

	def on_submit(self):
		self.check_mandatory_fields()
		for row in self.pifss_tracking_changes:
			if row.status == "Decreased" or row.status == "Increased":
				number_of_months = self.set_update_total_subscription(row.date_of_change)
				print("The month is ",number_of_months)
				print("Value after submitted",number_of_months*cint(row.new_value))
				row.updated_total_subscription = number_of_months*flt(row.new_value)
			if row.status == "New":
				number_of_months = self.set_update_total_subscription(row.date_of_joining)
				row.updated_total_subscription = number_of_months*flt(row.new_value)
			row.save()
		self.status = "Completed"

	def on_update(self):
		self.compare_employee_in_months()
		
	def compare_employee_in_months(self):
		"""This method is comparing the pifss monthly deduction of the current and the last one;
		 new kuwaiti employees, left employees and who got changes in their total subscription"""
		if self.old_pifss_monthly_deduction and self.new_pifss_monthly_deduction:
			doc_old = frappe.get_doc('PIFSS Monthly Deduction',self.old_pifss_monthly_deduction)#old monthly deduction doctype
			doc_new = frappe.get_doc('PIFSS Monthly Deduction',self.new_pifss_monthly_deduction)#new monthly deduction doctype
			list_of_old=frappe.db.get_list('PIFSS Monthly Deduction Employees',{'parent':doc_old},['pifss_id_no','total_subscription'])#deductions table in the old monthly deduction doctype
			list_of_new=frappe.db.get_list('PIFSS Monthly Deduction Employees',{'parent':doc_new},['pifss_id_no','total_subscription'])#deductions table in the new monthly deduction doctype
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
								status = sub_total_subscription(employee_new.total_subscription,value.total_subscription)#will return list of status and delta amount like status = ['Increased',90]
								
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
						'employee':frappe.get_value('Employee',{'pifss_id_no':employee_new.pifss_id_no},['name']),
						'pifss_no':employee_new.pifss_id_no,
						'old_value':value.total_subscription,
						'new_value':None,
						'status':"Left",
						'delta_amount':None
					})
					print(f"No, Value: '{employee_new.pifss_id_no}' is left")
		if len(table)>0:
			for row in table:
				print(row)
				pifss = self.append('pifss_tracking_changes', {})
				pifss.employee = row['employee']
				pifss.pifss_no = row['pifss_no']
				pifss.old_value = row['old_value']
				pifss.new_value = row['new_value']
				pifss.status = row['status']
				pifss.delta_amount = row['delta_amount']
				pifss.save()
				frappe.db.commit()
	
	def check_mandatory_fields(self):
		"""This method setting the mendatory fields and the new total subscription based on the munber of months they had the changes"""
		list=[]
		for row in self.pifss_tracking_changes:
			if row.status == "Decreased":
				if not row.date_of_change or not row.details:
					list.append(row.idx)
					fields = [{'Date Of Change':'date_of_change'},{'Details':'details'}]
					self.set_mendatory_fields(fields,list)

			if row.status == "Increased":
				if not row.date_of_change or not row.details:
					list.append(row.idx)
					fields = [{'Date Of Change':'date_of_change'},{'Details':'details'}]
					self.set_mendatory_fields(fields,list)

			if row.status == "New":
				if not row.date_of_joining:
					list.append(row.idx)
					fields = [{'Date of Joining':'date_of_joining'}]
					self.set_mendatory_fields(fields,list)

			if row.status == "Left":
				if not row.relieving_date:
					list.append(row.idx)
					fields = [{'Relieving Date':'relieving_date'}]
					self.set_mendatory_fields(fields,list)

	def set_update_total_subscription(self,date_input):
		"""This method will return the number of months employee got the changes in thrir total subscription"""
		month_of_pifss = date.today()#end date
		change_date = getdate(date_input)#start date
		num_months = (month_of_pifss.year - change_date.year) * 12 + (month_of_pifss.month - change_date.month)#calculating the months between 2 dates
		if num_months >=0:
			return num_months

	def set_mendatory_fields(self,field_list,idx):
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

def sub_total_subscription(new_value,old_value):
	"""This method checks the status of the total subscription between last 2 months"""
	if new_value and old_value:
		value = round(new_value-old_value,3)
		if (value)>0:
			return ["Increased",value]
		if (value)<0:
			return ["Decreased",value]

def track_pifss_changes(pifss_monthly_deduction_name):
	"""This method is fetching the two csv files of current and previous month,
		and listing employee who got increase or decrease in their total subscription and whose are the new and left kuwaiti employees.
		It returns list to pifss monthly deduction; name of the record and list of pifss number of employee got tracked"""
	# pifss_no_list=[]
	# table=[] #PIFSS Monthly Deduction Tool Table
	if not frappe.db.exists('PIFSS Monthly Deduction Tool',{'new_pifss_monthly_deduction':pifss_monthly_deduction_name}):
		first_day_in_previous_month = date.today().replace(day=1) + relativedelta(months=-1)#calculate first date in pervious month
		# new_pifss_doc = frappe.get_doc('PIFSS Monthly Deduction',pifss_monthly_deduction_name)# current pmd record
		pifss_previous_doc_name = frappe.get_value('PIFSS Monthly Deduction',{'deduction_month':first_day_in_previous_month},['name'])#fetch name of previous month record
		if pifss_previous_doc_name:
			
			# old_pifss_doc = frappe.get_doc('PIFSS Monthly Deduction',pifss_previous_doc_name)
			pmd_tool = frappe.new_doc('PIFSS Monthly Deduction Tool')
			pmd_tool.old_pifss_monthly_deduction= pifss_previous_doc_name
			pmd_tool.new_pifss_monthly_deduction=pifss_monthly_deduction_name
			pmd_tool.insert()
			pmd_tool.save()

			send_notification_to_grd(pmd_tool)#notifiy grd operator with the tracking record

			return pmd_tool
	
def send_notification_to_grd(create_record):
	"""This method to inform GRD to check the auto created Tracking Table """
	operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_pifss")
	supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
	page_link = get_url("/desk#Form/PIFSS Monthly Deduction Tool/" + create_record.name)
	message = "<p>Please Review the list of Employees in the PIFSS Monthly Deduction Tool. <br>Make sure to set the Month of Change field / Relieving Date if required. <a href='{1}'>{0}</a></p>".format(create_record.name,page_link)
	subject=_('Review the list of Employees in the PIFSS Monthly Deduction Tool for {0}.').format(create_record.name)
	if not frappe.db.exists("Notification Log",{'subject':subject}):
		create_notification_log(subject, message, [operator,supervisor], create_record)

