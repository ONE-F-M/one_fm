# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Purchase Order process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.purchase.utils import set_purchase_type_from_rfp

SCRIPTS = {
	"Prepare Purchase Order from Request for Purchase": """# For an order raised from a Request for Purchase: closes the request's tasks held by Purchase
# Users and copies the supplier quotations' attachments onto the order.
from frappe.desk.form.assign_to import remove
from frappe.desk.form.load import get_attachments
from frappe.utils.user import get_users_with_role

rfp = doc.one_fm_request_for_purchase
if rfp:
	for user in get_users_with_role("Purchase User"):
		remove("Request for Purchase", rfp, user)
	for quotation in frappe.get_list("Quotation From Supplier", filters={"request_for_purchase": rfp}, pluck="name"):
		for attachment in get_attachments("Quotation From Supplier", quotation):
			frappe.get_doc({
				"doctype": "File",
				"file_url": attachment.file_url,
				"file_name": attachment.file_name,
				"attached_to_doctype": doc.doctype,
				"attached_to_name": doc.name,
				"folder": "Home/Attachments",
			}).insert()
""",
	"Assign Purchase Order Step": """# Opens the next step to every holder of the role that acts on it. The Draft goes back to its
# owner and Pending Purchase Manager to its named user, so the role the last step was given is cleared.
result["assigned_user"] = ""
result["assigned_role"] = {
	"Pending Finance Approver": "Finance PO Approver",
	"Hold": "Purchase Manager",
	"Approved": "Purchase Manager",
}.get(doc.workflow_state, "")
""",
	"Stamp Purchase Order Approval Date": """# Records the day the Purchase Officer sent the order for approval (on reaching Pending Purchase
# Manager) and the day the Purchase Manager approved it (on reaching Pending Finance Approver).
# Once both dates are set they are kept.
field = {
	"Pending Purchase Manager": "custom_purchase_officer_approval_date",
	"Pending Finance Approver": "custom_purchase_manager_approval_date",
}.get(doc.workflow_state)
if field and not (doc.custom_purchase_officer_approval_date and doc.custom_purchase_manager_approval_date):
	frappe.db.set_value("Purchase Order", doc.name, field, frappe.utils.nowdate())
""",
	"Apply Purchase Order Submit Updates": """# Runs once the order is submitted: recounts the ordered and pending quantities on its Request for
# Purchase and Request for Material and their statuses, sets the Authorization Signature letter
# head, and opens a Transit Log for a Sample Purchase the courier does not hand-carry.
from one_fm.one_fm.doctype.transit_log.transit_log_utils import create_transit_log_from_po
from one_fm.purchase.doctype.request_for_material.request_for_material import (
	update_completed_purchase_qty,
	update_rfm_status_against_purchase_order,
)
from one_fm.purchase.doctype.request_for_purchase.request_for_purchase import update_rfp_status

doc.update_purchased_quantities()
doc.update_ordered_and_pending_quantities()
if doc.one_fm_request_for_purchase:
	update_rfp_status(doc.one_fm_request_for_purchase)
update_completed_purchase_qty(doc, "on_submit")
update_rfm_status_against_purchase_order(doc, "on_submit")

if not doc.letter_head and frappe.db.exists("Letter Head", "Authorization Signature"):
	frappe.db.set_value("Purchase Order", doc.name, "letter_head", "Authorization Signature")

result["transit_log"] = ""
if doc.custom_purpose == "Sample Purchase" and not frappe.utils.cint(doc.custom_is_courier_hand_carried):
	try:
		result["transit_log"] = create_transit_log_from_po(doc.name)
	except Exception:
		frappe.log_error(
			title=frappe._("Transit Log Auto-Creation Failed for PO {0}").format(doc.name),
			message=frappe.get_traceback(),
		)
""",
	"Notify Purchase Order Approved": """# Emails the Procurement Managers, copying saoud, a.magar and a.nowshad, that the order is approved.
from frappe.utils.user import get_users_with_role

message = '''Good day.
Please be informed that the Purchase Order {{doc.name}} created by {{doc.owner}} has been approved

The items to be purchased include: <br>
<h3>Order Summary</h3>
<p>Supplier: {{doc.supplier}}</p>
<table>
<tr>
    <th>Item Name</th>
    <th>Warehouse</th>
    <th> Qty</th>
    <th>Expected Delivery Date</th>
</tr>
{% for i in doc.items %}
        <tr align="center">
  <td>{{ i.item_name }}</td>  
  <td>{{i.warehouse}}</td>
  <td>{{i.qty}}</td>  
  <td>{{i.expected_delivery_date}}</td>
        </tr>
    {% endfor %}
</table>
<br>
<br>
Please make the appropriate preparations.
'''
context = {"doc": doc}
frappe.sendmail(
	recipients=get_users_with_role("Procurement Manager"),
	cc=["saoud@one-fm.com", "a.magar@one-fm.com", "a.nowshad@one-fm.com"],
	sender=frappe.db.get_value("Email Account", "Notifications", "email_id"),
	subject=frappe.render_template("Purchase Order {{doc.name}} Approved", context),
	message=frappe.utils.md_to_html(frappe.render_template(message, context)),
	reference_doctype=doc.doctype,
	reference_name=doc.name,
)
""",
	"Validate Purchase Order Cancel": """# Cancelling is refused while a submitted Purchase Receipt or Purchase Invoice is made against the
# order. Sets result["step_valid"]; on False the process reopens the Approved task.
result["step_valid"] = True
if task_data.get("action") == "Cancel":
	linked = sorted(set(
		frappe.get_all("Purchase Receipt Item", filters={"purchase_order": doc.name, "docstatus": 1}, pluck="parent")
		+ frappe.get_all("Purchase Invoice Item", filters={"purchase_order": doc.name, "docstatus": 1}, pluck="parent")
	))
	if linked:
		result["step_valid"] = False
		frappe.msgprint(
			frappe._("Cancel these documents first: {0}").format(", ".join(linked)),
			title=frappe._("Cannot Cancel"),
			indicator="red",
		)
""",
	"Apply Purchase Order Cancel Updates": """# Runs once the order is cancelled: recounts the purchased, ordered and pending quantities on its
# Request for Purchase and Request for Material and their statuses, so the cancelled order no longer
# counts. Throws, and so undoes the cancel, when a Request for Material on the order is Stopped or Cancelled.
from one_fm.purchase.doctype.request_for_material.request_for_material import (
	update_completed_purchase_qty,
	update_rfm_status_against_purchase_order,
)
from one_fm.purchase.doctype.request_for_purchase.request_for_purchase import update_rfp_status

doc.update_purchased_quantities()
doc.update_ordered_and_pending_quantities()
if doc.one_fm_request_for_purchase:
	update_rfp_status(doc.one_fm_request_for_purchase)
update_completed_purchase_qty(doc, "on_cancel")
update_rfm_status_against_purchase_order(doc, "on_cancel")
""",
	"Send Due Purchase Order Payment Terms": """# Runs daily at midnight, as the daily scheduler job did. Emails every Finance user the Purchase
# Order payment terms due today, when scheduler emails are enabled in ONEFM General Setting.
from datetime import datetime
from one_fm.processor import sendemail

template = '''<link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/css/bootstrap.min.css" rel="stylesheet" id="bootstrap-css">
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/js/bootstrap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>

<style media="screen">
    #invoice{
    padding: 30px;
}

.invoice {
    position: relative;
    background-color: #FFF;
    min-height: 680px;
    padding: 15px
}

.invoice header {
    padding: 10px 0;
    margin-bottom: 20px;
    border-bottom: 1px solid #3989c6
}

.invoice .company-details {
    text-align: right
}

.invoice .company-details .name {
    margin-top: 0;
    margin-bottom: 0
}

.invoice .contacts {
    margin-bottom: 20px
}

.invoice .invoice-to {
    text-align: left
}

.invoice .invoice-to .to {
    margin-top: 0;
    margin-bottom: 0
}

.invoice .invoice-details {
    text-align: right
}

.invoice .invoice-details .invoice-id {
    margin-top: 0;
    color: #3989c6
}

.invoice main {
    padding-bottom: 50px
}

.invoice main .thanks {
    margin-top: -100px;
    font-size: 2em;
    margin-bottom: 50px
}

.invoice main .notices {
    padding-left: 6px;
    border-left: 6px solid #3989c6
}

.invoice main .notices .notice {
    font-size: 1.2em
}

.invoice table {
    width: 100%;
    border-collapse: collapse;
    border-spacing: 0;
    margin-bottom: 20px
}

.invoice table td,.invoice table th {
    padding: 15px;
    background: #eee;
    border-bottom: 1px solid #fff
}

.invoice table th {
    white-space: nowrap;
    font-weight: 400;
    font-size: 16px
}

.invoice table td h3 {
    margin: 0;
    font-weight: 400;
    color: #3989c6;
    font-size: 1.2em
}

.invoice table .qty,.invoice table .total,.invoice table .unit {
    text-align: right;
    font-size: 1.2em
}

.invoice table .no {
    color: #fff;
    font-size: 1.6em;
    background: #3989c6
}

.invoice table .unit {
    background: #ddd
}

.invoice table .total {
    background: #3989c6;
    color: #fff
}

.invoice table tbody tr:last-child td {
    border: none
}

.invoice table tfoot td {
    background: 0 0;
    border-bottom: none;
    white-space: nowrap;
    text-align: right;
    padding: 10px 20px;
    font-size: 1.2em;
    border-top: 1px solid #aaa
}

.invoice table tfoot tr:first-child td {
    border-top: none
}

.invoice table tfoot tr:last-child td {
    color: #3989c6;
    font-size: 1.4em;
    border-top: 1px solid #3989c6
}

.invoice table tfoot tr td:first-child {
    border: none
}

.invoice footer {
    width: 100%;
    text-align: center;
    color: #777;
    border-top: 1px solid #aaa;
    padding: 8px 0
}

@media print {
    .invoice {
        font-size: 11px!important;
        overflow: hidden!important
    }

    .invoice footer {
        position: absolute;
        bottom: 10px;
        page-break-after: always
    }

    .invoice>div:last-child {
        page-break-before: always
    }
}
</style>

<div id="invoice">

    <div class="toolbar hidden-print">
        <div class="text-right">
            <!-- <button id="printInvoice" class="btn btn-info"><i class="fa fa-print"></i> Print</button>
            <button class="btn btn-info"><i class="fa fa-file-pdf-o"></i> Export as PDF</button> -->
        </div>
        <hr>
    </div>
    <div class="invoice overflow-auto">
        <div style="min-width: 600px">
            <header>
                <div class="row">
                    <div class="col">
                        <a target="_blank" href="https://lobianijs.com">
                            <img src="#" data-holder-rendered="true" />
                            </a>
                    </div>
                    <div class="col company-details">
                        <h2 class="name">
                            <a target="_blank" href="#">
                            {{company}}
                            </a>
                        </h2>
                        <!-- <div>455 Foggy Heights, AZ 85004, US</div>
                        <div>(123) 456-789</div>
                        <div>company@example.com</div> -->
                    </div>
                </div>
            </header>
            <main>
                <div class="row contacts">
                    <div class="col invoice-to">
                        <div class="text-gray-light">DUE PURCHASE ORDERS:</div>
                        <!-- <h2 class="to">John Doe</h2> -->
                        <div class="address">The following Purchase Order payment schedules are due for payment.</div>
                        <!-- <div class="email"><a href="mailto:john@example.com">john@example.com</a></div> -->
                    </div>
                    <div class="col invoice-details">
                        <h1 class="invoice-id">Purchase Order</h1>
                        <!-- <div class="date">Date of Invoice: 01/10/2018</div> -->
                        <div class="date">Due Date: {{date.date()}}</div>
                    </div>
                </div>
                <table border="0" cellspacing="0" cellpadding="0">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th class="">PO. Name</th>
                            <th class="">Supplier</th>
                            <th class="">Term</th>
                            <th>Due Date</th>
                            <th class="">Invoice Portion</th>
                            <th class="">Payment Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for i in items %}
                        <tr>
                            <td>{{loop.index}}</td>
                            <td class=""> <a target="_blank" href="{{frappe.utils.get_url()+'/app/purchase-order/'}}{{i.doc}}">{{i.doc}}</a></td>
                            <td class="">{{i.supplier_name}}</td>
                            <td class="">{{i.payment_term}}</td>
                            <td class="">{{i.due_date}}</td>
                            <td class="">{{i.invoice_portion}}%</td>
                            <td>{{frappe.utils.fmt_money(i.payment_amount, currency="KWD")}}</td>
                        </tr>
                        {% endfor %}

                    </tbody>
                    <br><br>
                    <tfoot>
                        <tr>
                            <td colspan="2"></td>
                            <td colspan="2">TOTAL DUE</td>
                            <td>{{frappe.utils.fmt_money(total, currency="KWD")}}</td>
                        </tr>
                    </tfoot>
                </table>
                <div class="thanks"></div>
                <div class="notices">
                    <br><br>
                    <div>NOTICE:</div>
                    <div class="notice">Please ensure to confirm the documents before proceeding, you can click on any of the name to open doucment.</div>
                </div>
            </main>
            <footer>
                <!-- Invoice was created on a computer and is valid without the signature and seal. -->
            </footer>
        </div>
        <!--DO NOT DELETE THIS div. IT is responsible for showing footer always at the bottom-->
        <div></div>
    </div>
</div>
'''

try:
	PurchaseOrder = frappe.qb.DocType("Purchase Order")
	PaymentSchedule = frappe.qb.DocType("Payment Schedule")
	items = (
		frappe.qb.from_(PurchaseOrder)
		.join(PaymentSchedule).on(PaymentSchedule.parent == PurchaseOrder.name)
		.select(
			PurchaseOrder.name.as_("doc"), PurchaseOrder.supplier, PurchaseOrder.supplier_name,
			PaymentSchedule.name, PaymentSchedule.payment_term, PaymentSchedule.due_date,
			PaymentSchedule.invoice_portion, PaymentSchedule.payment_amount, PaymentSchedule.outstanding,
		)
		.where(PaymentSchedule.due_date == datetime.today().date())
		.where(PurchaseOrder.docstatus == 1)
		.where(PaymentSchedule.parenttype == "Purchase Order")
		.orderby(PurchaseOrder.name)
	).run(as_dict=True)

	result["due_count"] = len(items)
	if items:
		content = frappe.render_template(template, {
			"items": items,
			"date": datetime.today(),
			"total": sum([i.payment_amount for i in items]),
			"company": frappe.utils.get_defaults("company"),
		})
		HasRole = frappe.qb.DocType("Has Role")
		User = frappe.qb.DocType("User")
		recipients = (
			frappe.qb.from_(HasRole)
			.inner_join(User).on(HasRole.parent == User.name)
			.select(User.name)
			.where(HasRole.role.like("Finance%"))
			.where(HasRole.parent.like("%@%"))
			.groupby(User.name)
		).run(pluck=True)
		sendemail(recipients=recipients, subject="Due Purchase Order Payment", message=content, is_scheduler_email=True)
except Exception as e:
	frappe.log_error(message=str(e), title="Purchase Order payment schedule")
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
		"context_doctype": "Purchase Order",
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


def po(**kw):
	doc = frappe.new_doc("Purchase Order")
	doc.name = "PO-PROCESSA-TEST-1"
	doc.update(kw)
	return doc


class TestAssignPurchaseOrderStep(FrappeTestCase):
	def test_each_state_goes_to_its_role(self):
		for state, role in (("Pending Finance Approver", "Finance PO Approver"), ("Hold", "Purchase Manager"),
				("Approved", "Purchase Manager"), ("Draft", ""), ("Pending Purchase Manager", "")):
			result = run("Assign Purchase Order Step", po(workflow_state=state), assigned_role="Stale")
			self.assertEqual((result["assigned_role"], result["assigned_user"]), (role, ""), state)


class TestStampPurchaseOrderApprovalDate(FrappeTestCase):
	def test_each_state_stamps_its_date(self):
		for state, field in (("Pending Purchase Manager", "custom_purchase_officer_approval_date"),
				("Pending Finance Approver", "custom_purchase_manager_approval_date")):
			with patch("frappe.db.set_value") as set_value:
				run("Stamp Purchase Order Approval Date", po(workflow_state=state))
			set_value.assert_called_once_with("Purchase Order", "PO-PROCESSA-TEST-1", field, frappe.utils.nowdate())

	def test_dates_are_kept_once_both_are_set(self):
		doc = po(workflow_state="Pending Purchase Manager", custom_purchase_officer_approval_date="2026-01-01",
			custom_purchase_manager_approval_date="2026-01-02")
		with patch("frappe.db.set_value") as set_value:
			run("Stamp Purchase Order Approval Date", doc)
		set_value.assert_not_called()

	def test_other_states_stamp_nothing(self):
		with patch("frappe.db.set_value") as set_value:
			run("Stamp Purchase Order Approval Date", po(workflow_state="Hold"))
		set_value.assert_not_called()


class TestPreparePurchaseOrderFromRequestForPurchase(FrappeTestCase):
	def test_closes_rfp_tasks_and_copies_quotation_attachments(self):
		file_doc, doc = MagicMock(), po(one_fm_request_for_purchase="RFP-1")
		with patch("frappe.utils.user.get_users_with_role", return_value=["pu@example.com"]), \
			patch("frappe.desk.form.assign_to.remove") as remove, \
			patch("frappe.get_list", return_value=["QFS-1"]), \
			patch("frappe.desk.form.load.get_attachments", return_value=[frappe._dict(file_url="/files/q.pdf", file_name="q.pdf")]), \
			patch("frappe.get_doc", return_value=file_doc) as get_doc:
			run("Prepare Purchase Order from Request for Purchase", doc)
		remove.assert_called_once_with("Request for Purchase", "RFP-1", "pu@example.com")
		self.assertEqual(get_doc.call_args[0][0]["attached_to_name"], "PO-PROCESSA-TEST-1")
		file_doc.insert.assert_called_once()

	def test_order_without_rfp_is_left_alone(self):
		with patch("frappe.desk.form.assign_to.remove") as remove, patch("frappe.get_list") as get_list:
			run("Prepare Purchase Order from Request for Purchase", po())
		remove.assert_not_called()
		get_list.assert_not_called()


class TestApplyPurchaseOrderSubmitUpdates(FrappeTestCase):
	def doc(self, **kw):
		doc = MagicMock()
		doc.name, doc.letter_head, doc.one_fm_request_for_purchase = "PO-PROCESSA-TEST-1", None, "RFP-1"
		doc.custom_purpose, doc.custom_is_courier_hand_carried = "Purchase", 0
		for k, v in kw.items():
			setattr(doc, k, v)
		return doc

	def run_updates(self, doc):
		M = "one_fm.purchase.doctype.request_for_material.request_for_material."
		with patch(M + "update_completed_purchase_qty") as rfm_qty, patch(M + "update_rfm_status_against_purchase_order") as rfm_status, \
			patch("one_fm.purchase.doctype.request_for_purchase.request_for_purchase.update_rfp_status") as rfp_status, \
			patch("one_fm.one_fm.doctype.transit_log.transit_log_utils.create_transit_log_from_po", return_value="TL-1") as transit, \
			patch("frappe.db.exists", return_value=True), patch("frappe.db.set_value") as set_value:
			result = run("Apply Purchase Order Submit Updates", doc)
		return result, rfm_qty, rfm_status, rfp_status, transit, set_value

	def test_recounts_and_sets_letter_head(self):
		doc = self.doc()
		result, rfm_qty, rfm_status, rfp_status, transit, set_value = self.run_updates(doc)
		doc.update_purchased_quantities.assert_called_once()
		doc.update_ordered_and_pending_quantities.assert_called_once()
		rfp_status.assert_called_once_with("RFP-1")
		rfm_qty.assert_called_once_with(doc, "on_submit")
		rfm_status.assert_called_once_with(doc, "on_submit")
		set_value.assert_called_once_with("Purchase Order", "PO-PROCESSA-TEST-1", "letter_head", "Authorization Signature")
		transit.assert_not_called()
		self.assertEqual(result["transit_log"], "")

	def test_letter_head_already_chosen_is_kept(self):
		set_value = self.run_updates(self.doc(letter_head="Other"))[5]
		set_value.assert_not_called()

	def test_sample_purchase_opens_a_transit_log_unless_hand_carried(self):
		result, *_rest, transit, _sv = self.run_updates(self.doc(custom_purpose="Sample Purchase"))
		transit.assert_called_once_with("PO-PROCESSA-TEST-1")
		self.assertEqual(result["transit_log"], "TL-1")
		transit = self.run_updates(self.doc(custom_purpose="Sample Purchase", custom_is_courier_hand_carried=1))[4]
		transit.assert_not_called()


class TestNotifyPurchaseOrderApproved(FrappeTestCase):
	def test_emails_procurement_managers_with_the_live_cc(self):
		doc = po(supplier="Supplier X", owner="officer@example.com")
		doc.append("items", {"item_name": "Boots", "warehouse": "W1", "qty": 3})
		with patch("frappe.utils.user.get_users_with_role", return_value=["pm@example.com"]) as role_users, \
			patch("frappe.sendmail") as sendmail:
			run("Notify Purchase Order Approved", doc)
		role_users.assert_called_once_with("Procurement Manager")
		kw = sendmail.call_args.kwargs
		self.assertEqual(kw["recipients"], ["pm@example.com"])
		self.assertEqual(kw["cc"], ["saoud@one-fm.com", "a.magar@one-fm.com", "a.nowshad@one-fm.com"])
		self.assertEqual(kw["subject"], "Purchase Order PO-PROCESSA-TEST-1 Approved")
		self.assertIn("Boots", kw["message"])
		self.assertIn("Supplier X", kw["message"])


class TestValidatePurchaseOrderCancel(FrappeTestCase):
	def test_submitted_receipts_or_invoices_block_the_cancel(self):
		with patch("frappe.get_all", side_effect=[["PR-1"], []]):
			self.assertFalse(run("Validate Purchase Order Cancel", po(), action="Cancel")["step_valid"])

	def test_nothing_linked_lets_it_cancel(self):
		with patch("frappe.get_all", return_value=[]) as get_all:
			self.assertTrue(run("Validate Purchase Order Cancel", po(), action="Cancel")["step_valid"])
		self.assertEqual(get_all.call_args.kwargs["filters"], {"purchase_order": "PO-PROCESSA-TEST-1", "docstatus": 1})


class TestPurchaseOrderPython(FrappeTestCase):
	def test_purchase_type_comes_from_the_rfp_before_insert(self):
		doc = po(one_fm_request_for_purchase="RFP-1")
		with patch("frappe.db.get_value", return_value="Project") as get_value:
			set_purchase_type_from_rfp(doc, "before_insert")
		get_value.assert_called_once_with("Request for Purchase", "RFP-1", "type")
		self.assertEqual(doc.purchase_type, "Project")

	def test_the_lifecycle_hooks_are_gone(self):
		events = frappe.get_hooks("doc_events")["Purchase Order"]
		self.assertNotIn("on_submit", events)
		self.assertNotIn("after_insert", events)
		self.assertNotIn("on_update", events)
		self.assertNotIn("on_cancel", events)
		self.assertEqual(events["before_insert"], ["one_fm.purchase.utils.set_purchase_type_from_rfp"])

	def test_submit_runs_no_follow_up_in_python(self):
		from one_fm.overrides.purchase_order import PurchaseOrderOverride
		doc = MagicMock()
		PurchaseOrderOverride.on_submit(doc)
		doc.update_purchased_quantities.assert_not_called()

	def test_cancel_runs_no_follow_up_in_python(self):
		from one_fm.overrides.purchase_order import PurchaseOrderOverride
		doc = MagicMock()
		with patch("erpnext.buying.doctype.purchase_order.purchase_order.PurchaseOrder.on_cancel") as core:
			PurchaseOrderOverride.on_cancel(doc)
		doc.update_purchased_quantities.assert_not_called()
		doc.update_ordered_and_pending_quantities.assert_not_called()
		core.assert_not_called()

	def test_the_payment_terms_job_left_the_scheduler(self):
		from one_fm.tasks import execute
		with patch.object(execute, "enqueue") as enqueue:
			execute.daily()
		self.assertNotIn("one_fm.tasks.erpnext.purchase_order.due_purchase_order_payment_terms", [c.args[0] for c in enqueue.call_args_list])
		self.assertEqual(len(enqueue.call_args_list), 2)

	def test_unprotected_and_dead_functions_are_gone(self):
		import one_fm.overrides.purchase_order as po_module
		import one_fm.purchase.utils as utils
		for name in ("correct_purchase_order_rates", "get_incorrect_purchase_orders"):
			self.assertFalse(hasattr(po_module, name), name)
		self.assertFalse(hasattr(utils, "on_update"))


class TestApplyPurchaseOrderCancelUpdates(FrappeTestCase):
	def run_updates(self, doc):
		M = "one_fm.purchase.doctype.request_for_material.request_for_material."
		calls = MagicMock()
		with patch(M + "update_completed_purchase_qty", side_effect=lambda *a: calls("rfm_qty", *a)), \
			patch(M + "update_rfm_status_against_purchase_order", side_effect=lambda *a: calls("rfm_status", *a)), \
			patch("one_fm.purchase.doctype.request_for_purchase.request_for_purchase.update_rfp_status", side_effect=lambda *a: calls("rfp_status", *a)):
			doc.update_purchased_quantities.side_effect = lambda: calls("purchased")
			doc.update_ordered_and_pending_quantities.side_effect = lambda: calls("ordered")
			run("Apply Purchase Order Cancel Updates", doc)
		return [c.args for c in calls.call_args_list]

	def test_recounts_in_the_order_the_cancel_hooks_ran(self):
		doc = MagicMock()
		doc.name, doc.one_fm_request_for_purchase = "PO-PROCESSA-TEST-1", "RFP-1"
		self.assertEqual(self.run_updates(doc), [
			("purchased",), ("ordered",), ("rfp_status", "RFP-1"), ("rfm_qty", doc, "on_cancel"), ("rfm_status", doc, "on_cancel"),
		])

	def test_no_rfp_status_without_a_request_for_purchase(self):
		doc = MagicMock()
		doc.name, doc.one_fm_request_for_purchase = "PO-PROCESSA-TEST-1", None
		self.assertNotIn("rfp_status", [c[0] for c in self.run_updates(doc)])

	def test_a_stopped_request_for_material_still_refuses_the_cancel(self):
		M = "one_fm.purchase.doctype.request_for_material.request_for_material."
		doc = MagicMock()
		doc.name, doc.one_fm_request_for_purchase = "PO-PROCESSA-TEST-1", None
		with patch(M + "update_completed_purchase_qty", side_effect=frappe.InvalidStatusError), \
			patch(M + "update_rfm_status_against_purchase_order") as rfm_status:
			self.assertRaises(frappe.InvalidStatusError, run, "Apply Purchase Order Cancel Updates", doc)
		rfm_status.assert_not_called()


class TestSendDuePurchaseOrderPaymentTerms(FrappeTestCase):
	def due(self, **kw):
		row = frappe._dict(doc="PO-PROCESSA-TEST-1", supplier="SUP-1", supplier_name="Supplier X", name="PS-1",
			payment_term="Advance", due_date=frappe.utils.getdate(), invoice_portion=50, payment_amount=125.5, outstanding=125.5)
		row.update(kw)
		return row

	def send(self, due_rows, finance_users=("fin@example.com",)):
		runs = [due_rows, list(finance_users)]
		query = MagicMock()
		query.run.side_effect = lambda **kw: runs.pop(0)
		for method in ("from_", "join", "inner_join", "on", "select", "where", "orderby", "groupby"):
			getattr(query, method).return_value = query
		with patch("frappe.qb.from_", return_value=query), patch("one_fm.processor.sendemail") as sendemail:
			result = run("Send Due Purchase Order Payment Terms", MagicMock())
		return result, sendemail, query

	def test_finance_users_get_the_due_terms(self):
		result, sendemail, _query = self.send([self.due(), self.due(name="PS-2", payment_amount=74.5)])
		kw = sendemail.call_args.kwargs
		self.assertEqual(kw["recipients"], ["fin@example.com"])
		self.assertEqual(kw["subject"], "Due Purchase Order Payment")
		self.assertTrue(kw["is_scheduler_email"])
		self.assertIn("PO-PROCESSA-TEST-1", kw["message"])
		self.assertIn("Supplier X", kw["message"])
		self.assertIn(frappe.utils.fmt_money(200, currency="KWD"), kw["message"])
		self.assertEqual(result["due_count"], 2)

	def test_nothing_due_sends_nothing(self):
		result, sendemail, query = self.send([])
		sendemail.assert_not_called()
		self.assertEqual(query.run.call_count, 1)
		self.assertEqual(result["due_count"], 0)

	def test_an_error_is_logged_not_raised(self):
		with patch("frappe.qb.from_", side_effect=Exception("boom")), patch("frappe.log_error") as log_error:
			run("Send Due Purchase Order Payment Terms", MagicMock())
		log_error.assert_called_once_with(message="boom", title="Purchase Order payment schedule")

	def test_the_query_reads_live_data(self):
		# Runs the real queries; only the email is stopped.
		with patch("one_fm.processor.sendemail"), patch("frappe.log_error") as log_error:
			run("Send Due Purchase Order Payment Terms", MagicMock())
		log_error.assert_not_called()
