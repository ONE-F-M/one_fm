# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class PostAllocationPlan(Document):
	pass

@frappe.whitelist()
def filter_posts(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		SELECT post
		FROM `tabPost Schedule`
		WHERE 
			post_status="Planned"
		AND shift=%(shift)s
		AND date=%(date)s 
	""", {
		'shift': frappe.db.escape(filters.get("operations_shift")),
		'date': frappe.db.escape(filters.get("date"))
	})

@frappe.whitelist()
def get_table_data(operations_shift, date):
	print(operations_shift, date)
	employees = frappe.get_all("Employee Schedule", {'date': date, 'shift': operations_shift, 'employee_availability': 'Working'}, ["employee", "employee_name"])
	posts = frappe.db.get_all("Post Schedule", {'date': date, 'shift': operations_shift, 'post_status': 'Planned'}, ["post"])
	
	post_details_list = []
	for post in posts:
		post_data = get_post_data_map(post)
		post_details_list.append(post_data)

	employee_details_list = []
	for employee in employees:
		employee_skills = get_employee_data_map(employee)
		employee_details_list.append(employee_skills)		

	return {
		'employees': employee_details_list, 
		'posts': post_details_list
	}

def get_employee_data_map(employee):
	employee_skills = frappe._dict()
	if frappe.db.exists("Employee Skill Map", employee.employee):
		employee_skill = frappe.get_doc("Employee Skill Map", employee.employee).as_dict()
		employee_skills.skills = [{'skill': skill.skill, 'proficiency': skill.proficiency } for skill in employee_skill.employee_skills]
		employee_skills.designation = employee_skill.designation
	else:
		frappe.throw(_("Employee Skill Map not found for {id}:{name}".format(id=employee.employee, name=employee.employee_name)))
	
	gender = frappe.db.get_value("Employee", employee.employee, "gender")
	employee_skills.update({"gender": gender})
	employee_skills.update(employee)
	return employee_skills

def get_post_data_map(post):
	post_data = frappe._dict()
	post_doc = frappe.get_doc("Operations Post", post.post).as_dict()
	post_data.gender = post_doc.gender
	post_data.skills =  [{'skill': skill.skill, 'proficiency': skill.minimum_proficiency_required } for skill in post_doc.skills]
	post_data.designations = [designation.designation for designation in post_doc.designations]
	post_data.post = post.post
	print(post_data)
	return post_data