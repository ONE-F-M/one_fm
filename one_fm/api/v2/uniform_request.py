"""WI-002301: the endpoint the mobile Uniform Request form submits to.

An employee reports a damaged uniform item: what it is, what size, and a photo of the
damage. Everything else about the resulting Request for Material - who it is for, what
department they are in, how many of the item, who approves it - the employee should not
have to type, so none of it is asked for.
"""

import base64
import datetime
import hashlib

import frappe
from frappe import _

from one_fm.api.api import upload_file
from one_fm.api.v1.utils import response

# The request type a uniform replacement is raised as, and the state it goes straight to:
# an employee is not filing a draft for themselves to approve later.
INDIVIDUAL = "Individual"
PENDING_APPROVAL = "Pending Approval"

# One of each. The employee is replacing a damaged item, not ordering stock, so the form
# never asks and the row carries the only quantity that makes sense.
UNIFORM_QTY = 1


@frappe.whitelist()
def create_uniform_request(items=None, schedule_date: str = None) -> dict:
	"""Raise a uniform replacement request for the session user.

	Args:
	    items: list of {item_code, size, attach_photo, requested_description?}.
	           Accepts a JSON string, which is what the app posts.
	    schedule_date: when the employee needs it. Optional - the request can be started
	           without it, and it is asked for before the request goes for approval.

	Returns:
	    dict: message, status_code, data (the created request), error.
	"""
	items = frappe.parse_json(items) if isinstance(items, str) else items

	if not items:
		return response("Bad Request", 400, None, "At least one uniform item is required.")

	employee = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user, "status": "Active"},
		["name", "employee_name", "department"],
		as_dict=True,
	)
	if not employee:
		return response(
			"Bad Request", 400, None,
			"No active employee record is linked to your user, so the request has nobody "
			"to be raised for.",
		)

	missing = _missing_details(items)
	if missing:
		return response("Bad Request", 400, None, missing)

	try:
		request = _build_request(employee, items, schedule_date)
	except frappe.ValidationError as error:
		return response("Bad Request", 400, None, str(error))
	except Exception:
		frappe.log_error(
			title="Could not create a uniform Request for Material",
			message=frappe.get_traceback(),
		)
		return response("Internal Server Error", 500, None, "Could not create the request.")

	return response("Success", 201, request.as_dict(), None)


def _missing_details(items) -> str:
	"""Say which row is short of what, rather than refusing the whole form blankly."""
	for index, item in enumerate(items, start=1):
		if not item.get("item_code"):
			return f"Row {index}: choose the uniform item."
		if not item.get("size"):
			return f"Row {index}: the size of the uniform item is required."
		if not _photo_of(item):
			return f"Row {index}: a photo of the damaged uniform is required."
	return ""


def _photo_of(item):
	"""The photo on a row, however the caller sent it.

	The app captures the damage and posts it as {attachment_name, attachment} with the
	bytes base64-encoded - the same shape the leave application takes - so there is no
	file on the server until this request is saved. A caller that already has a file may
	pass its url as a plain string instead.
	"""
	photo = item.get("attach_photo")
	if isinstance(photo, str):
		return photo.strip()
	if isinstance(photo, dict):
		return photo.get("attachment") and photo.get("attachment_name")
	return None


def _build_request(employee, items, schedule_date):
	"""The Request for Material a uniform submission becomes.

	The approver is not set here: Request for Material already resolves it from the
	employee's Reports To, falling back to the Site Supervisor of their allocated site,
	and duplicating that rule would leave two versions of it to disagree.
	"""
	request = frappe.new_doc("Request for Material")
	request.type = INDIVIDUAL
	request.employee = employee.name
	request.employee_name = employee.employee_name
	request.department = employee.department
	request.requested_by = frappe.session.user
	request.transaction_date = frappe.utils.today()
	if schedule_date:
		request.schedule_date = schedule_date

	for item in items:
		photo = item.get("attach_photo")
		request.append("items", {
			"item_code": item.get("item_code"),
			"requested_item_name": item.get("item_name"),
			"requested_description": item.get("requested_description"),
			"size": item.get("size"),
			# A url the caller already had can be set now; bytes have nowhere to live
			# until the request exists, so those rows are filled in after the insert.
			"attach_photo": photo if isinstance(photo, str) else None,
			"is_uniform_request": 1,
			"qty": UNIFORM_QTY,
		})

	# The size and photo checks run on validate, and a row whose photo is still bytes has
	# nothing in the field yet - so the rows are saved first and the photos attached
	# before the request is validated again on its way to the approver.
	request.flags.ignore_validate = True
	request.insert(ignore_permissions=True)

	_attach_photos(request, items)

	# Straight to the supervisor. Saved first so the approver is resolved against a
	# request that exists, and set with db_set so the state change cannot be undone by a
	# later validation on a document that has already been created.
	request.db_set("workflow_state", PENDING_APPROVAL)
	request.reload()

	return request


def _attach_photos(request, items):
	"""Store each row's photo and point the row at it.

	Written straight to the row with db_set: the request has already been created, and
	re-saving the whole document here would run the very validation the photos are being
	added to satisfy.
	"""
	for row, item in zip(request.items, items):
		photo = item.get("attach_photo")
		if not isinstance(photo, dict):
			continue

		name = photo.get("attachment_name") or "uniform.jpg"
		extension = "." + name.split(".")[-1] if "." in name else ".jpg"
		stored_as = hashlib.md5(
			(name + str(datetime.datetime.now())).encode("utf-8")
		).hexdigest() + extension

		saved = upload_file(
			request, "attach_photo", stored_as, "", base64.b64decode(photo["attachment"]),
			is_private=True,
		)
		row.db_set("attach_photo", saved.file_url)
