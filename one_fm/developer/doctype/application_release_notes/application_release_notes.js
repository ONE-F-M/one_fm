// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Application Release Notes', {
	refresh: function(frm) {
		frm.disable_save()
	}
});
