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
			# WI-001781: the OUT movement's assignment closes on `checked_out`, but
			# set_value does not save that document, so its assignment rule is never
			# re-evaluated and the supervisor's ToDo would stay open forever. Same
			# reasoning as reapply_leave_application_assignment_rules below.
			self.reapply_own_assignment_rules(self.checkin_reference)

		if self.type == "OUT":
			self.handle_checkout_notification()

		if self.type == "OUT" and self.leave_application:
			self.reapply_leave_application_assignment_rules()

		if self.type == "IN":
			self.handle_checkin_notification()

	def on_cancel(self):
		if self.type == "IN" and self.checkin_reference:
			frappe.db.set_value("Accommodation Leave Movement", self.checkin_reference, "checked_out", 0)

		if self.type == "OUT" and self.leave_application:
			self.reapply_leave_application_assignment_rules()

	def reapply_own_assignment_rules(self, name):
		"""Re-evaluate the assignment rules on another movement of this doctype.

		Assignment rules only fire on their own document's save, so a flag written
		with set_value leaves the rule unaware and the assignment open.
		"""
		from frappe.automation.doctype.assignment_rule.assignment_rule import apply

		try:
			apply(doctype=self.doctype, name=name)
		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title="Error Reapplying Assignment Rules for Accommodation Leave Movement",
			)

	def reapply_leave_application_assignment_rules(self):
		"""Set accommodation checkout flag and re-evaluate assignment rules.

		Assignment rules only fire on the target document's own save/update events.
		When an Accommodation Leave Movement is submitted or cancelled, the Leave
		Application is not saved, so its unassign_condition is never checked.

		This method:
		1. Sets/clears the custom_accommodation_checked_out flag on the Leave Application
		2. Explicitly calls the assignment rule engine to evaluate unassign/assign conditions
		"""
		from frappe.automation.doctype.assignment_rule.assignment_rule import apply

		try:
			checked_out = 1 if self.docstatus == 1 else 0
			frappe.db.set_value(
				"Leave Application",
				self.leave_application,
				"custom_accommodation_checked_out",
				checked_out,
			)
			apply(doctype="Leave Application", name=self.leave_application)
		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title="Error Reapplying Assignment Rules for Leave Application",
			)

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

	def handle_checkin_notification(self):
		"""
		On submission of an IN record:
		- Get the leave_application from the linked OUT (checkin_reference).
		- Check the leave's resumption_date against today.
		- If resumption_date <= today: send notification immediately.
		- If resumption_date > today (early check-in): flag for deferred notification.
		"""
		if not self.checkin_reference:
			return

		leave_application = frappe.db.get_value(
			"Accommodation Leave Movement", self.checkin_reference, "leave_application"
		)

		if not leave_application:
			return

		resumption_date = frappe.db.get_value(
			"Leave Application", leave_application, "resumption_date"
		)

		if not resumption_date:
			return

		if getdate(resumption_date) <= getdate(today()):
			# Leave has ended (resumption date reached) — send notification immediately
			send_alm_checkin_notification(self.name)
		else:
			# Early check-in — defer notification to scheduler
			self.db_set("custom_notify_on_leave_end", 1)


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


def send_alm_checkin_notification(alm_name):
	"""
	Sends an email notification when an ALM (IN) triggers an employee
	status change to Active (via the daily scheduler).

	The email is sent to users listed in the HR Settings >
	Employee Status Update Notification Email table.
	"""
	try:
		alm = frappe.get_doc("Accommodation Leave Movement", alm_name)
		employee = frappe.get_doc("Employee", alm.employee)

		recipients = get_alm_notification_recipients()
		if not recipients:
			frappe.log_error(
				title=_("ALM Check-In Notification - No Recipients"),
				message=_("No notification members found in HR Settings > Employee Status Update "
					"Notification Email. Please add users to the Notification Members table.")
			)
			return

		# Get the leave application from the linked OUT record
		leave_application = ""
		if alm.checkin_reference:
			leave_application = frappe.db.get_value(
				"Accommodation Leave Movement", alm.checkin_reference, "leave_application"
			) or ""

		employee_url = get_url_to_form("Employee", employee.name)

		context = {
			"employee_id": employee.name,
			"employee_name": employee.employee_name,
			"status": employee.status,
			"department": employee.department,
			"designation": employee.designation,
			"leave_application": leave_application,
			"checkin_date_time": alm.checkin_checkout_date_time,
			"employee_url": employee_url,
		}

		message = frappe.render_template(
			"one_fm/templates/emails/accommodation_leave_movement_checkin.html",
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
			title=_("ALM Check-In Notification Error"),
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

	Contiguous leave handling:
	- Resolves the full contiguous leave chain from the OUT record's leave.
	- If the current date is within or after the last contiguous leave, the IN
	  record's leave_application is set to that latest leave.
	- If the employee returns early (before contiguous leaves start), the IN
	  record's leave_application stays bound to the original leave, and a
	  warning flag is returned so the client can display a message.
	"""
	if has_linked_checkin(source_name):
		frappe.throw(_("A linked check-in already exists for this check-out."))

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

	# --- Contiguous leave chain resolution ---
	original_leave = target_doc.leave_application
	if original_leave and frappe.db.exists("Leave Application", original_leave):
		latest_leave = get_latest_contiguous_leave(target_doc.employee, original_leave)

		if latest_leave != original_leave:
			# A contiguous chain exists. Determine if this is an early check-in.
			original_leave_data = frappe.db.get_value(
				"Leave Application", original_leave,
				["to_date", "resumption_date"], as_dict=True
			)
			current_date = getdate(today())

			if original_leave_data and current_date <= getdate(original_leave_data.to_date):
				# Early check-in: employee returned during the original leave period.
				# Keep leave_application bound to original leave; flag warning.
				target_doc.leave_application = original_leave

				# Fetch the next contiguous leave name for the warning message
				next_leave = _get_next_contiguous_leave(original_leave)
				target_doc._early_checkin_warning = _(
					"Note: Employee checked in before the start of contiguous leave ({0}). "
					"A new Check-Out record will be required when that leave begins."
				).format(next_leave)
			else:
				# Normal scenario: bind to the latest contiguous leave
				target_doc.leave_application = latest_leave
		# else: no contiguous chain — keep original leave_application

	return target_doc


def get_latest_contiguous_leave(employee: str, leave_application: str) -> str:
	"""
	Walk forward through the contiguous leave chain starting from the given
	leave application and return the name of the last leave in the chain.

	Contiguity is defined strictly:
	  next_leave.from_date == current_leave.resumption_date

	Only approved (docstatus=1) leaves for the same employee are considered.
	Cancelled leaves (docstatus=2) break the chain.

	Args:
		employee: Employee ID
		leave_application: Starting Leave Application name

	Returns:
		Name of the latest contiguous Leave Application (may be the same as
		the input if no contiguous leaves exist).
	"""
	if not employee or not leave_application:
		return leave_application

	LeaveApp = frappe.qb.DocType("Leave Application")
	current_leave = leave_application

	# Safety limit to prevent infinite loops in case of data issues
	max_iterations = 50
	iteration = 0

	while iteration < max_iterations:
		iteration += 1

		# Get the resumption_date of the current leave
		resumption_date = frappe.db.get_value(
			"Leave Application", current_leave, "resumption_date"
		)

		if not resumption_date:
			break

		# Look for the next contiguous leave: from_date == resumption_date
		next_leave = (
			frappe.qb.from_(LeaveApp)
			.select(LeaveApp.name)
			.where(LeaveApp.employee == employee)
			.where(LeaveApp.from_date == getdate(resumption_date))
			.where(LeaveApp.docstatus == 1)
			.where(LeaveApp.name != current_leave)
			.limit(1)
		).run(as_dict=True)

		if not next_leave:
			break

		current_leave = next_leave[0].name

	return current_leave


def _get_next_contiguous_leave(leave_application: str) -> str:
	"""
	Return the name of the immediately next contiguous leave after the given
	leave application, or an empty string if none exists.

	Used internally for building early check-in warning messages.
	"""
	leave_data = frappe.db.get_value(
		"Leave Application", leave_application,
		["employee", "resumption_date"], as_dict=True
	)

	if not leave_data or not leave_data.resumption_date:
		return ""

	LeaveApp = frappe.qb.DocType("Leave Application")
	next_leave = (
		frappe.qb.from_(LeaveApp)
		.select(LeaveApp.name)
		.where(LeaveApp.employee == leave_data.employee)
		.where(LeaveApp.from_date == getdate(leave_data.resumption_date))
		.where(LeaveApp.docstatus == 1)
		.where(LeaveApp.name != leave_application)
		.limit(1)
	).run(as_dict=True)

	return next_leave[0].name if next_leave else ""


@frappe.whitelist()
def has_active_checkout_for_contiguous_chain(employee: str, leave_application: str) -> bool:
	"""
	Check whether an active (un-returned) ALM OUT record exists for any leave
	in the contiguous chain that includes the given leave application.

	Walks backward from the given leave to find the start of the chain, then
	walks forward checking each leave for a submitted OUT record that has not
	been returned (checked_out == 0).

	Args:
		employee: Employee ID
		leave_application: Leave Application name to check

	Returns:
		True if an active OUT exists anywhere in the chain, False otherwise.
	"""
	if not employee or not leave_application:
		return False

	# Step 1: Walk backward to find the first leave in the chain
	chain_start = _find_chain_start(employee, leave_application)

	# Step 2: Walk forward through the entire chain, checking for active OUTs
	LeaveApp = frappe.qb.DocType("Leave Application")
	ALM = frappe.qb.DocType("Accommodation Leave Movement")

	current_leave = chain_start
	max_iterations = 50
	iteration = 0

	while iteration < max_iterations:
		iteration += 1

		# Check if this leave has a submitted, un-returned OUT record
		active_out = (
			frappe.qb.from_(ALM)
			.select(ALM.name)
			.where(ALM.leave_application == current_leave)
			.where(ALM.type == "OUT")
			.where(ALM.docstatus == 1)
			.where(ALM.checked_out == 0)
			.limit(1)
		).run(as_dict=True)

		if active_out:
			return True

		# Move to the next contiguous leave
		resumption_date = frappe.db.get_value(
			"Leave Application", current_leave, "resumption_date"
		)

		if not resumption_date:
			break

		next_leave = (
			frappe.qb.from_(LeaveApp)
			.select(LeaveApp.name)
			.where(LeaveApp.employee == employee)
			.where(LeaveApp.from_date == getdate(resumption_date))
			.where(LeaveApp.docstatus == 1)
			.where(LeaveApp.name != current_leave)
			.limit(1)
		).run(as_dict=True)

		if not next_leave:
			break

		current_leave = next_leave[0].name

	return False


def _find_chain_start(employee: str, leave_application: str) -> str:
	"""
	Walk backward through the contiguous chain to find the first leave.

	A leave L_prev is the predecessor of L_current if:
	  L_prev.resumption_date == L_current.from_date

	Args:
		employee: Employee ID
		leave_application: Starting Leave Application name

	Returns:
		Name of the first Leave Application in the contiguous chain.
	"""
	LeaveApp = frappe.qb.DocType("Leave Application")
	current_leave = leave_application
	max_iterations = 50
	iteration = 0

	while iteration < max_iterations:
		iteration += 1

		from_date = frappe.db.get_value(
			"Leave Application", current_leave, "from_date"
		)

		if not from_date:
			break

		# Look for a predecessor whose resumption_date == current from_date
		prev_leave = (
			frappe.qb.from_(LeaveApp)
			.select(LeaveApp.name)
			.where(LeaveApp.employee == employee)
			.where(LeaveApp.resumption_date == getdate(from_date))
			.where(LeaveApp.docstatus == 1)
			.where(LeaveApp.name != current_leave)
			.limit(1)
		).run(as_dict=True)

		if not prev_leave:
			break

		current_leave = prev_leave[0].name

	return current_leave


@frappe.whitelist()
def get_checkin_leave_application(checkout_name: str) -> dict:
	"""
	Preview which Leave Application will be auto-populated on a new IN record
	created from the given OUT record.

	Returns a dict with:
	- leave_application: the resolved leave name
	- is_early_checkin: True if the employee is returning early
	- warning: warning message for early check-in, or empty string
	"""
	if not checkout_name:
		return {"leave_application": "", "is_early_checkin": False, "warning": ""}

	out_data = frappe.db.get_value(
		"Accommodation Leave Movement", checkout_name,
		["employee", "leave_application"], as_dict=True
	)

	if not out_data or not out_data.leave_application:
		return {"leave_application": "", "is_early_checkin": False, "warning": ""}

	employee = out_data.employee
	original_leave = out_data.leave_application

	if not frappe.db.exists("Leave Application", original_leave):
		return {"leave_application": original_leave, "is_early_checkin": False, "warning": ""}

	latest_leave = get_latest_contiguous_leave(employee, original_leave)

	if latest_leave != original_leave:
		original_leave_data = frappe.db.get_value(
			"Leave Application", original_leave,
			["to_date"], as_dict=True
		)
		current_date = getdate(today())

		if original_leave_data and current_date <= getdate(original_leave_data.to_date):
			next_leave = _get_next_contiguous_leave(original_leave)
			return {
				"leave_application": original_leave,
				"is_early_checkin": True,
				"warning": _(
					"Note: Employee checked in before the start of contiguous leave ({0}). "
					"A new Check-Out record will be required when that leave begins."
				).format(next_leave),
			}

		return {"leave_application": latest_leave, "is_early_checkin": False, "warning": ""}

	return {"leave_application": original_leave, "is_early_checkin": False, "warning": ""}
