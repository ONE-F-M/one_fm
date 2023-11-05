// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Candidate Orientation', {
	refresh: function(frm) {

	},
	check_list_template: function(frm) {
		set_check_list(frm);
	}
});

var set_check_list = function(frm) {
	if(frm.doc.check_list_template){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Check List Template',
				filters: {'name': frm.doc.check_list_template}
			},
			callback: function(r) {
				if(r && r.message){
					var data = r.message;
					if(data.check_list){
						data.check_list.forEach((item, i) => {
							var check_list = frm.add_child('candidate_orientation_check_list');
							check_list.check_list = item.check_list
						});
					}
				}
				frm.refresh_field('candidate_orientation_check_list');
			}
		});
	}
}
