# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr, add_days, getdate
from one_fm.utils import get_week_start_end, get_month_start_end
from one_fm.processor import sendemail

class EmployeeSchedule(Document):
	def before_insert(self):
		if frappe.db.exists("Employee Schedule", {"employee": self.employee, "date": self.date, "roster_type" : self.roster_type}):
			frappe.throw(_("Employee Schedule already scheduled for {employee} on {date}.".format(employee=self.employee_name, date=cstr(self.date))))

		# validate employee is active
		if not frappe.db.exists("Employee", {'status':'Active', 'name':self.employee}):
			frappe.throw(f"{self.employee} - {self.employee_name} is not active and cannot be scheduled.")


	def validate(self):
		if self.employee_availability=='Working' and self.shift_type and self.date:
			start_time, end_time = frappe.db.get_value("Shift Type", self.shift_type, ['start_time', 'end_time'])
			end_date = self.date
			if start_time > end_time:
				end_date = add_days(end_date, 1)
			self.start_datetime = f"{self.date} {start_time}"
			self.end_datetime = f"{end_date} {end_time}"

		# clear record if Day Off
		if self.employee_availability=='Day Off':
			self.operations_role==''
			self.post_abbrv = ''
			self.site = ''
			self.shift = ''
			self.shift_type = ''
			self.start_datetime = ''
			self.end_datetime = ''
			self.project = ''

		validate_operations_post_overfill({self.date: 1}, self.shift)

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
