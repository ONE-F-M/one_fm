# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Purchase Receipt process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Validate Purchase Receipt Step": """# Submit needs the signed and stamped delivery note, and the user submitting must pass the store
# keeper check that every save runs (a reliever holding the task does not). Cancel is refused while
# a submitted Purchase Invoice or return is made against the receipt. Sets result["step_valid"];
# on False the process reopens the task.
from one_fm.purchase.utils import validate_store_keeper_project_supervisor

result["step_valid"] = True
action = task_data.get("action")
if action == "Submit":
	if not doc.one_fm_attach_delivery_note:
		result["step_valid"] = False
		frappe.msgprint(frappe._("Please Attach Signed and Stamped Delivery Note"), title=frappe._("Cannot Submit"), indicator="red")
	else:
		try:
			validate_store_keeper_project_supervisor(doc, "validate")
		except frappe.ValidationError:
			result["step_valid"] = False
elif action == "Cancel":
	linked = sorted(set(
		frappe.get_all("Purchase Invoice Item", filters={"purchase_receipt": doc.name, "docstatus": 1}, pluck="parent")
		+ frappe.get_all("Purchase Receipt", filters={"return_against": doc.name, "docstatus": 1}, pluck="name")
	))
	if linked:
		result["step_valid"] = False
		frappe.msgprint(
			frappe._("Cancel these documents first: {0}").format(", ".join(linked)),
			title=frappe._("Cannot Cancel"),
			indicator="red",
		)
""",
	"Update Receipt Request for Material": """# Recounts the received quantity and status of the Request for Material the receipt fills,
# then emails its requester once, when every receivable row is fully received.
from frappe.utils import flt
from one_fm.overrides.purchase_receipt import get_rfm_in_purchase_receipt, update_received_qty
from one_fm.purchase.doctype.request_for_material.request_for_material import (
	build_full_receipt_email,
	send_email,
	update_rfm_status_against_purchase_receipt,
)

update_received_qty(doc, "on_submit")
update_rfm_status_against_purchase_receipt(doc, "on_submit")

rfm_name = doc.custom_request_for_material or get_rfm_in_purchase_receipt(doc)
result["rfm_notified"] = False
if rfm_name and frappe.db.exists("Request for Material", rfm_name):
	rfm = frappe.get_doc("Request for Material", rfm_name)
	receivable = [d for d in rfm.items if d.item_code and not d.reject_item]
	if (
		rfm.purpose in ("Purchase", "Sample Purchase")
		and not rfm.full_receipt_notified
		and rfm.requested_by
		and receivable
		and all(flt(d.qty) - flt(d.received_qty) <= 0 for d in receivable)
	):
		subject = frappe._("Items Arrived: Purchase Receipt Submitted for RFM {0}").format(rfm.name)
		send_email(rfm, [rfm.requested_by], build_full_receipt_email(rfm, receivable, doc), subject)
		frappe.db.set_value("Request for Material", rfm.name, "full_receipt_notified", 1)
		result["rfm_notified"] = True
""",
	"Complete Receipt Transit Logs": """# Marks the Transit Logs of each Purchase Order on the receipt Completed once all their items are received.
from one_fm.one_fm.doctype.transit_log.transit_log_utils import _check_and_complete_transit_log

for po_name in sorted({d.purchase_order for d in doc.items if d.purchase_order}):
	_check_and_complete_transit_log(reference_doctype="Purchase Order", reference_name=po_name)
""",
	"Register Purchase Receipt Assets": """# Creates a Customer Asset per unit of each customer-asset row, and hands the Assets ERPNext
# created for refundable fixed-asset rows to the receipt's customer.
from one_fm.one_fm.doctype.customer_asset.customer_asset import on_purchase_receipt_submit

on_purchase_receipt_submit(doc)

for d in doc.items:
	if not d.get("custom_refundable"):
		continue
	item = frappe.db.get_value("Item", d.item_code, ["is_fixed_asset", "auto_create_assets"], as_dict=True)
	if not (item and item.is_fixed_asset and item.auto_create_assets):
		continue
	asset = frappe.db.get_value(
		"Asset",
		{"purchase_receipt": doc.name, "purchase_receipt_item": d.name, "item_code": d.item_code},
		["name", "available_for_use_date"],
		as_dict=True,
	)
	if asset:
		frappe.db.set_value("Asset", asset.name, {
			"custom_is_refundable": 1,
			"asset_owner": "Customer",
			"customer": doc.custom_customer or None,
			"available_for_use_date": asset.available_for_use_date or doc.posting_date,
		})
		frappe.msgprint(frappe._("Updated asset {0} for refundable item {1}").format(asset.name, d.item_code), alert=True)
""",
	"Assign Purchase Receipt Step": """# Cancelling a submitted receipt is open to every Stock User, the role that cancels receipts.
result["assigned_user"] = ""
result["assigned_role"] = "Stock User"
""",
}


def run(script_name, doc, **task_data):
	"""Run a script the way the Processa engine does and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc,
		"task_data": task_data,
		"result": result,
		"context_doctype": "Purchase Receipt",
		"context_docname": doc.name,
		"bpmn_id": "test",
	}
	with patch("frappe.msgprint"):
		exec(SCRIPTS[script_name], namespace)
	return result


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)


def pr(**kw):
	doc = frappe.new_doc("Purchase Receipt")
	doc.name = "PR-PROCESSA-TEST-1"
	doc.posting_date = "2026-11-22"
	doc.update(kw)
	return doc


class TestAssignPurchaseReceiptStep(FrappeTestCase):
	def test_cancel_goes_to_stock_users(self):
		self.assertEqual(run("Assign Purchase Receipt Step", pr()), {"assigned_user": "", "assigned_role": "Stock User"})


class TestValidatePurchaseReceiptStep(FrappeTestCase):
	V = "Validate Purchase Receipt Step"

	def test_submit_needs_the_delivery_note(self):
		with patch("one_fm.purchase.utils.validate_store_keeper_project_supervisor") as keeper:
			self.assertFalse(run(self.V, pr(), action="Submit")["step_valid"])
		keeper.assert_not_called()

	def test_submit_needs_the_store_keeper(self):
		with patch("one_fm.purchase.utils.validate_store_keeper_project_supervisor", side_effect=frappe.ValidationError):
			self.assertFalse(run(self.V, pr(one_fm_attach_delivery_note="/files/dn.pdf"), action="Submit")["step_valid"])
		with patch("one_fm.purchase.utils.validate_store_keeper_project_supervisor"):
			self.assertTrue(run(self.V, pr(one_fm_attach_delivery_note="/files/dn.pdf"), action="Submit")["step_valid"])

	def test_cancel_refused_while_an_invoice_or_return_is_submitted(self):
		with patch("frappe.get_all", side_effect=[["PINV-1"], []]):
			self.assertFalse(run(self.V, pr(), action="Cancel")["step_valid"])
		with patch("frappe.get_all", side_effect=[[], ["PR-RET-1"]]):
			self.assertFalse(run(self.V, pr(), action="Cancel")["step_valid"])
		with patch("frappe.get_all", return_value=[]):
			self.assertTrue(run(self.V, pr(), action="Cancel")["step_valid"])


class TestUpdateReceiptRequestForMaterial(FrappeTestCase):
	M = "one_fm.purchase.doctype.request_for_material.request_for_material."

	def rfm(self, **kw):
		fields = dict(name="RFM-1", purpose="Purchase", full_receipt_notified=0, requested_by="req@example.com",
			items=[frappe._dict(item_code="I1", reject_item=0, qty=5, received_qty=5), frappe._dict(item_code="I2", reject_item=1, qty=5, received_qty=0)])
		fields.update(kw)
		return SimpleNamespace(**fields)

	def run_update(self, rfm):
		doc = pr(custom_request_for_material="RFM-1")
		with patch("one_fm.overrides.purchase_receipt.update_received_qty") as received, \
			patch(self.M + "update_rfm_status_against_purchase_receipt") as status, \
			patch(self.M + "build_full_receipt_email", return_value="body"), patch(self.M + "send_email") as send, \
			patch("frappe.db.exists", return_value=True), patch("frappe.get_doc", return_value=rfm), \
			patch("frappe.db.set_value") as set_value:
			result = run("Update Receipt Request for Material", doc)
		return result, received, status, send, set_value

	def test_recounts_and_notifies_once_when_fully_received(self):
		result, received, status, send, set_value = self.run_update(self.rfm())
		received.assert_called_once()
		status.assert_called_once()
		send.assert_called_once()
		self.assertEqual(send.call_args[0][1], ["req@example.com"])
		set_value.assert_called_once_with("Request for Material", "RFM-1", "full_receipt_notified", 1)
		self.assertTrue(result["rfm_notified"])

	def test_no_email_when_already_notified_partly_received_or_wrong_purpose(self):
		for rfm in (self.rfm(full_receipt_notified=1), self.rfm(purpose="Individual"),
				self.rfm(items=[frappe._dict(item_code="I1", reject_item=0, qty=5, received_qty=4)])):
			send = self.run_update(rfm)[3]
			send.assert_not_called()


class TestCompleteReceiptTransitLogs(FrappeTestCase):
	def test_checks_each_purchase_order_once(self):
		doc = pr()
		for po_name in ("PO-2", "PO-1", "PO-2", None):
			doc.append("items", {"purchase_order": po_name})
		with patch("one_fm.one_fm.doctype.transit_log.transit_log_utils._check_and_complete_transit_log") as check_log:
			run("Complete Receipt Transit Logs", doc)
		self.assertEqual([c.kwargs["reference_name"] for c in check_log.call_args_list], ["PO-1", "PO-2"])


class TestRegisterPurchaseReceiptAssets(FrappeTestCase):
	def test_customer_assets_and_refundable_assets(self):
		doc = pr(custom_customer="CUST-1")
		doc.append("items", {"item_code": "ASSET-ITEM", "custom_refundable": 1})
		doc.append("items", {"item_code": "PLAIN", "custom_refundable": 0})
		doc.items[0].name = "ROW-1"
		values = [frappe._dict(is_fixed_asset=1, auto_create_assets=1), frappe._dict(name="ACC-ASS-1", available_for_use_date=None)]
		with patch("one_fm.one_fm.doctype.customer_asset.customer_asset.on_purchase_receipt_submit") as customer_assets, \
			patch("frappe.db.get_value", side_effect=values), patch("frappe.db.set_value") as set_value:
			run("Register Purchase Receipt Assets", doc)
		customer_assets.assert_called_once_with(doc)
		set_value.assert_called_once_with("Asset", "ACC-ASS-1", {
			"custom_is_refundable": 1, "asset_owner": "Customer", "customer": "CUST-1", "available_for_use_date": "2026-11-22"})

	def test_refundable_row_that_is_not_an_auto_created_asset_is_skipped(self):
		doc = pr()
		doc.append("items", {"item_code": "X", "custom_refundable": 1})
		with patch("one_fm.one_fm.doctype.customer_asset.customer_asset.on_purchase_receipt_submit"), \
			patch("frappe.db.get_value", return_value=frappe._dict(is_fixed_asset=1, auto_create_assets=0)), \
			patch("frappe.db.set_value") as set_value:
			run("Register Purchase Receipt Assets", doc)
		set_value.assert_not_called()


class TestPurchaseReceiptPython(FrappeTestCase):
	def test_the_map_has_a_field_to_write_the_state_to(self):
		field = frappe.get_meta("Purchase Receipt").get_field("workflow_state")
		self.assertIsNotNone(field)
		self.assertEqual((field.fieldtype, field.options, field.no_copy, field.allow_on_submit), ("Link", "Workflow State", 1, 1))

	def test_submit_hooks_are_gone_and_cancel_hooks_stay(self):
		events = frappe.get_hooks("doc_events")["Purchase Receipt"]
		self.assertNotIn("on_submit", events)
		self.assertNotIn("before_submit", events)
		self.assertIn("one_fm.overrides.purchase_receipt.update_received_qty", events["on_cancel"])
		self.assertNotIn("Purchase Receipt", frappe.get_hooks("override_doctype_class"))
