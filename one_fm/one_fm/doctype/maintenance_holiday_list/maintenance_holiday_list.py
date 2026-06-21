# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import calendar
from datetime import timedelta

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import cint, formatdate, getdate

from dateutil import relativedelta


class MaintenanceHolidayList(Document):
	def validate(self):
		self.validate_days()
		self.total_holidays = len(self.holidays)
		self.validate_duplicate_date()
		self.sort_holidays()

	def validate_days(self):
		"""Validate that From Date is before To Date and all holidays fall within the range."""
		if getdate(self.from_date) > getdate(self.to_date):
			throw(_("To Date cannot be before From Date"))

		for day in self.get("holidays"):
			if not (getdate(self.from_date) <= getdate(day.holiday_date) <= getdate(self.to_date)):
				frappe.throw(
					_("The holiday on {0} is not between From Date and To Date").format(
						formatdate(day.holiday_date)
					)
				)

	def validate_duplicate_date(self):
		"""Prevent duplicate holiday dates in the table."""
		unique_dates = []
		for row in self.holidays:
			if row.holiday_date in unique_dates:
				frappe.throw(
					_("Holiday Date {0} added multiple times").format(
						frappe.bold(formatdate(row.holiday_date))
					)
				)
			unique_dates.append(row.holiday_date)

	def sort_holidays(self):
		"""Sort holidays by date and reindex."""
		self.holidays.sort(key=lambda x: getdate(x.holiday_date))
		for i in range(len(self.holidays)):
			self.holidays[i].idx = i + 1

	def get_holidays(self):
		"""Return a list of existing holiday dates."""
		return [getdate(holiday.holiday_date) for holiday in self.holidays]

	@frappe.whitelist()
	def get_weekly_off_dates(self):
		"""Calculate all weekly off dates within the From/To Date range and append
		them to the Holidays child table with weekly_off=1, public_holiday=0.
		"""
		if not self.weekly_off:
			throw(_("Please select weekly off day"))

		existing_holidays = self.get_holidays()
		date_list = self.get_weekly_off_date_list(self.from_date, self.to_date)

		last_idx = max(
			[cint(d.idx) for d in self.get("holidays")]
			or [0]
		)

		for i, d in enumerate(date_list):
			if d in existing_holidays:
				continue
			ch = self.append("holidays", {})
			ch.description = _(self.weekly_off)
			ch.holiday_date = d
			ch.weekly_off = 1
			ch.public_holiday = 0
			ch.idx = last_idx + i + 1

	def get_weekly_off_date_list(self, start_date, end_date):
		"""Generate a list of dates matching the selected weekly off day."""
		start_date, end_date = getdate(start_date), getdate(end_date)

		date_list = []
		weekday = getattr(calendar, (self.weekly_off).upper())
		reference_date = start_date + relativedelta.relativedelta(weekday=weekday)

		existing_date_list = [getdate(holiday.holiday_date) for holiday in self.get("holidays")]

		while reference_date <= end_date:
			if reference_date not in existing_date_list:
				date_list.append(reference_date)
			reference_date += timedelta(days=7)

		return date_list

	@frappe.whitelist()
	def get_local_holidays(self):
		"""Fetch regional public holidays for the selected country/subdivision
		and append them with public_holiday=1, weekly_off=0.

		Delegates to ERPNext's existing holidays library integration.
		"""
		if not self.country:
			throw(_("Please select a country"))

		from holidays import country_holidays

		existing_holidays = self.get_holidays()
		from_date = getdate(self.from_date)
		to_date = getdate(self.to_date)

		for holiday_date, holiday_name in country_holidays(
			self.country,
			subdiv=self.subdivision,
			years=list(range(from_date.year, to_date.year + 1)),
			language=frappe.local.lang,
		).items():
			if holiday_date in existing_holidays:
				continue

			if holiday_date < from_date or holiday_date > to_date:
				continue

			self.append(
				"holidays",
				{
					"description": holiday_name,
					"holiday_date": holiday_date,
					"public_holiday": 1,
					"weekly_off": 0,
				},
			)

	@frappe.whitelist()
	def clear_table(self):
		"""Clear all holidays from the child table."""
		self.set("holidays", [])


@frappe.whitelist()
def get_supported_countries():
	"""Fetch supported countries for the country autocomplete field.

	This is a module-level function (not a class method) so it can be
	called on new, unsaved documents via frappe.call().
	"""
	temp = frappe.new_doc("Holiday List")
	return temp.get_supported_countries()
