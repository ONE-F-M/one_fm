# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json, time
from datetime import timedelta
from frappe.model.document import Document
from frappe import _
from frappe.model.rename_doc import rename_doc
from frappe.utils import cstr, get_datetime, today, formatdate, getdate, add_days, get_time

class OperationsShift(Document):
	def autoname(self):
		#this method is updating the name of the record and sending clear message through exception if any of the records are missing
		try:
			self.name = self.service_type+"-"+self.site+"-"+self.shift_classification+"-"+cstr(self.shift_number)
		except Exception as e:
			if not self.service_type and self.site and self.shift_classification:
				frappe.throw("Kindly, make sure all required fields are not missing")

	def clear_cache(self):
		if self.has_value_changed('supervisor'):
			frappe.cache.delete_key('user_permissions')

	def on_update(self):
		self.clear_cache()
		self.validate_name()
		self.update_employee_schedules_and_shift_assignments()

		if self.has_value_changed("status"): # only updates post and roles when status is changed
			self.update_post_status()
			

	def validate_name(self):
		#this method is updating the name of the record and sending clear message through exception if any of the records are missing
		try:
			new_name = self.service_type+"-"+self.site+"-"+self.shift_classification+"-"+cstr(self.shift_number)
			if new_name != self.name:
				rename_doc(self.doctype, self.name, new_name, force=True)
		except Exception as e:
			if not self.service_type and self.site and self.shift_classification:
				frappe.throw("Kindly, make sure all required fields are not missing")

	def validate(self):
		if self.status != 'Active':
			self.set_operation_role_inactive()
		self.validate_operations_site_status()
		self.validate_operations_shift_link_to_employees()
		self.validate_duration()

	def validate_duration(self):
		if self.shift_type:
			self.duration = frappe.db.get_value("Shift Type", self.shift_type, 'duration')

	def update_post_status(self):
		if frappe.db.exists("Operations Post", {'site_shift':self.name}):
			frappe.db.sql(f"""
				UPDATE `tabOperations Post` set status="{self.status}"
				WHERE site_shift="{self.name}";
			""")
		if frappe.db.exists("Operations Role", {'shift':self.name}):
			frappe.db.sql(f"""
				UPDATE `tabOperations Role` set status="{self.status}"
				WHERE shift="{self.name}";
			""")

	def validate_operations_shift_link_to_employees(self):
		if self.status != 'Active' and self.shift_type:
			query = """
				select
					name, employee_name
				from
					`tabEmployee`
				where
					status = 'Active' and shift = '{0}'
			"""
			employees = frappe.db.sql(query.format(self.name), as_dict=True)
			if employees and len(employees) > 0:
				msg = "The shift `{0}` is linked with {1} employee(s):<br/>".format(self.name, len(employees))
				for employee in employees:
					msg += "<br/>"+"<a href='/app/employee/{0}'>{0}: {1}</a>".format(employee.name, employee.employee_name)
				msg += '</br></br><a href="/app/employee?status=Active&shift={0}">click here to view the list</a>'.format(self.name)
				frappe.throw(_("{0}".format(msg)))

	def validate_operations_site_status(self):
		if self.status == "Active" and self.site \
			and frappe.db.get_value('Operations Site', self.site, 'status') != 'Active':
			frappe.throw(_("The Site '<b>{0}</b>' selected in the Shift '<b>{1}</b>' is <b>Inactive</b>. <br/> To make the Shift active first make the Site active".format(self.site, self.name)))

	def set_operation_role_inactive(self):
		operations_role_list = frappe.get_all('Operations Role', {'is_active': 1, 'shift': self.name})
		if operations_role_list:
			if len(operations_role_list) > 10:
				frappe.enqueue(queue_operation_role_inactive, operations_role_list=operations_role_list, is_async=True, queue="long")
				frappe.msgprint(_("Operations Role linked to the Shift {0} will set to Inactive!".format(self.name)), alert=True, indicator='green')
			else:
				queue_operation_role_inactive(operations_role_list)
				frappe.msgprint(_("Operations Role linked to the Shift {0} is set to Inactive!".format(self.name)), alert=True, indicator='green')

	def update_employee_schedules_and_shift_assignments(self):
		if self.is_new():
			return
		
		if self.has_value_changed('shift_type'):
			start_time = get_time(self.start_time)
			end_time = get_time(self.end_time)

			frappe.enqueue(update_employee_schedule_shift_type, is_async=True, queue='long', operations_shift=self.name, new_shift_type=self.shift_type, new_start_time=start_time, new_end_time=end_time)
			frappe.enqueue(update_shift_assignment_shift_type, is_async=True, queue='long', operations_shift=self.name, new_shift_type=self.shift_type, new_start_time=start_time, new_end_time=end_time)


def queue_operation_role_inactive(operations_role_list):
	for operations_role in operations_role_list:
		doc = frappe.get_doc('Operations Role', operations_role.name)
		doc.is_active = False
		doc.save(ignore_permissions=True)

@frappe.whitelist()
def create_posts(data, site_shift, site, project=None):
	try:
		data = frappe._dict(json.loads(data))
		post_names = data.post_names
		skills = data.skills
		designations = data.designations
		gender = data.gender
		sale_item = data.sale_item
		post_template = data.post_template
		post_description = data.post_description
		post_location = data.post_location

		for post_name in post_names:
			operations_post = frappe.new_doc("Operations Post")
			operations_post.post_name = post_name["post_name"]
			operations_post.gender = gender
			operations_post.post_location = post_location
			operations_post.post_description = post_description
			operations_post.post_template = post_template
			operations_post.sale_item = sale_item
			operations_post.site_shift = site_shift
			operations_post.site = site
			operations_post.project = project
			for designation in designations:
				operations_post.append("designations",{
					"designation": designation["designation"],
					"primary": designation["primary"] if "primary" in designation else 0
				})
			for skill in skills:
				operations_post.append("skills",{
					"skill": skill["skill"],
					"minimum_proficiency_required": skill["minimum_proficiency_required"]
				})

			operations_post.save()

		frappe.db.commit()
		frappe.msgprint(_("Posts created successfully."))
	except Exception as e:
		frappe.throw(_(frappe.get_traceback()))

def get_shift_supervisor_user(shift, date=False):
	shift_supervisor = get_shift_supervisor(shift, date)
	if shift_supervisor:
		return frappe.db.get_value("Employee", shift_supervisor, "user_id")
	return None

def get_shift_supervisor(shift, date=False):
	# Get all the shift supervisors assigned to the shift
	supervisors = frappe.get_all(
		"Operations Shift Supervisor",
		fields=["supervisor"],
		filters={
			"parent": shift, "parenttype": "Operations Shift"
		},
		order_by="idx"
	)

	if not date:
		date = getdate()

	for supervisor in supervisors:
		# Return the supervisor if the supervisor working on the day
		shift_working = frappe.db.get_value("Employee", supervisor.supervisor, "shift_working")
		if shift_working:
			if frappe.db.exists(
				"Employee Schedule",
				{
					"employee": supervisor.supervisor,
					"date": date,
					"employee_availability": "Working"
				}
			):
				return supervisor.supervisor
		else:
			if not frappe.db.exists("Leave Application", {"employee": supervisor.supervisor, "status": "Approved", "from_date":["<=", date], "to_date":[">=", date]}):
				return supervisor.supervisor

	return None

def get_supervisor_operations_shifts(supervisor=None, project=None, site=None):
	query = """
		select
			distinct shift.name
		from
			`tabOperations Shift Supervisor` supervisor,
			`tabOperations Shift` shift
		where
			supervisor.parenttype='Operations Shift'
			and
			supervisor.parent=shift.name
			and
			status='Active'
	"""
	if supervisor:
		query += " and supervisor.supervisor='{0}'".format(supervisor)
	if project:
		query += " and shift.project='{0}'".format(project)
	if site:
		query += " and shift.site='{0}'".format(site)

	shifts = frappe.db.sql(query, as_dict=True)

	return [shift.name for shift in shifts]

def update_employee_schedule_shift_type(operations_shift, new_shift_type, new_start_time, new_end_time):
	employee_schedules = frappe.get_all("Employee Schedule", filters={"shift": operations_shift, "date": [">=", today()]}, fields=["name", "date"])

	for schedule in employee_schedules:
		start_date_time = f"{schedule.date} {new_start_time}"
		end_date_time = f"{add_days(schedule.date, 1) if new_start_time > new_end_time else schedule.date} {new_end_time}"

		frappe.db.set_value("Employee Schedule", schedule.name, {"shift_type": new_shift_type, "start_datetime": start_date_time, "end_datetime": end_date_time})

def update_shift_assignment_shift_type(operations_shift, new_shift_type, new_start_time, new_end_time):
	shift_assignments = frappe.get_all("Shift Assignment", filters={"shift": operations_shift, "start_date": [">=", today()]}, fields=["name", "start_date", "end_date", "shift_classification"])

	for assignment in shift_assignments:
		start_date_time = f"{assignment.start_date} {new_start_time}"
		end_date_time = f"{add_days(assignment.end_date, 1) if new_start_time > new_end_time else assignment.end_date} {new_end_time}" if assignment.end_date else ""

		frappe.db.set_value("Shift Assignment", assignment.name, {"shift_type": new_shift_type, "start_datetime": start_date_time, "end_datetime": end_date_time, "shift_classification": assignment.shift_classification})
