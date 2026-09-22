"""WI-002449: a week's notice before a PAM Licence letter of guarantee expires.

Modelled on fleet_management.vehicle_branding_expiry, which does the same job for vehicle
branding - a daily sweep, a Notification Log so the bell shows it, and an email. The one
difference is the point of this story: who is told is configured in GRD Settings rather
than hard-coded, and more than one person can be told at once.
"""

import frappe
from frappe.utils import add_days, formatdate, get_url_to_form, today

from one_fm.processor import sendemail

# How much notice the story asks for.
NOTICE_DAYS = 7

# Where the recipients are configured. The first row is written to; everyone below is
# copied in, which is the order the table itself is in - Frappe keeps child rows by idx.
SETTINGS = "GRD Settings"
RECIPIENTS_FIELD = "lg_expiry_notification_recipients"


def notification_recipients():
	"""The configured recipients, in the order they were entered.

	Returns (to, cc). Administrator is dropped - it is nobody's mailbox, and sendemail
	strips it from `recipients` anyway but not from `cc`, which would leave a copy going
	nowhere.
	"""
	rows = frappe.get_all(
		"Action User",
		filters={"parenttype": SETTINGS, "parentfield": RECIPIENTS_FIELD},
		pluck="user",
		order_by="idx asc",
	)

	users, seen = [], set()
	for user in rows:
		if user and user != "Administrator" and user not in seen:
			seen.add(user)
			users.append(user)

	if not users:
		return None, []

	return users[0], users[1:]


def expiring_licenses(on_date=None):
	"""Licences whose letter of guarantee expires on the notice date.

	An exact date rather than a range, so one licence is announced once. The nightly job
	is what makes that safe: miss a day and that licence's notice is missed, which is the
	same bargain vehicle branding already takes.

	WI-002597 adds the second filter: not every PAM Licence has a letter of guarantee, and
	a licence whose LG Details box is unchecked is not one this job has anything to say
	about. Filtering here rather than in the caller keeps the two halves of the criterion
	together - a licence excluded from the notification is also a licence whose LG fields
	are hidden on the form.
	"""
	return frappe.get_all(
		"PAM License Details",
		filters={
			"lg_details_applicable": 1,
			"lg_expiry_date": on_date or add_days(today(), NOTICE_DAYS),
		},
		fields=[
			"name",
			"lg_number",
			"lg_expiry_date",
			"license_name",
			"civil_id_number_for_licensing",
			"issuing_authority",
		],
	)


def notify_lg_expiry():
	"""Daily: tell the GRD team which letters of guarantee expire in a week.

	Wrapped, like the job it is modelled on, so one unsendable licence does not stop the
	rest - and so a scheduler failure is a log entry rather than a silent gap.
	"""
	try:
		licenses = expiring_licenses()
		if not licenses:
			return

		to, cc = notification_recipients()
		if not to:
			frappe.log_error(
				title="LG Expiry Notification",
				message=(
					f"{len(licenses)} licence(s) have a letter of guarantee expiring in "
					f"{NOTICE_DAYS} days, but no recipients are configured in {SETTINGS}."
				),
			)
			return

		for license in licenses:
			send_lg_expiry_alert(license, to, cc)

	except Exception:
		frappe.log_error(title="LG Expiry Notification", message=frappe.get_traceback())


def send_lg_expiry_alert(license, to, cc):
	"""One licence, to one recipient with the rest copied in.

	The Notification Log is written for everybody, not only the recipient: a copied-in
	reader has the same reason to see it on the bell as the one addressed.
	"""
	subject = f"LG Expiry Warning: {license.lg_number or license.name}"

	message = frappe.render_template(
		"one_fm/templates/emails/lg_expiry_notification.html",
		context={
			"lg_number": license.lg_number or "",
			"lg_expiry_date": formatdate(license.lg_expiry_date),
			"license_name": license.license_name or license.name,
			"civil_id_number_for_licensing": license.civil_id_number_for_licensing or "",
			"issuing_authority": license.issuing_authority or "",
			"license_link": get_url_to_form("PAM License Details", license.name),
			"days_left": NOTICE_DAYS,
		},
	)

	for user in [to] + list(cc):
		frappe.get_doc({
			"doctype": "Notification Log",
			# "Alert" is the one type Frappe never emails - is_email_notifications_enabled_
			# for_type() returns False for it outright. Without that, Notification Log's
			# after_insert sends its own copy through the new_notification template, so
			# everybody got two emails for one licence and the one they opened was the
			# Notification Log's: addressed to them alone, with no Cc, whatever this job
			# passed. The bell still shows it; only the duplicate email is gone.
			"type": "Alert",
			"subject": subject,
			"email_content": message,
			"document_type": "PAM License Details",
			"document_name": license.name,
			"for_user": user,
		}).insert(ignore_permissions=True)

	sendemail(
		recipients=[to],
		cc=list(cc) or None,
		subject=subject,
		content=message,
		reference_doctype="PAM License Details",
		reference_name=license.name,
		# Without this Frappe writes "To: <!--recipient-->" and no Cc header at all
		# (email_body.make), personalising one copy per address - so a copied-in reader
		# gets the mail but it arrives looking as though it were addressed to them alone,
		# and the recipient cannot see who else was told. "header" writes the real To and
		# Cc, which is what makes the first row the recipient and the rest a copy.
		expose_recipients="header",
		is_scheduler_email=True,
	)

	frappe.db.commit()
