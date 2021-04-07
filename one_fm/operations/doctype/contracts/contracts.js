// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

var values = '';

function open_form(frm, doctype, child_doctype, parentfield) {
	frappe.model.with_doctype(doctype, () => {
        let new_doc = frappe.model.get_new_doc(doctype);
        new_doc.type  = 'Contracts';
		new_doc.customer = frm.doc.client;
		new_doc.project = frm.doc.project;

		frappe.ui.form.make_quick_entry(doctype, null, null, new_doc);
	});

}
frappe.ui.form.on('Contracts', {
	setup(frm) {
		frm.make_methods = {
			'Sales Invoice': () => {
				open_form(frm, "Sales Invoice", null, null);
			},
			'Delivery Note': () => {
				open_form(frm, "Delivery Note", null, null);
			},
		};
	},
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
		if(!frm.doc.client || !frm.doc.project || !frm.doc.start_date){
			frappe.msgprint({
				title: __('Value Missing Error'),
				indicator: 'red',
				message: __('You have to fill Client, Project and Contract Start Date Before Saving a Contract.')
			});
			validated = false;
		}
		if(frm.doc.end_date){
			if(frm.doc.end_date < frm.doc.start_date){
				frappe.msgprint({
					title: __('Validation Error'),
					indicator: 'red',
					message: __('Contract End Date Cannot be before Contracts Start Date.')
				});
				validated = false;
			}
		}
	},
	refresh:function(frm){
		frm.set_query("bank_account", function() {
			return {
				"filters": {
					"party_type": 'Customer',
					"party": frm.doc.client
				}
			};
		});
		frm.refresh_field("bank_account");			
		frm.set_query("project", function() {
			return {
				filters:{
					project_type: 'External',
					customer: frm.doc.client
										
				}
			};
		});
		frm.refresh_field("project");
		frm.set_query("customer_address", function() {
			return {
				"filters": {
					"link_doctype": 'Customer',
					"link_name": frm.doc.client
				}
			};
		});
		frm.refresh_field("customer_address");
		frm.fields_dict['items'].grid.get_field('item_code').get_query = function() {
            return {    
                filters:{
					is_stock_item: 0,
					is_sales_item: 1,
                    disabled: 0
                }
            }
        }
		frm.refresh_field("items");
		frm.fields_dict['assets'].grid.get_field('item_code').get_query = function() {
            return {    
                filters:{
					is_stock_item: 1,
					is_sales_item: 1,
                    disabled: 0
                }
            }
		}
		frm.fields_dict['assets'].grid.get_field('site').get_query = function() {
            return {    
                filters:{
					project: frm.doc.project
                }
            }
        }
        frm.refresh_field("assets");
		var days = frappe.meta.get_docfield("Contract Item","days", frm.doc.name);
		days.hidden = 1;
		frm.refresh_field("items");
	},
	customer_address:function(frm){
		if(frm.doc.customer_address){
			erpnext.utils.get_address_display(frm, 'customer_address', 'address_display')
		}
	},
	project: function(frm){
		if(frm.doc.project){
			frappe.call({
				method: 'frappe.client.get_value',
				args:{
					'doctype':'Price List',
					'filters':{
						'project': frm.doc.project,
						'enabled': 1,
						'selling': 1
					},
					'fieldname':[
						'name'
					]
				},
				callback:function(s){
					if (!s.exc) {
						if(s.message){
							frm.set_value("price_list",s.message.name);
							frm.refresh_field("price_list");
						}
					}
				}
			});
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

frappe.ui.form.on('Contract Item', {
	item_code: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.item_code){
			frappe.call({
				method: 'frappe.client.get_value',
				args:{
					'doctype':'Item',
					'filters':{
						'item_code': d.item_code,
						'disabled': 0,
					},
					'fieldname':[
						'item_name'
					]
				},
				callback:function(s){
					if (!s.exc) {
						if(s.message){
							frappe.model.set_value(d.doctype, d.name, "item_name", s.message.item_name);
							frm.refresh_field("items");
						}
					}
				}
			});
		}

	}
})
frappe.ui.form.on('Contract Asset', {
	item_code: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.item_code){
			frappe.call({
				method: 'frappe.client.get_value',
				args:{
					'doctype':'Item',
					'filters':{
						'item_code': d.item_code,
						'disabled': 0,
					},
					'fieldname':[
						'item_name',
						'stock_uom',
						'sales_uom'
					]
				},
				callback:function(s){
					if (!s.exc) {
						if(s.message){
							console.log(s.message);
							frappe.model.set_value(d.doctype, d.name, "item_name", s.message.item_name);
							if(s.message.sales_uom != undefined){
								frappe.model.set_value(d.doctype, d.name, "uom", s.message.sales_uom);
							}
							else{
								frappe.model.set_value(d.doctype, d.name, "uom", s.message.stock_uom);
							}
							frm.refresh_field("assets");
						}
					}
				}
			});
		}

	}
})

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
