// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Magic Link', {
	refresh: function(frm) {
		if (frm.doc.expired != 1 && frm.doc.reference_doctype == "Job Applicant" && (frm.doc.link_for == "Job Applicant" || frm.doc.link_for == "Career History")){
		frm.add_custom_button("Send Magic Link", () =>{
			send_magic_link(frm, "one_fm.hiring.utils.send_magic_link_to_applicant_based_on_link_for")
		});
	}

	}
});


var send_magic_link = function(frm, method) {
	frappe.call({
		method: method,
		args: {
			"name": frm.doc.reference_docname,
			"link_for": frm.doc.link_for
		},
		callback: function(r) {
			if(r && r.message){
				frappe.msgprint(__("Succesfully Send the Magic Link"));
			}
		},
		freeze: true,
		freeze_message: __("Sending the magic link ..!")
	});
};
