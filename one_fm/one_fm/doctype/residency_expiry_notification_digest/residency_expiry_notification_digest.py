# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from datetime import timedelta

from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.core.doctype.user.user import STANDARD_USERS
from frappe.utils import (
	format_time,
	formatdate,
	now_datetime,
	date_diff
)

class ResidencyExpiryNotificationDigest(Document):
	def __init__(self, *args, **kwargs):
		super(ResidencyExpiryNotificationDigest, self).__init__(*args, **kwargs)

		self.from_date, self.to_date = self.get_from_to_date()
		self.set_dates()
		self._accounts = {}
		self.currency = frappe.db.get_value('Company',  self.company,  "default_currency")

	@frappe.whitelist()
	def get_users(self):
		"""get list of users"""
		user_list = frappe.db.sql("""
		select name, enabled from tabUser
		where name not in ({})
		and user_type != "Website User"
		order by enabled desc, name asc""".format(", ".join(["%s"]*len(STANDARD_USERS))), STANDARD_USERS, as_dict=1)

		if self.recipient_list:
			recipient_list = self.recipient_list.split("\n")
		else:
			recipient_list = []
		for p in user_list:
			p["checked"] = p["name"] in recipient_list and 1 or 0

		frappe.response['user_list'] = user_list

	@frappe.whitelist()
	def send(self):
		# send email only to enabled users
		valid_users = [p[0] for p in frappe.db.sql("""select name from `tabUser`
		where enabled=1""")]

		if self.recipients:
			for row in self.recipients:
				msg_for_this_recipient = self.get_msg_html()
				if msg_for_this_recipient and row.recipient in valid_users:
					frappe.sendmail(
						recipients=row.recipient,
						subject=_("{0} Residency Expiry Notification Digest").format(self.frequency),
						message=msg_for_this_recipient,
						reference_doctype = self.doctype,
						reference_name = self.name,
						unsubscribe_message = _("Unsubscribe from this Residency Expiry Notification Digest")
					)

	def get_msg_html(self):
		"""Build digest content"""
		msg_content = get_employee_list()
		msg_header = self.set_title()
		return msg_header+msg_content

	def set_title(self):
		"""Set digest title"""
		title = _("Daily Reminder")
		subtitle = _("List of residency expiry notification for today")
		if self.frequency=="Weekly":
			title = _("Weekly Reminder")
			subtitle = _("List of residency expiry notification for the week")
		elif self.frequency=="Monthly":
			title = _("Monthly Reminder")
			subtitle = _("List of residency expiry notification for the month")
		return "<h3>{0}<h3><br/><h4>{1}</h4>".format(title, subtitle)

	def get_from_to_date(self):
		today = now_datetime().date()

		# decide from date based on digest frequency
		if self.frequency == "Daily":
			# from date, to_date is yesterday
			from_date = to_date = today - timedelta(days=1)
		elif self.frequency == "Weekly":
			# from date is the previous week's monday
			from_date = today - timedelta(days=today.weekday(), weeks=1)

			# to date is sunday i.e. the previous day
			to_date = from_date + timedelta(days=6)
		else:
			# from date is the 1st day of the previous month
			from_date = today - relativedelta(days=today.day-1, months=1)
			# to date is the last day of the previous month
			to_date = today - relativedelta(days=today.day)

		return from_date, to_date

	def set_dates(self):
		self.future_from_date, self.future_to_date = self.from_date, self.to_date

		# decide from date based on digest frequency
		if self.frequency == "Daily":
			self.past_from_date = self.past_to_date = self.future_from_date - relativedelta(days = 1)

		elif self.frequency == "Weekly":
			self.past_from_date = self.future_from_date - relativedelta(weeks=1)
			self.past_to_date = self.future_from_date - relativedelta(days=1)
		else:
			self.past_from_date = self.future_from_date - relativedelta(months=1)
			self.past_to_date = self.future_from_date - relativedelta(days=1)

	def get_next_sending(self):
		from_date, to_date = self.get_from_to_date()

		send_date = to_date + timedelta(days=1)

		if self.frequency == "Daily":
			next_send_date = send_date + timedelta(days=1)
		elif self.frequency == "Weekly":
			next_send_date = send_date + timedelta(weeks=1)
		else:
			next_send_date = send_date + relativedelta(months=1)
		self.next_send = formatdate(next_send_date) + " at midnight"

		return send_date

	def onload(self):
		self.get_next_sending()

def get_employee_list():
	today = now_datetime().date()
	employee_list = frappe.db.get_list('Employee', ['name', 'employee_name', 'residency_expiry_date'])
	message = "<ol>"
	for employee in employee_list:
		if date_diff(employee.residency_expiry_date, today) == -45:
			page_link = get_url("/desk#Form/Employee/"+employee.name)
			message = "<li><a href='{0}'>{1}</a></li>".format(page_link, employee.name+": "+employee.employee_name)
	message += "<ol>"
	return message

def send():
	now_date = now_datetime().date()

	for ed in frappe.db.sql("""select name from `tabResidency Expiry Notification Digest`
			where enabled=1 and docstatus<2""", as_list=1):
		ed_obj = frappe.get_doc('Residency Expiry Notification Digest', ed[0])
		if (now_date == ed_obj.get_next_sending()):
			ed_obj.send()

@frappe.whitelist()
def get_digest_msg(name):
	return frappe.get_doc("Residency Expiry Notification Digest", name).get_msg_html()
