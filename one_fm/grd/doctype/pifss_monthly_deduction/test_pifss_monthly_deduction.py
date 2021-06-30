# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe
import unittest
from frappe.utils import flt, getdate
import pandas as pd
import frappe, erpnext
from frappe.model.document import Document
from frappe import _
class TestPIFSSMonthlyDeduction(unittest.TestCase):
	pass

def import_deduction_data(file_url):#file_url
	url = frappe.get_site_path() + file_url
	# print(url)
	df = pd.read_csv(url, encoding='utf-8')
	
	print("File URL")
	print(df)
	# print("28", df)#just printing text near the file
	data = {}
	#Due Date part NEED TO DESCUSS
	# for index, row in df.iterrows(): 
	# 	print(index)# textbox48 (first one).....
	# 	print(str(row[1])+"=> "+str(row[7]))# amount => civilID value in each heading
	# 	if frappe.db.exists("Employee", {"one_fm_civil_id": row[7]}):
	# 		employee = frappe.get_doc('Employee', {'one_fm_civil_id':row[7]})
	# 		emplo = frappe.get_doc('deductions')
	# 		print(emplo)
	url = frappe.get_site_path() + file_url
	data = {}	
	table_data = []
	df = pd.read_csv(url, encoding='utf-8')
	for index, row in df.iterrows():
		# print(str(row[1])+"=> "+str(row[7]))# amount => civilID value in each heading
		if frappe.db.exists("Employee", {"one_fm_civil_id": row[7]}):
			employee = frappe.get_doc('Employee', {'one_fm_civil_id':row[7]})
			# table_data.append({'pifss_id_no': row[12], 'total_subscription': flt(row[1])})
			additional_amount = flt(row[1], precision=3)#employee_amount
			civi_id = row[7]
			table_data.append({'pifss_id_no': employee.pifss_id_no, 'additional_deduction': additional_amount, 'employee': employee.employee})

			employee_deduction = frappe.db.get_list('PIFSS Monthly Deduction Employees')
			employee = frappe.db.get_list('Employee',{'one_fm_civil_id':civi_id})
			for employee in employee_deduction:
				if employee.pifss_id_no == employee_deduction.pifss_id_no:
					print(employee_deduction)
	# data.update({'table_data': table_data})
	# print(data)

		
			# employee_deduction.append('additional_deduction':additional_amount)
	

			# for employee_in_deductions in frappe.get_doc('deductions'):
			# 	print(employee_in_deductions.pifss_id_no)
				# if employee.pifss_id_no == employee_in_deductions.pifss_id_no:
				# 	employee_in_deductions.append('deductions',{'employer_deduction':flt(row[1])})
				# 	print(employee_in_deductions)
			# deduction_list = frappe.get_doc('PIFSS Monthly Deduction Employees')
			# print(deduction_list)

			# for employee_deduct in deduction_list:
			# 	if employee_deduct.pifss_id_no == employee.pifss_id_no:
			# 		employee_deduct.append("deductions",{
			# 			"employer_deduction": flt(row[1]),
			# 			})
			# 		employee_deduct.save()
			# 		print(employee_decduct)

			# employee = frappe.db.get_value("Employee", {"pifss_id_no": employee.pifss_id_no})
			# print(employee.pifss_id_no)
			# print(employee.first_name)
	
		# if index == 2:#will not reach it at all
		# 	date = row[0].replace("/", "-")
		# 	data.update({'deduction_month': date})

	# row_count = len(df.index)
	# print(row_count)
	# print("second ")
	# table_data = []
	# df = pd.read_csv(url, encoding='utf-8',skiprows = 3)#.drop([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])#TESTING 
	# for index, row in df.iterrows():
	# 	employee_amount = flt(row[1] * (10.5 / 100),precision=3)#employee_amount
	# 	employer_amount = flt(row[1] * (11.5 / 100),precision=3)#employer_amount
	# 	table_data.append({'pifss_id_no': row[12], 'total_subscription': flt(row[1]), 'employee_deduction':employee_amount, 'employer_deduction':employer_amount})
	# 	print(row[12], row[1], employee_amount, employer_amount)
	# data.update({'table_data': table_data})
	# print(data)
	# return data
def test():
	print('===>',round(6237.155000000003, 3))