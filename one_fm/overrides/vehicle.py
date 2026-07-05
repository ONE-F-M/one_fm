import frappe
from frappe import _
from frappe.utils import getdate


def validate_vehicle_branding(doc, method):
	"""Validate branding details on Vehicle save."""
	validate_branding_expiration_dates(doc)
	validate_branding_image_required(doc)


def validate_branding_expiration_dates(doc):
	"""Ensure expiration date is later than both application date and issue date."""
	expiration_date = doc.custom_branding_registration_expiration_date
	if not expiration_date:
		return

	expiration = getdate(expiration_date)

	application_date = doc.custom_branding_application_date
	if application_date and getdate(application_date) >= expiration:
		frappe.throw(
			_("Branding Registration Expiration Date must be later than Branding Application Date.")
		)

	issue_date = doc.custom_branding_registration_issue_date
	if issue_date and getdate(issue_date) >= expiration:
		frappe.throw(
			_("Branding Registration Expiration Date must be later than Branding Registration Issue Date.")
		)


def validate_branding_image_required(doc):
	"""Require branding image when branding registration issue date is set."""
	if doc.custom_branding_registration_issue_date and not doc.custom_branding_image:
		frappe.throw(
			_("Branding Image is required when Branding Registration Issue Date is set.")
		)
