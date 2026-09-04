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

# What the picker falls back to when an employee has no issued uniform on record. Groups
# rather than a fixed item list, so a new uniform item is offered the day it is created.
UNIFORM_ITEM_GROUPS = ("Uniform", "Cleaner Uniform", "Male & Female Semi Tactical Security Uniform Design")


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


def _decode(attachment: str) -> bytes:
	"""The image bytes, whether or not the caller left the data-URL prefix on.

	FileReader.readAsDataURL yields "data:image/jpeg;base64,...", and whether the prefix
	is stripped before sending depends on which helper the screen happens to use - the
	app has one of each. Decoding either shape here means the two repositories can ship
	without having to agree first.
	"""
	if "," in attachment[:64] and attachment.lstrip().startswith("data:"):
		attachment = attachment.split(",", 1)[1]
	return base64.b64decode(attachment)


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
			request, "attach_photo", stored_as, "", _decode(photo["attachment"]),
			is_private=True,
		)
		row.db_set("attach_photo", saved.file_url)


@frappe.whitelist()
def get_uniform_items() -> dict:
	"""The uniform items this employee can ask to have replaced.

	Their own issued uniform first: a replacement is for something they were given, so
	the list they choose from should be the list they hold. An employee with nothing on
	record - a new starter, or one whose issue predates the register - falls back to the
	uniform item groups rather than being shown an empty picker with no way forward.
	"""
	employee = frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
	)
	if not employee:
		return response(
			"Bad Request", 400, None,
			"No active employee record is linked to your user.",
		)

	items = _issued_uniform_items(employee) or _uniform_catalogue()

	return response("Success", 200, items, None)


def _issued_uniform_items(employee) -> list:
	"""What this employee was actually issued, most recent first, one row per item."""
	rows = frappe.db.sql(
		"""
		SELECT eui.item AS item_code, eui.item_name
		FROM `tabEmployee Uniform Item` eui
		JOIN `tabEmployee Uniform` eu ON eu.name = eui.parent
		WHERE eu.employee = %(employee)s
		  AND eu.type = 'Issue'
		  AND eu.docstatus = 1
		  AND eui.item IS NOT NULL
		ORDER BY eu.issued_on DESC
		""",
		{"employee": employee},
		as_dict=True,
	)

	seen, items = set(), []
	for row in rows:
		if row.item_code in seen:
			continue
		seen.add(row.item_code)
		items.append({"item_code": row.item_code, "item_name": row.item_name or row.item_code})
	return items


def _uniform_catalogue() -> list:
	return [
		{"item_code": row.name, "item_name": row.item_name or row.name}
		for row in frappe.get_all(
			"Item",
			filters={"item_group": ["in", UNIFORM_ITEM_GROUPS], "disabled": 0},
			fields=["name", "item_name"],
			order_by="item_name asc",
		)
	]
