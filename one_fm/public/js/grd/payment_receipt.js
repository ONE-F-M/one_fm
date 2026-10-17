// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt
//
// Fill Payment Date from the attached payment receipt PDF.
// Registered once from app_include_js, like residency_payment_request_button.js.

frappe.provide("one_fm.grd");

one_fm.grd.payment_receipt = {
	read_payment_date: function (frm, fieldname) {
		const file_url = frm.doc[fieldname];
		// payment_date has no allow_on_submit, so a submitted record is left alone.
		if (!file_url || frm.is_new() || frm.doc.docstatus === 1) {
			return;
		}

		frappe.call({
			method: "one_fm.grd.payment_receipt.read_payment_date",
			args: {
				doctype: frm.doc.doctype,
				name: frm.doc.name,
				file_url: file_url
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value("payment_date", r.message);
					frappe.show_alert(__("Payment Date read from the receipt. Please check it."));
				} else {
					frappe.show_alert(
						{
							message: __("Payment Date could not be read from the receipt. Please enter it."),
							indicator: "orange"
						},
						7
					);
				}
			}
		});
	}
};

Object.entries({
	"Work Permit": "attach_invoice",
	"Medical Insurance": "upload_medical_insurance",
	"Residency": "invoice_attachment",
	"PACI": "upload_civil_id_payment"
}).forEach(function ([doctype, fieldname]) {
	frappe.ui.form.on(doctype, fieldname, function (frm) {
		one_fm.grd.payment_receipt.read_payment_date(frm, fieldname);
	});
});
