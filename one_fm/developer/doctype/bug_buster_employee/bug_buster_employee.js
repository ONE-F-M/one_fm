// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bug Buster Employee', {
	validate: function(frm) {
		frm.doc.employees.forEach((item, index)=>{
			item.order = index+1
		})
	}
});