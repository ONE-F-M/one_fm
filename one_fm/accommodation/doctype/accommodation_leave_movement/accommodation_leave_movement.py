# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import getdate, now_datetime, get_datetime, get_url_to_form, today

class AccommodationLeaveMovement(Document):
	def autoname(self):
		if self.type == "OUT":
			self.naming_series = "HR-ALM-OUT-.YYYY.-"
		else:
			self.naming_series = "HR-ALM-IN-.YYYY.-"
		
		from frappe.model.naming import make_autoname
		self.name = make_autoname(self.naming_series)

	def validate(self):
		self.validate_checkout_date_time()

	def validate_checkout_date_time(self):
		if self.type == "OUT" and self.checkin_checkout_date_time:
			if get_datetime(self.checkin_checkout_date_time) > now_datetime():
				frappe.throw(_("Checkout Date and Time cannot be in the future."))

	def on_submit(self):
		if self.type == "IN" and self.checkin_reference:
			frappe.db.set_value("Accommodation Leave Movement", self.checkin_reference, "checked_out", 1)

		if self.type == "OUT":
			self.handle_checkout_notification()

	def on_cancel(self):
		if self.type == "IN" and self.checkin_reference:
			frappe.db.set_value("Accommodation Leave Movement", self.checkin_reference, "checked_out", 0)

	def handle_checkout_notification(self):
		"""
		On submission of an OUT record:
		- If the linked leave has already started (from_date <= today), send email immediately.
		- If the leave hasn't started yet, flag for notification via daily scheduler.
		"""
		if not self.leave_application:
			return

		leave_from_date = frappe.db.get_value(
			"Leave Application", self.leave_application, "from_date"
		)

		if not leave_from_date:
			return

		if getdate(leave_from_date) <= getdate(today()):
			# Leave has started — send notification immediately
			send_alm_checkout_notification(self.name)
		else:
			# Leave hasn't started yet — flag for daily scheduler
			self.db_set("custom_notify_on_leave_start", 1)


def get_alm_notification_recipients():
	"""
	Returns a list of email addresses from the 'Employee Status Update Notification Email'
	table in HR Settings.
	"""
	recipients = []
	hr_settings = frappe.get_cached_doc("HR Settings")
	for member in hr_settings.get("employee_status_update_notification_members", []):
		if member.user:
			recipients.append(member.user)
	return recipients


def send_alm_checkout_notification(alm_name):
	"""
	Sends an email notification when an ALM (OUT) triggers an employee
	status change to Vacation (via the daily scheduler).

	The email is sent to users listed in the ALM's Notification Members table
	with Employee details and ALM checkout information.
	"""
	try:
		alm = frappe.get_doc("Accommodation Leave Movement", alm_name)
		employee = frappe.get_doc("Employee", alm.employee)

		recipients = get_alm_notification_recipients()
		if not recipients:
			frappe.log_error(
				title=_("ALM Checkout Notification - No Recipients"),
				message=_("No notification members found in HR Settings > Employee Status Update "
					"Notification Email. Please add users to the Notification Members table.")
			)
			return

		employee_url = get_url_to_form("Employee", employee.name)

		context = {
			"employee_id": employee.name,
			"employee_name": employee.employee_name,
			"status": employee.status,
			"department": employee.department,
			"designation": employee.designation,
			"leave_application": alm.leave_application or "",
			"checkout_date_time": alm.checkin_checkout_date_time,
			"employee_url": employee_url,
		}

		message = frappe.render_template(
			"one_fm/templates/emails/accommodation_leave_movement_checkout.html",
			context
		)

		subject = _("Employee Status Update: {0} - {1} is now {2}").format(
			employee.name, employee.employee_name, employee.status
		)

		from one_fm.processor import sendemail
		sendemail(
			recipients=recipients,
			subject=subject,
			header=[_("Employee Status Update")],
			message=message,
		)

	except Exception:
		frappe.log_error(
			title=_("ALM Checkout Notification Error"),
			message=frappe.get_traceback()
		)


@frappe.whitelist()
def get_last_active_checkin(employee: str):
	"""
	Fetches the most recent active check-in for an employee from 'Accommodation Checkin Checkout'.
	Active check-in is defined as type 'IN' and 'checked_out' is 0.
	"""
	if not employee:
		return None
	
	checkins = frappe.get_all("Accommodation Checkin Checkout",
		filters={
			"employee": employee,
			"type": "IN",
			"checked_out": 0
		},
		fields=["bed", "accommodation", "floor", "accommodation_unit", "accommodation_space"],
		order_by="checkin_checkout_date_time desc, creation desc",
		limit=1
	)
	
	return checkins[0] if checkins else None

@frappe.whitelist()
def has_linked_checkin(checkout_name: str) -> bool:
	"""
	Returns True if a non-cancelled IN record already exists that is linked to
	the given OUT document via the checkin_reference field.

	Used by the client script to decide whether to render the "Create > Check In"
	button.  The check covers Draft (docstatus=0) and Submitted (docstatus=1)
	records so that the button is hidden as soon as the IN record is created,
	not only after it is submitted.
	"""
	if not checkout_name:
		return False

	AlmDoctype = frappe.qb.DocType("Accommodation Leave Movement")
	result = (
		frappe.qb.from_(AlmDoctype)
		.select(AlmDoctype.name)
		.where(AlmDoctype.checkin_reference == checkout_name)
		.where(AlmDoctype.type == "IN")
		.where(AlmDoctype.docstatus != 2)  # exclude cancelled records
		.limit(1)
	).run(as_dict=True)

	return bool(result)


@frappe.whitelist()
def make_checkin_from_checkout(source_name: str):
	"""
	Maps fields from an 'OUT' Accommodation Leave Movement to a new 'IN' one.
	"""
	if has_linked_checkin(source_name):
		frappe.throw(frappe._("A linked check-in already exists for this check-out."))

	target_doc = get_mapped_doc(
		"Accommodation Leave Movement",
		source_name,
		{
			"Accommodation Leave Movement": {
				"doctype": "Accommodation Leave Movement",
				"validation": {
					"docstatus": ["=", 1],
					"type": ["=", "OUT"]
				}
			}
		},
		ignore_permissions=False,
	)
	
	target_doc.type = "IN"
	target_doc.checkin_reference = source_name
	target_doc.checkin_checkout_date_time = frappe.utils.now_datetime()
	
	return target_doc
