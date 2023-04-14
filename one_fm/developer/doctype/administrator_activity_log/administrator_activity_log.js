// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Administrator Activity Log', {
	refresh: function(frm) {
		frm.trigger('set_defaults');
	},
	set_defaults: function(frm) {
		if (frm.is_new() && !frm.doc.employee){
			frappe.db.get_value('Employee', {'user_id':frappe.session.user}, 'name').then(res=>{
				frm.set_value('employee', res.message.name);
			})
		}
		if (frm.is_new() && !frm.doc.date){frm.set_value('date', frappe.datetime.get_today())}
	}
});
