import frappe
from frappe import _
from frappe.utils import now_datetime, getdate


# ---------------------------------------------------------------------------
# Transit Log Creation Utilities
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_transit_log_from_po(po_name: str) -> str:
	"""Create a Transit Log from a submitted Purchase Order.

	Used both by the auto-creation on PO submit (Story 2) and by the
	manual "Create Transit Log" button on the PO form.

	Returns the name of the newly created Transit Log.
	"""
	frappe.has_permission("Purchase Order", "read", throw=True)

	po = frappe.get_doc("Purchase Order", po_name)
	po.check_permission("read")

	if po.docstatus != 1:
		frappe.throw(_("Purchase Order {0} must be submitted before creating a Transit Log.").format(po_name))

	# Prevent duplicate Transit Logs for the same PO
	existing = frappe.db.exists("Transit Log", {
		"reference_doctype": "Purchase Order",
		"reference_name": po_name
	})
	if existing:
		frappe.throw(_("A Transit Log {0} already exists for this Purchase Order.").format(existing))

	transit_log = frappe.new_doc("Transit Log")
	transit_log.reference_doctype = "Purchase Order"
	transit_log.reference_name = po_name
	transit_log.purpose = po.custom_purpose or ""
	transit_log.courier = po.supplier
	transit_log.status = "Pending"
	transit_log.api_sync_status = "Not Started"

	for item in po.items:
		transit_log.append("transit_item_details", {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"quantity": item.qty
		})

	transit_log.insert(ignore_permissions=True)

	frappe.msgprint(
		_("Transit Log {0} created successfully.").format(
			frappe.utils.get_link_to_form("Transit Log", transit_log.name)
		),
		alert=True,
		indicator="green"
	)

	return transit_log.name


@frappe.whitelist()
def create_transit_log_from_rfm(rfm_name: str) -> str:
	"""Create a Transit Log from an approved Request for Material (Story 4).

	Only applicable when RFM purpose = 'Sample Stock Receipt' and items
	have item_code populated.

	Returns the name of the newly created Transit Log.
	"""
	frappe.has_permission("Request for Material", "read", throw=True)

	rfm = frappe.get_doc("Request for Material", rfm_name)
	rfm.check_permission("read")

	if rfm.docstatus != 1:
		frappe.throw(_("Request for Material {0} must be submitted before creating a Transit Log.").format(rfm_name))

	if rfm.purpose != "Sample Stock Receipt":
		frappe.throw(_("Transit Log can only be created for RFMs with purpose 'Sample Stock Receipt'."))

	# Prevent duplicate Transit Logs for the same RFM
	existing = frappe.db.exists("Transit Log", {
		"reference_doctype": "Request for Material",
		"reference_name": rfm_name
	})
	if existing:
		frappe.throw(_("A Transit Log {0} already exists for this Request for Material.").format(existing))

	# Only include items that have an item_code
	items_with_code = [item for item in rfm.items if item.item_code]
	if not items_with_code:
		frappe.throw(_("No items with Item Code found in this Request for Material."))

	transit_log = frappe.new_doc("Transit Log")
	transit_log.reference_doctype = "Request for Material"
	transit_log.reference_name = rfm_name
	transit_log.purpose = rfm.purpose
	transit_log.status = "Pending"
	transit_log.api_sync_status = "Not Started"

	for item in items_with_code:
		transit_log.append("transit_item_details", {
			"item_code": item.item_code,
			"item_name": item.item_name or item.requested_item_name,
			"quantity": item.qty
		})

	transit_log.insert(ignore_permissions=True)

	frappe.msgprint(
		_("Transit Log {0} created successfully.").format(
			frappe.utils.get_link_to_form("Transit Log", transit_log.name)
		),
		alert=True,
		indicator="green"
	)

	return transit_log.name


# ---------------------------------------------------------------------------
# Backtracking Utilities (Story 3 & 4)
# ---------------------------------------------------------------------------

def update_transit_log_from_purchase_receipt(doc, method):
	"""Hook: on_submit of Purchase Receipt.

	Finds Transit Logs linked to the parent Purchase Order(s) of this
	Purchase Receipt and marks them as 'Completed' when all items have
	been fully received.
	"""
	# Collect unique PO names from the PR items
	po_names = set()
	for item in doc.items:
		if item.purchase_order:
			po_names.add(item.purchase_order)

	if not po_names:
		return

	for po_name in po_names:
		_check_and_complete_transit_log(
			reference_doctype="Purchase Order",
			reference_name=po_name
		)


def update_transit_log_from_stock_entry(doc, method):
	"""Hook: on_submit of Stock Entry.

	For Stock Entries of type 'Sample Stock Receipt', finds Transit Logs
	linked to the parent Request for Material and marks them as 'Completed'
	when all items have been fully received.
	"""
	if doc.stock_entry_type != "Sample Stock Receipt":
		return

	rfm_name = doc.one_fm_request_for_material
	if not rfm_name:
		return

	_check_and_complete_transit_log(
		reference_doctype="Request for Material",
		reference_name=rfm_name
	)


def _check_and_complete_transit_log(reference_doctype: str, reference_name: str):
	"""Core backtracking logic: compare received quantities against Transit
	Log item quantities and set status to 'Completed' if all items are
	fulfilled.
	"""
	transit_logs = frappe.get_list(
		"Transit Log",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"status": "Pending"
		},
		fields=["name"]
	)

	if not transit_logs:
		return

	# Build received quantity map based on reference type
	received_map = _get_received_quantities(reference_doctype, reference_name)

	for tl in transit_logs:
		transit_log = frappe.get_doc("Transit Log", tl.name)
		all_fulfilled = True

		for item in transit_log.transit_item_details:
			received_qty = received_map.get(item.item_code, 0)
			if received_qty < item.quantity:
				all_fulfilled = False
				break

		if all_fulfilled:
			frappe.db.set_value("Transit Log", tl.name, "status", "Completed")
			frappe.db.set_value("Transit Log", tl.name, "transit_status", "Delivered")


def _get_received_quantities(reference_doctype: str, reference_name: str) -> dict:
	"""Returns a dict of {item_code: total_received_qty} for the given
	reference document.
	"""
	received_map = {}

	if reference_doctype == "Purchase Order":
		# Sum quantities from all submitted Purchase Receipts for this PO
		from frappe.query_builder import DocType
		from frappe.query_builder.functions import Sum

		PRItem = DocType("Purchase Receipt Item")
		PR = DocType("Purchase Receipt")

		result = (
			frappe.qb.from_(PRItem)
			.join(PR).on(PRItem.parent == PR.name)
			.select(
				PRItem.item_code,
				Sum(PRItem.qty).as_("total_qty")
			)
			.where(PRItem.purchase_order == reference_name)
			.where(PR.docstatus == 1)
			.groupby(PRItem.item_code)
		).run(as_dict=True)

		for row in result:
			received_map[row.item_code] = row.total_qty

	elif reference_doctype == "Request for Material":
		# Sum quantities from all submitted Stock Entries of type
		# 'Sample Stock Receipt' linked to this RFM
		from frappe.query_builder import DocType
		from frappe.query_builder.functions import Sum

		SEDetail = DocType("Stock Entry Detail")
		SE = DocType("Stock Entry")

		result = (
			frappe.qb.from_(SEDetail)
			.join(SE).on(SEDetail.parent == SE.name)
			.select(
				SEDetail.item_code,
				Sum(SEDetail.qty).as_("total_qty")
			)
			.where(SE.one_fm_request_for_material == reference_name)
			.where(SE.stock_entry_type == "Sample Stock Receipt")
			.where(SE.docstatus == 1)
			.groupby(SEDetail.item_code)
		).run(as_dict=True)

		for row in result:
			received_map[row.item_code] = row.total_qty

	return received_map


# ---------------------------------------------------------------------------
# Courier API Sync — 12-hour Cron Job (Story 2)
# ---------------------------------------------------------------------------

def sync_transit_log_status():
	"""Scheduled job (every 12 hours): sync transit statuses from courier
	APIs for all Pending Transit Logs that have a tracking number and a
	courier with a configured API provider.
	"""
	transit_logs = frappe.get_list(
		"Transit Log",
		filters={
			"status": "Pending",
			"tracking_number": ["is", "set"],
			"courier": ["is", "set"]
		},
		fields=["name", "tracking_number", "courier"]
	)

	for tl in transit_logs:
		frappe.enqueue(
			"one_fm.one_fm.doctype.transit_log.transit_log_utils.process_single_transit_log_sync",
			queue="short",
			timeout=300,
			tl=tl
		)


def process_single_transit_log_sync(tl):
	"""Background job wrapper to sync a single Transit Log."""
	if isinstance(tl, dict):
		tl = frappe._dict(tl)

	try:
		_sync_single_transit_log(tl)
	except Exception:
		frappe.log_error(
			title=_("Transit Log API Sync Failed: {0}").format(tl.name),
			message=frappe.get_traceback()
		)
		frappe.db.set_value("Transit Log", tl.name, {
			"api_sync_status": "Failed",
			"last_api_sync": now_datetime()
		})


def _sync_single_transit_log(tl):
	"""Sync a single Transit Log with the courier's tracking API."""
	supplier = frappe.get_cached_doc("Supplier", tl.courier)

	# Skip if supplier is not a courier or has no API provider
	if not supplier.custom_is_courier:
		return
	if not supplier.custom_courier_api_provider:
		return

	provider = supplier.custom_courier_api_provider
	tracking_number = tl.tracking_number

	# Get decrypted credentials (strip whitespace from copy-paste artifacts)
	api_key = (supplier.get_password("custom_api_key") or "").strip() if supplier.custom_api_key else ""
	api_secret = (supplier.get_password("custom_api_secret") or "").strip() if supplier.custom_api_secret else ""
	account_number = (supplier.custom_api_account_number or "").strip()

	# Call the appropriate API
	result = None
	if provider == "DHL":
		result = _track_dhl(tracking_number, api_key)
	elif provider == "FedEx":
		result = _track_fedex(tracking_number, api_key, api_secret, account_number)
	elif provider == "UPS":
		result = _track_ups(tracking_number, api_key, api_secret)

	if result:
		update_values = {
			"api_sync_status": "Success",
			"last_api_sync": now_datetime()
		}

		if result.get("transit_status"):
			update_values["transit_status"] = result["transit_status"]
		if result.get("expected_delivery_date"):
			update_values["expected_delivery_date"] = getdate(result["expected_delivery_date"])

		frappe.db.set_value("Transit Log", tl.name, update_values)
	else:
		frappe.db.set_value("Transit Log", tl.name, {
			"api_sync_status": "Failed",
			"last_api_sync": now_datetime()
		})


# ---------------------------------------------------------------------------
# Courier API Clients — Placeholder Implementations
# ---------------------------------------------------------------------------

def _track_dhl(tracking_number: str, api_key: str) -> dict:
	"""DHL Shipment Tracking API integration.

	API Docs: https://developer.dhl.com/api-reference/shipment-tracking

	Returns dict with keys: transit_status, expected_delivery_date
	"""
	import requests

	if not api_key:
		frappe.log_error(
			title=_("DHL API: Missing API Key"),
			message=_("API Key is required for DHL tracking.")
		)
		return {}

	url = "https://api-eu.dhl.com/track/shipments"
	headers = {
		"DHL-API-Key": api_key
	}
	params = {
		"trackingNumber": tracking_number
	}

	try:
		response = requests.get(url, headers=headers, params=params, timeout=30)
		response.raise_for_status()

		data = response.json()
		shipments = data.get("shipments", [])
		if not shipments:
			return {}

		shipment = shipments[0]
		status_raw = shipment.get("status", {}).get("statusCode", "")
		estimated_delivery = shipment.get("estimatedTimeOfDelivery", "")

		return {
			"transit_status": status_raw,
			"expected_delivery_date": estimated_delivery[:10] if estimated_delivery else ""
		}

	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title=_("DHL API Error"),
			message=str(e)
		)
		return {}


def _track_fedex(tracking_number: str, api_key: str, api_secret: str, account_number: str) -> dict:
	"""FedEx Track API integration.

	API Docs: https://developer.fedex.com/api/en-us/catalog/track/v1/docs.html

	Returns dict with keys: transit_status, expected_delivery_date
	"""
	import requests

	if not api_key or not api_secret:
		frappe.log_error(
			title=_("FedEx API: Missing Credentials"),
			message=_("API Key and API Secret are required for FedEx tracking.")
		)
		return {}

	# Step 1: Get OAuth token
	token_url = "https://apis.fedex.com/oauth/token"
	token_data = {
		"grant_type": "client_credentials",
		"client_id": api_key,
		"client_secret": api_secret
	}

	try:
		token_response = requests.post(token_url, data=token_data, timeout=30)
		token_response.raise_for_status()
		access_token = token_response.json().get("access_token", "")

		if not access_token:
			return {}

		# Step 2: Track shipment
		track_url = "https://apis.fedex.com/track/v1/trackingnumbers"
		track_headers = {
			"Authorization": "Bearer " + access_token,
			"Content-Type": "application/json",
			"X-locale": "en_US"
		}
		track_payload = {
			"trackingInfo": [
				{
					"trackingNumberInfo": {
						"trackingNumber": tracking_number
					}
				}
			],
			"includeDetailedScans": False
		}

		track_response = requests.post(track_url, headers=track_headers, json=track_payload, timeout=30)
		track_response.raise_for_status()

		track_data = track_response.json()
		results = track_data.get("output", {}).get("completeTrackResults", [])

		if not results:
			return {}

		track_result = results[0].get("trackResults", [{}])[0]
		status_raw = track_result.get("latestStatusDetail", {}).get("statusByLocale", "")
		delivery_detail = track_result.get("estimatedDeliveryTimeWindow", {})
		estimated_delivery = delivery_detail.get("window", {}).get("ends", "")

		return {
			"transit_status": status_raw,
			"expected_delivery_date": estimated_delivery[:10] if estimated_delivery else ""
		}

	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title=_("FedEx API Error"),
			message=str(e)
		)
		return {}


def _track_ups(tracking_number: str, api_key: str, api_secret: str) -> dict:
	"""UPS Tracking API integration.

	API Docs: https://developer.ups.com/api/reference/tracking

	Returns dict with keys: transit_status, expected_delivery_date
	"""
	import requests

	if not api_key or not api_secret:
		frappe.log_error(
			title=_("UPS API: Missing Credentials"),
			message=_("API Key and API Secret are required for UPS tracking.")
		)
		return {}

	# Step 1: Get OAuth token
	token_url = "https://onlinetools.ups.com/security/v1/oauth/token"
	token_data = {
		"grant_type": "client_credentials"
	}

	try:
		token_response = requests.post(
			token_url,
			data=token_data,
			auth=(api_key, api_secret),
			timeout=30
		)
		token_response.raise_for_status()
		access_token = token_response.json().get("access_token", "")

		if not access_token:
			return {}

		# Step 2: Track shipment
		track_url = f"https://onlinetools.ups.com/api/track/v1/details/{tracking_number}"
		track_headers = {
			"Authorization": "Bearer " + access_token,
			"Content-Type": "application/json",
			"transId": tracking_number,
			"transactionSrc": "one_fm"
		}

		track_response = requests.get(track_url, headers=track_headers, timeout=30)
		track_response.raise_for_status()

		track_data = track_response.json()
		shipment = track_data.get("trackResponse", {}).get("shipment", [{}])[0]
		package = shipment.get("package", [{}])[0]

		status_raw = package.get("currentStatus", {}).get("description", "")
		delivery_date_info = package.get("deliveryDate", [{}])
		estimated_delivery = ""
		if delivery_date_info:
			estimated_delivery = delivery_date_info[0].get("date", "")

		return {
			"transit_status": status_raw,
			"expected_delivery_date": estimated_delivery[:10] if estimated_delivery else ""
		}

	except requests.exceptions.RequestException as e:
		frappe.log_error(
			title=_("UPS API Error"),
			message=str(e)
		)
		return {}
