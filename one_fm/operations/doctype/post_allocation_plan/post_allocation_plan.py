# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, cstr, add_to_date
import itertools, time

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
	employees = frappe.get_all("Employee Schedule", {'date': date, 'shift': operations_shift, 'employee_availability': 'Working'}, ["employee", "employee_name"])
	posts = get_posts(operations_shift, date)
	post_list = {}

	for key, group in itertools.groupby(posts, key=lambda x: (x['priority_level'])):
		post_details_list = []
		# Sort descending by length of skills in post
		priority_posts = sorted(list(group), key=post_sorting, reverse=True)
		for post in priority_posts:
			post_data = get_post_data_map(post)
			post_details_list.append(post_data)

		post_list.update({key: post_details_list})	

	employee_details_list = []
	for employee in employees:
		employee_skills = get_employee_data_map(employee, operations_shift, date)
		employee_details_list.append(employee_skills)		

	return {
		'employees': employee_details_list, 
		'posts': post_list
	}

def post_sorting(post):
	return len(post.skills) if post.skills else 0

def get_posts(operations_shift, date):
	return frappe.db.sql("""
		SELECT ps.post, p.priority_level
		FROM `tabPost Schedule` ps, `tabOperations Post` p
		WHERE 
			ps.post=p.name
		AND	ps.post_status="Planned"
		AND ps.shift=%(shift)s
		AND ps.date=%(date)s 
		ORDER BY p.priority_level DESC, p.gender DESC
	""", {
		'shift':operations_shift,
		'date': date
	}, as_dict=1)

def get_employee_data_map(employee, shift, date):
	employee_skills = frappe._dict()
	if frappe.db.exists("Employee Skill Map", employee.employee):
		employee_skill = frappe.get_doc("Employee Skill Map", employee.employee).as_dict()
		employee_skills.skills = [{'skill': skill.skill, 'proficiency': skill.proficiency } for skill in employee_skill.employee_skills]
		employee_skills.certifications = [{'certification' : training_program_certificate.training_program_name, 'issue_date' : cstr(training_program_certificate.issue_date), 'expiry_date' : cstr(training_program_certificate.expiry_date)} for training_program_certificate in get_training_program_certificate_documents(employee.employee)]
		#employee_skills.licenses = [{'license' : employee_license.license, 'issue_date' : employee_license.issue_date, 'expiry_date' : employee_license.expiry_date} for employee_license in employee_skill.employee_licenses]
		employee_skills.designation = frappe.db.get_value("Employee", employee.employee, "designation")
	else:
		frappe.throw(_("Employee Skill Map not found for {id}:{name}".format(id=employee.employee, name=employee.employee_name)))

	prev_date = cstr(add_to_date(getdate(date), days=-1))
	previous_day = frappe.db.get_value("Employee Schedule", {"employee": employee.employee, "date": prev_date}, ["employee_availability"])
	previous_day_schedule = frappe.db.get_value("Post Allocation Employee Assignment", {"parent": shift+"|"+prev_date, "employee": employee.employee}, ["post"])

	day_before_prev_date = cstr(add_to_date(getdate(date), days=-2))
	day_before_previous_day = frappe.db.get_value("Employee Schedule", {"employee": employee.employee, "date": day_before_prev_date}, ["employee_availability"])
	day_before_previous_day_schedule = frappe.db.get_value("Post Allocation Employee Assignment", {"parent": shift+"|"+day_before_prev_date, "employee": employee.employee}, ["post"])

	gender = frappe.db.get_value("Employee", employee.employee, "gender")
	employee_skills.update({"previous_day": previous_day, "previous_day_schedule": previous_day_schedule})
	employee_skills.update({"day_before_previous_day": day_before_previous_day, "day_before_previous_day_schedule": day_before_previous_day_schedule})
	employee_skills.update({"gender": gender})
	employee_skills.update(employee)
	return employee_skills


def get_training_program_certificate_documents(employee):
	docs = []
	doc_name_list = frappe.db.get_list("Training Program Certificate", {'employee': employee})
	for doc_name in doc_name_list:
		docs.append(frappe.get_doc("Training Program Certificate", doc_name))
	return docs	

def get_post_data_map(post):
	post_data = frappe._dict()
	post_doc = frappe.get_doc("Operations Post", post.post).as_dict()
	post_data.gender = post_doc.gender
	post_data.priority_level = post_doc.priority_level
	post_data.skills =  [{'skill': skill.skill, 'proficiency': skill.minimum_proficiency_required } for skill in post_doc.skills]
	post_data.designations = [designation.designation for designation in post_doc.designations]
	post_data.certifications = [post_certification.certification for post_certification in post_doc.post_certifications]
	#post_data.licenses = [post_license.license for post_license in post_doc.post_licenses]
	post_data.post = post.post
	post_data.allow_staff_rotation = post_doc.allow_staff_rotation
	post_data.day_off_priority = post_doc.day_off_priority
	return post_data

@frappe.whitelist()
def get_post_employee_data(employee, operations_shift, post, date):
	return {
		'employee': get_employee_data_map(frappe.get_value("Employee", employee, ["name as employee", "employee_name"], as_dict=1), operations_shift, date),
		'post': get_post_data_map(frappe.get_value("Operations Post", post, ["name as post", "priority_level"], as_dict=1))
	}

@frappe.whitelist()
def get_day_off_employees(operations_shift, date):
	employees = frappe.db.sql("""
		SELECT DISTINCT name, employee_name, designation
		FROM `tabEmployee` 
		WHERE shift=%(shift)s AND NAME IN(SELECT employee FROM `tabEmployee Schedule` WHERE date=%(date)s AND employee_availability="Day Off")  """, {
		'shift': operations_shift,
		'date': date
	}, as_dict=1)
	return employees


@frappe.whitelist()
def get_sorted_post_list(assignments):
	# Converting into list of tuple
	assignments = [(key,)+tuple(val) for assignment in assignments for key,val in assignment.items()]
	col = 1
	sorted(assignments, key=lambda k: (k[col] is None, k[col] == "", k[col])) 
	print(assignments)