# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import date
from frappe.utils import getdate,get_first_day,get_last_day
#from one_fm.one_fm.sales_invoice_custom import add_into_sales_invoice

class EmergencyDeployment(Document):
	pass

def create_sales_invoice_for_emergency_deployments(contracts = None):
	today = date.today()
	today = getdate("31-10-2020")
	day = today.day
	#contracts = 'bfef4b805e'
	first_day = get_first_day(today)
	last_day = get_last_day(today)
	filters = { 
		'date': ['between', (first_day, last_day)],
		'contracts': contracts
	}
	emergency_deployment_list = frappe.db.sql("""select ci.item_code,ci.head_count as qty,ci.days,ci.shift_hours,
		ci.type,ci.unit_rate,ci.monthly_rate
		from `tabContract Item` ci,`tabEmergency Deployment` e 
		where e.name = ci.parent and ci.parenttype = 'Emergency Deployment'
		and e.contracts = %s and date between %s and %s 
		order by e.date asc""",(contracts,first_day,last_day),as_dict = 1)
	if emergency_deployment_list:
		customer,project,price_list = frappe.db.get_value('Contracts',contracts,['client','project','price_list'])
		income_account,cost_center = frappe.db.get_value('Project',project,['income_account','cost_center'])
		sales_invoice = frappe.new_doc('Sales Invoice')
		sales_invoice.contracts = contracts
		sales_invoice.customer = customer
		sales_invoice.set_posting_time = 1
		sales_invoice.project = project
		sales_invoice.selling_price_list = price_list
		#overriding erpnext standard functionality
		sales_invoice.timesheets = []
		for item in emergency_deployment_list:
			sales_invoice.append('items',{
				'item_code': item.item_code,
				'qty':item.qty,
				'rate': item.unit_rate * item.shift_hours * item.days,
				#'site': site,
				'days': item.days,
				'basic_hours': item.shift_hours,
				'hourly_rate': item.unit_rate,
				#'monthly_rate': monthly_rate,
				'total_hours' : item.days * item.shift_hours,
				'hours_worked' : item.days * item.shift_hours,
				'income_account': income_account,
				'cost_center': cost_center
			})
		add_into_sales_invoice(sales_invoice)	
	return 
