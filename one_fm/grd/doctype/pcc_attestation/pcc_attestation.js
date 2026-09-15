// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// WI-002028: show the operator when a receipt went up without waiting for a save, and blank
// the stamp as soon as a file is removed. The controller stamps the same fields from the
// server clock on every save and stays the authority on them.
frappe.ui.form.on('PCC Attestation', {
	upload_embassy_payment_receipt: function(frm){
		stamp_receipt(frm, 'upload_embassy_payment_receipt', 'upload_embassy_payment_receipt_on');
	},
	upload_mofa_payment_receipt: function(frm){
		stamp_receipt(frm, 'upload_mofa_payment_receipt', 'upload_mofa_payment_receipt_on');
	},
	upload_translation_payment_receipt: function(frm){
		stamp_receipt(frm, 'upload_translation_payment_receipt', 'upload_translation_payment_receipt_on');
	}
});

function stamp_receipt(frm, receipt_field, timestamp_field){
	if(frm.doc[receipt_field] && !frm.doc[timestamp_field]){
		frm.set_value(timestamp_field, frappe.datetime.now_datetime());
	}
	if(!frm.doc[receipt_field] && frm.doc[timestamp_field]){
		frm.set_value(timestamp_field, null);
	}
}
