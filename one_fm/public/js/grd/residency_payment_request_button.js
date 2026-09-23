// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt
//
// WI-002498: raise a Residency Payment Request from the record that owes the money.
//
// Registered once for the session from app_include_js rather than per DocType: a file
// loaded through doctype_js is evaluated again for every DocType it is listed against, and
// three registrations of the same handler add the button three times.

frappe.provide("one_fm.grd");

one_fm.grd.residency_payment_request = {
	// What has to be true of a record before it can owe anything. The same three rules
	// live on the server in one_fm/grd/residency_payment.py - this decides whether the
	// button is offered, that decides whether the request may be raised.
	is_payable: function (frm) {
		if (frm.is_new()) {
			return false;
		}

		if (frm.doc.doctype === "Preparation") {
			// The costing is what the document is for, and it is only real once submitted.
			return frm.doc.docstatus === 1;
		}

		if (frm.doc.workflow_state === "Cancelled") {
			return false;
		}

		if (frm.doc.doctype === "Residency") {
			return Boolean(frm.doc.residency_fine_to_be_added && frm.doc.residency_fine_amount_kwd);
		}

		if (frm.doc.doctype === "PACI") {
			return Boolean(frm.doc.is_paci_fine_applicable && frm.doc.paci_fine_amount_kwd);
		}

		return false;
	},

	add_button: function (frm) {
		if (!one_fm.grd.residency_payment_request.is_payable(frm)) {
			return;
		}

		frm.add_custom_button(__("Create Residency Payment Request"), function () {
			one_fm.grd.residency_payment_request.open(frm);
		});
	},

	open: function (frm) {
		frappe.call({
			method: "one_fm.grd.residency_payment.make_residency_payment_request",
			args: {
				source_doctype: frm.doc.doctype,
				source_name: frm.doc.name
			},
			freeze: true,
			freeze_message: __("Opening Residency Payment Request..."),
			callback: function (r) {
				if (!r.message) {
					return;
				}

				// One request per record. A second one against the same Residency fine is
				// the fine paid twice, so the existing one is opened instead.
				if (r.message.existing) {
					frappe.msgprint({
						title: __("Already Linked"),
						indicator: "blue",
						message: __("A Residency Payment Request [{0}] is already linked to this document.", [
							r.message.existing
						])
					});
					frappe.set_route("Form", "Residency Payment Request", r.message.existing);
					return;
				}

				// Handed over unsaved: an operator who clicked by mistake leaves nothing
				// behind, and the request exists only once they save it.
				const doclist = frappe.model.sync(r.message.doc);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	}
};

["Preparation", "Residency", "PACI"].forEach(function (doctype) {
	frappe.ui.form.on(doctype, {
		refresh: function (frm) {
			one_fm.grd.residency_payment_request.add_button(frm);
		}
	});
});
