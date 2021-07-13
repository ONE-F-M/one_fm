// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee License Issuance', {
	onload_post_render: function(frm){
		frm.get_field("employees").grid.set_multiple_add("employee");
	}
	// refresh: function(frm) {

	// }
});
