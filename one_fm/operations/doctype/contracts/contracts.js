// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

var values = '';

frappe.ui.form.on('Contracts', {
	use_portal_for_invoice:function(frm){
		if(frm.doc.use_portal_for_invoice){
			if(!frm.doc.password_management){
				var d = new frappe.ui.Dialog({
					title: __("Online Portal Credentials"),
					fields: [
						{"fieldname":"url", "fieldtype":"Data", "label":__("URL"),
							"default" : "https://",reqd: 1},
						{"fieldname":"user_name", "fieldtype":"Data", "label":__("User Name"),
							reqd: 1},
						{"fieldname":"password", "fieldtype":"Password", "label":__("Password"),
							reqd: 1},
						{"fieldname":"client", "fieldtype":"Link","options":"Customer", "label":__("Client"),
							"default":frm.doc.client,reqd: 1,hidden:1},
					]
				});
				d.set_primary_action(__("Save"),function(){
					values = d.get_values();
					d.hide();
				})
				d.show()
			}
			else{
				msgprint('Password Management is already exist for this contract');
			}
		}
	},
	before_save:function(frm){
		if(frm.doc.use_portal_for_invoice && !frm.doc.password_management){
			frappe.call({
				method: "one_fm.operations.doctype.contracts.contracts.insert_login_credential",
				args: values,
				callback: function(r) {
					if(!r.exc){
						frm.set_value("password_management",r.message.name);
						frm.refresh_field("password_management");
					}
				}
			});
		}
	},
	validate: function(frm){
		
	},
	client: function(frm) {
		let client = frm.doc.client;
		if(client != undefined){
			frm.set_query("project", function() {
				return {
					"filters": {
						"customer": client,
						"project_type": 'External'
					}
				};
			});
			frm.set_query("customer_address", function() {
				return {
					"filters": {
						"link_doctype": 'Customer',
						"link_name": client
					}
				};
			});
			frm.refresh_field("customer_address");
			frm.set_query("bank_account", function() {
				return {
					"filters": {
						"party_type": 'Customer',
						"party": client
					}
				};
			});
			frm.refresh_field("bank_account");
		}
		else{
			frm.set_query("project", function() {
				return {
					"filters": {
						"project_type": 'External'
					}
				};
			});
		}
		frm.refresh_field("project");
	},
	refresh:function(frm){
		if(!frm.doc.client){
			frm.set_query("project", function() {
				return {
					filters:{
						project_type: 'External'					
					}
				};
			});
			frm.refresh_field("project");
		}
	},
	customer_address:function(frm){
		if(frm.doc.customer_address){
			erpnext.utils.get_address_display(frm, 'customer_address', 'address_display')
		}
	},
	bank_account:function(frm){
		if(frm.doc.bank_account){
			frappe.call({
				method: 'frappe.client.get_value',
				args:{
					'doctype':'Bank Account',
					'filters':{
						'name': frm.doc.bank_account
					},
					'fieldname':[
						'bank',
						'iban'
					]
				},
				callback:function(s){
					if (!s.exc) {
						frm.set_value("bank_name",s.message.bank);
						frm.set_value("iban",s.message.iban);
						frm.refresh_field("bank_name");
						frm.refresh_field("iban");
					}
				}
			});
		}
	}
});

frappe.ui.form.on('POC', {
	form_render: function(frm, cdt, cdn) {
		let doc = locals[cdt][cdn];
		if(doc.poc !== undefined){
			get_contact(doc);
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

frappe.ui.form.on('Contract Addendum', {
	end_date: function(frm, cdt, cdn) {
		let doc = locals[cdt][cdn];
	},
	addendums_add: function(frm, cdt, cdn){
		let doc = locals[cdt][cdn];
		if(doc.idx == 1){
			frappe.model.set_value(doc.doctype, doc.name, "version", "1.0");
		}else{

		}
	}
})
