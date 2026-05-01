# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr, add_days, getdate, get_last_day
from one_fm.utils import get_week_start_end, get_month_start_end
from one_fm.processor import sendemail

class EmployeeSchedule(Document):
	def before_save(self):
		"""Enforce read-only for non-System Managers"""
		if not self.is_new():
			# Allow programmatic updates (ignore_permissions=True)
			if frappe.flags.in_patch or frappe.flags.in_install or frappe.flags.in_migrate:
				return
			
			# Allow if ignore_permissions is set (background jobs / programmatic updates)
			if getattr(self.flags, "ignore_permissions", False):
				return
			
			# Check if user has System Manager role
			if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
				frappe.throw(_("Only System Managers can edit Employee Schedule records directly. Please use the appropriate tools (Roster, OJT, Client Event, etc.) to make schedule changes."))

	def before_insert(self):
		if frappe.db.exists("Employee Schedule", {"employee": self.employee, "date": self.date, "roster_type" : self.roster_type}):
			frappe.throw(_("Employee Schedule already scheduled for {employee} on {date}.".format(employee=self.employee_name, date=cstr(self.date))))

		# validate employee is active
		if not frappe.db.exists("Employee", {'status':'Active', 'name':self.employee}):
			frappe.throw(f"{self.employee} - {self.employee_name} is not active and cannot be scheduled.")

	def on_update(self):
		previous_doc =  self.get_doc_before_save()
		if previous_doc and previous_doc.employee_availability != "Day Off" and self.employee_availability == "Day Off":
			start_date = self.date
			end_date = get_last_day(start_date)
			employee_schedule = frappe.get_value("Employee Schedule",
				{
					"employee": self.employee,
					"day_off_ot": 1,
					"date": ["between", [start_date, end_date]],
				},
				["name"], as_dict=True
			)
			if employee_schedule:
				frappe.db.set_value("Employee Schedule", employee_schedule.name, "day_off_ot", 0)

		if self.employee_availability == "Suspended":
			ot_schedules = frappe.get_all("Employee Schedule", filters={"employee": self.employee, "date": self.date, "roster_type": "Over-Time"})
			for ot in ot_schedules:
				frappe.delete_doc("Employee Schedule", ot.name, ignore_permissions=True)

	def validate(self):
		# Clear Client Event-specific fields when transitioning AWAY from Client Event.
		# This handles saves done from the Desk form (roster uses direct SQL).
		if not self.is_new():
			previous_availability = frappe.db.get_value(
				"Employee Schedule", self.name, "employee_availability"
			)
			if previous_availability == "Client Event" and self.employee_availability != "Client Event":
				self.reference_doctype = ""
				self.reference_docname = ""
				self.is_event_schedule = 0
				self.client_event = ""
				self.event_staff = ""
				self.event_location = ""

		self.validate_ojt_change()
		self.validate_leave_application()
		self.validate_relieving_date()
		if self.employee_availability=='Working' and self.shift_type and self.date:
			start_time, end_time = frappe.db.get_value("Shift Type", self.shift_type, ['start_time', 'end_time'])
			end_date = self.date
			if start_time > end_time:
				end_date = add_days(end_date, 1)
			self.start_datetime = f"{self.date} {start_time}"
			self.end_datetime = f"{end_date} {end_time}"

		# clear record if Day Off or Suspended
		if self.employee_availability in ['Day Off', 'Suspended']:
			self.operations_role = ''
			self.post_abbrv = ''
			self.site = ''
			self.shift = ''
			self.shift_type = ''
			self.start_datetime = ''
			self.end_datetime = ''
			self.project = ''

		# validate_operations_post_overfill({self.date: 1}, self.shift)

	def validate_leave_application(self):
		if self.employee and self.date:
			leave_application = frappe.db.exists("Leave Application", {
				"employee": self.employee,
				"status": "Approved",
				"leave_type": "Annual Leave",
				"docstatus": 1,
				"from_date": ["<=", self.date],
				"to_date": [">=", self.date],
			})
			if leave_application:
				frappe.throw(_("You can't add employee schedule for this date because employee {0} has an approved leave application for {1}").format(self.employee, self.date))

	def validate_relieving_date(self):
		if self.employee and self.date:
			relieving_date = frappe.db.get_value("Employee", self.employee, "relieving_date")
			if relieving_date and getdate(self.date) > getdate(relieving_date):
				frappe.throw(_("Employee {0} is expected to leave on {1}, so cannot be scheduled for {2}").format(self.employee, relieving_date, self.date))

	def validate_ojt_change(self):
		if not self.is_new() and self.on_the_job_training and self.employee_availability == "Working":
			old_doc = self.get_doc_before_save()
			if old_doc and old_doc.employee_availability == "On-the-job Training":
				frappe.throw(_("Cannot change availability to 'Working' while an OJT record is linked. To change to 'Working', please delete this schedule and create a new one through Roster."))

	def validate_offs(self):
		"""
		Validate if the employee is has exceeded weekly or monthly off schedule.
		:return:
		"""
		if self.employee_availability in ['Day Off', 'Working']:
			stopthrow = False
			offs = self.get_off_category()
			daterange = self.get_daterange(offs.category, str(self.date))
			querystring = """
				SELECT COUNT(name) as cnt FROM `tabEmployee Schedule`
					WHERE
				employee='{self.employee}' AND employee_availability='{self.employee_availability}'
				AND date BETWEEN '{daterange.start}' AND '{daterange.end}'
			""".format(self=self, daterange=daterange)
			total_schedule = frappe.db.sql(querystring, as_dict=1)[0].cnt
			msg = f"{self.employee_name} - {self.employee} has exceeded '{self.employee_availability}' for {offs.category} on {self.date} between {daterange.start} and {daterange.end}. Off days is {offs.days} day(s)."
			if ((self.employee_availability == 'Day Off') and (total_schedule >= offs.days)):
				stopthrow = True
			else:
				if ((offs.category == 'Monthly') and (total_schedule > (int(daterange.end.split('-')[2])-offs.days))):
					stopthrow = True
				elif ((offs.category == 'Weekly') and (total_schedule > (7-offs.days))):
					stopthrow = True
			if stopthrow:
				frappe.enqueue(
					sendemail,
					recipients=[frappe.session.user],
					subject=frappe._('Employee Schedule Error'),
					message=msg
				)
				frappe.throw(_(msg))
	def get_off_category(self):
		days_off = frappe.db.get_values("Employee", self.employee, ["day_off_category", "number_of_days_off"])[0]
		return frappe._dict({'category': days_off[0], 'days':days_off[1]})

	def get_daterange(self, category, datestr):
		if category == "Monthly":
			return get_month_start_end(datestr)
		return get_week_start_end(datestr)

def is_operations_post_overfill(date, operations_shift, new_roster=0):
	operations_post_overfill = False
	# Fetch total number of active operations post for the operations shift
	no_of_posts = frappe.db.count("Operations Post", {'site_shift': operations_shift, 'status': 'Active'})

	# Fetch employee scedules for the operations_shift and date
	staffs_rostered = frappe.db.count("Employee Schedule",
		{'date': getdate(date), 'employee_availability': 'Working', 'shift': operations_shift}
	)

	'''
		If number of post less than the total of staff rostered and new roster,
		then the post is overfilled else not
	'''
	total_staffs_rostered = staffs_rostered + new_roster
	if no_of_posts < total_staffs_rostered:
		operations_post_overfill = True
	return {"operations_post_overfill": operations_post_overfill, "overfilled_by": total_staffs_rostered-no_of_posts}

def validate_operations_post_overfill(no_of_schedules_on_date, operations_shift):
	dates = False
	for datevalue in no_of_schedules_on_date:
		operations_post_overfill = is_operations_post_overfill(datevalue, operations_shift, no_of_schedules_on_date[datevalue])
		if operations_post_overfill['operations_post_overfill']:
			if not dates:
				dates = str(datevalue)+"({0})".format(operations_post_overfill['overfilled_by'])
			else:
				dates += ', '+str(datevalue)+"({0})".format(operations_post_overfill['overfilled_by'])
	if dates:
		msg = _(
			'The Operation post is overfilled by rostering employees for the operations shift {0} on {1}'
			.format(operations_shift, dates)
		)
		frappe.throw(msg)

@frappe.whitelist()
def get_operations_posts(doctype, txt, searchfield, start, page_len, filters):
	shift = filters.get('shift')
	operations_roles = frappe.db.sql("""
		SELECT DISTINCT name
		FROM `tabOperations Post`
		WHERE site_shift="{shift}"
	""".format(shift=shift))
	return operations_roles
