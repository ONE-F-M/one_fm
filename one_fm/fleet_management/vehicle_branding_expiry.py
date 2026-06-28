import frappe
from frappe.utils import add_days, today, formatdate
from frappe.utils.data import get_url_to_form
from one_fm.processor import sendemail


# Hardcoded recipient per business requirement
BRANDING_EXPIRY_RECIPIENT = "y.oyedele@one-fm.com"


def notify_vehicle_branding_expiry():
	"""Daily scheduled task: send email alert 30 days before branding expiration.

	Queries all Vehicle records whose custom_branding_registration_expiration_date
	is exactly 30 days from today, then sends a notification email to the
	designated recipient.
	"""
	try:
		target_date = add_days(today(), 30)

		vehicles = frappe.get_all(
			"Vehicle",
			filters={
				"custom_branding_registration_expiration_date": target_date,
			},
			fields=[
				"name",
				"license_plate",
				"make",
				"model",
				"custom_branding_application_date",
				"custom_branding_registration_issue_date",
				"custom_branding_registration_expiration_date",
			],
		)

		if not vehicles:
			return

		for vehicle in vehicles:
			send_branding_expiry_alert(vehicle)

	except Exception as e:
		frappe.log_error(message=str(e), title="Vehicle Branding Expiry Alert")


def send_branding_expiry_alert(vehicle):
	"""Send branding expiry email and create notification log for a single vehicle."""
	vehicle_link = get_url_to_form("Vehicle", vehicle.name)
	license_plate = vehicle.license_plate or vehicle.name

	context = {
		"license_plate": license_plate,
		"make": vehicle.make or "",
		"model": vehicle.model or "",
		"application_date": formatdate(vehicle.custom_branding_application_date) if vehicle.custom_branding_application_date else "",
		"issue_date": formatdate(vehicle.custom_branding_registration_issue_date) if vehicle.custom_branding_registration_issue_date else "",
		"expiration_date": formatdate(vehicle.custom_branding_registration_expiration_date),
		"vehicle_link": vehicle_link,
		"vehicle_name": vehicle.name,
	}

	subject = f"Vehicle Branding Expiration Warning: {license_plate}"
	msg = frappe.render_template(
		"one_fm/templates/emails/vehicle_branding_expiry.html",
		context=context,
	)

	# Create notification log
	frappe.get_doc({
		"doctype": "Notification Log",
		"subject": subject,
		"email_content": msg,
		"document_type": "Vehicle",
		"document_name": vehicle.name,
		"for_user": BRANDING_EXPIRY_RECIPIENT,
	}).insert(ignore_permissions=True)

	# Send email
	sendemail(
		recipients=[BRANDING_EXPIRY_RECIPIENT],
		subject=subject,
		content=msg,
		is_scheduler_email=True,
	)

	frappe.db.commit()
