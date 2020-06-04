// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Operations Site', {
	refresh: function(frm){
		frm.set_query("project", function() {
			return {
				"filters": [
					["Project", "project_type", "=", "External"],
				]
			}
		});

		// Remove and change it
		let {changes_log} = frm.doc;
		let changes = ``;
		let ids = ``;
		if(changes_log.length > 0){
			for(let i=0;i<changes_log.length;i++){
				let {name, message, assigned_to} = changes_log[i]
				if(assigned_to == frappe.session.user){
					changes += `<span>${message}<span>\n`;
					ids += `${name},`;
				}
			}
		}
		console.log(changes);
		if(changes && ids){
			frm.add_custom_button(
				__('Review Changes'),
				() => {
					frappe.confirm(
						changes,
						function(){
							frappe.msgprint(__('Changes approved.'));
							changes_action(frm, "Approved", ids);
							window.close();
							// frm.reload_doc();
						},
						function(){
							frappe.msgprint(__('You have rejected the changes. They have been reverted.'));
							changes_action(frm, "Rejected", ids);
							window.close();
							// frm.reload_doc();
						}
					)
				}
			).addClass('btn-primary');		
		}			
	},
})

function changes_action(frm, action, ids){
	frappe.call('one_fm.operations.doctype.operations_site.operations_site.changes_action', {
		action, ids, parent: frm.doc.name
	}).then((r) => {
		console.log(r);
		frm.reload_doc();
	});
}
frappe.ui.form.on('POC', {
	form_render: function(frm, cdt, cdn) {
		let doc = locals[cdt][cdn];
		if(doc.poc !== undefined){
			get_contact(doc);
		}
	},
	before_poc_remove: function(frm, cdt, cdn){
		if(!frappe.user_roles.includes("Shift Supervisor") && !frappe.user_roles.includes("Site Supervisor")){
			frappe.throw(__("You are not allowed to make changes to POC list."))
		}
	},
	poc: function(frm, cdt, cdn){
		let doc = locals[cdt][cdn];
		if(doc.poc !== undefined){
			get_contact(doc);
		}
	}
});

function get_contact(doc){
	let operations_site_poc = doc.poc;
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Contact',
			name: operations_site_poc
		},
		callback: function(r) {
			if(!r.exc) {
				set_contact(r.message);
			}
		}
	});
}

function set_contact(doc){
	let {email_ids, phone_nos} = doc;
	console.log(email_ids, phone_nos);
	let contact_details = ``;
	for(let i=0; i<email_ids.length;i++){
		contact_details += `<p>Email: ${email_ids[i].email_id}</p>\n`;
	}

	for(let j=0; j<phone_nos.length;j++){
		contact_details += `<p>Phone: ${phone_nos[j].phone}</p>\n`;
	}
	console.log(contact_details);
	$('div[data-fieldname="contact_html"]').empty().append(`<div class="address-box">${contact_details}</div>`);
}

