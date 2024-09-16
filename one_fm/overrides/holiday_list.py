# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import pycountry
import json, frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import cint, formatdate, getdate, today
from erpnext.setup.doctype.holiday_list.holiday_list import *


class OverlapError(frappe.ValidationError):
	pass


class HolidayListOverride(HolidayList):
	def validate(self):
		self.validate_days()
		self.total_holidays = len(self.holidays)
	
	def on_update(self):
		# Get the previous version of the document
		previous_doc = self.get_doc_before_save()
		# Loop through the child table records
		# if previous_doc:
		# 	for idx, row in enumerate(self.holidays):
		# 		#only on update of existing Row
		# 		if len(previous_doc.get("holidays")) != idx:
		# 			previous_row = previous_doc.get("holidays")[idx]
		# 			old_date = getdate(previous_row.holiday_date)
		# 			new_date = getdate(row.holiday_date)
		# 			# Compare the field in the current row with the previous version
		# 			if old_date != new_date:
		# 				self.validate_attendance(old_date, new_date)
			

	@frappe.whitelist()
	def get_weekly_off_dates(self):
		self.validate_values()
		date_list = self.get_weekly_off_date_list(self.from_date, self.to_date)
		last_idx = max(
			[cint(d.idx) for d in self.get("holidays")]
			or [
				0,
			]
		)
		for i, d in enumerate(date_list):
			ch = self.append("holidays", {})
			ch.description = _(self.weekly_off)
			ch.holiday_date = d
			ch.weekly_off = 1
			ch.idx = last_idx + i + 1

	def validate_values(self):
		if not self.weekly_off:
			throw(_("Please select weekly off day"))

	def validate_days(self):
		if getdate(self.from_date) > getdate(self.to_date):
			throw(_("To Date cannot be before From Date"))

		for day in self.get("holidays"):
			if not (getdate(self.from_date) <= getdate(day.holiday_date) <= getdate(self.to_date)):
				frappe.throw(
					_("The holiday on {0} is not between From Date and To Date").format(
						formatdate(day.holiday_date)
					)
				)
	def validate_attendance(self, old_date, new_date):
		old_date_attendance = frappe.get_list("Attendance",{'attendance_date':old_date, 'status':'Holiday'},['*'])
		if old_date_attendance:
			for att in old_date_attendance:
				#Attendance For Old Date.
				leave_application = frappe.db.sql(f"""SELECT * FROM `tabLeave Application` WHERE '{old_date}' BETWEEN from_date AND to_date AND employee = '{att.employee}'""", as_dict=1)
				if leave_application:
					att_doc = frappe.get_doc("Attendance", att.name)
					att_doc.db_set("status",'On Leave')
					att_doc.db_set('leave_type',leave_application[0].leave_type)
					att_doc.db_set('leave_application',leave_application[0].name)
					att_doc.submit()
		
		#Attendance For New Date
		new_date_attendance = frappe.get_list("Attendance",{'attendance_date':new_date},['*'])
		if new_date_attendance:
			for n_att in new_date_attendance:
				if frappe.db.exists("Employee",{'name':n_att.employee, 'holiday_list':self.name}):
					doc = frappe.get_doc("Attendance",n_att.name)
					doc.db_set("status",'Holiday')
					doc.db_set('leave_type','')
					doc.db_set('leave_application','')
		frappe.db.commit()	

	def get_weekly_off_date_list(self, start_date, end_date):
		start_date, end_date = getdate(start_date), getdate(end_date)

		import calendar
		from datetime import timedelta

		from dateutil import relativedelta

		date_list = []
		existing_date_list = []
		weekday = getattr(calendar, (self.weekly_off).upper())
		reference_date = start_date + relativedelta.relativedelta(weekday=weekday)

		existing_date_list = [getdate(holiday.holiday_date) for holiday in self.get("holidays")]

		while reference_date <= end_date:
			if reference_date not in existing_date_list:
				date_list.append(reference_date)
			reference_date += timedelta(days=7)

		return date_list


	@frappe.whitelist()
	def clear_table(self):
		self.set("holidays", [])

	@frappe.whitelist()
	def get_supported_countries(self):
		from holidays.utils import list_supported_countries

		subdivisions_by_country = list_supported_countries()
		if not subdivisions_by_country.get('KW'):
			subdivisions_by_country['KW'] = []
		countries = [
			{"value": country, "label": local_country_name(country)}
			for country in subdivisions_by_country.keys()
		]
		return {
			"countries": countries,
			"subdivisions_by_country": subdivisions_by_country,
		}


@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	if filters:
		filters = json.loads(filters)
	else:
		filters = []

	if start:
		filters.append(["Holiday", "holiday_date", ">", getdate(start)])
	if end:
		filters.append(["Holiday", "holiday_date", "<", getdate(end)])

	return frappe.get_list(
		"Holiday List",
		fields=[
			"name",
			"`tabHoliday`.holiday_date",
			"`tabHoliday`.description",
			"`tabHoliday List`.color",
		],
		filters=filters,
		update={"allDay": 1},
	)


def is_holiday(holiday_list, date=None):
	"""Returns true if the given date is a holiday in the given holiday list"""
	if date is None:
		date = today()
	if holiday_list:
		return bool(
			frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date}, cache=True)
		)
	else:
		return False

