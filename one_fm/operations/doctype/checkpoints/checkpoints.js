// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Checkpoints', {
	refresh: function(frm) {
		var qr_code = frappe.render_template("qr_code",{"doc":frm.doc});
        $(frm.fields_dict["checkpoint_qr"].wrapper).html(qr_code);
        refresh_field("checkpoint_qr")
	}
});
