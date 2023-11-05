// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Incident Form', {
	refresh: function(frm) {
		if(!frm.doc.reporter){
			set_reporter_from_the_session_user(frm);
		}
	}
});

var set_reporter_from_the_session_user = function(frm) {
	if(frappe.session.user != 'Administrator'){
		frappe.db.get_value('Employee', {'user_id': frappe.session.user} , 'name', function(r) {
			if(r && r.name){
				frm.set_value('reporter', r.name);
			}
			else{
				frappe.show_alert(__('No employee linked to the user <b>{0}</b>', [frappe.session.user]));
			}
		});
	}
};
