// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site', {
	refresh: function(frm) {
		if(frm.doc.site_poc !== undefined){
			get_contact(frm);
		}
	},
	site_poc: function(frm){
		if(frm.doc.site_poc !== undefined){
			get_contact(frm);
		}
	}
});

function get_contact(frm){
	let site_poc = frm.doc.site_poc;
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Contact',
			name: site_poc
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