// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Generate QR Code', {
	refresh: function(frm) {
		alert("Hello");
		var qr_code = frappe.render_template("qr_code",{"doc":frm.doc});
        $(frm.fields_dict["qr_code_html"].wrapper).html(qr_code);
        refresh_field("qr_code_html");
	}
});
