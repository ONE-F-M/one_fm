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
		var days,management_fee_percentage,management_fee;
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
		frm.set_query("price_list", function() {
			return {
				"filters": {
					//"customer": frm.doc.client,
					"selling": 1
				}
			};
		});
		frm.refresh_field("price_list");
		frm.fields_dict['items'].grid.get_field('item_code').get_query = function() {
            return {
                filters:{
					is_stock_item: 0,
					is_sales_item: 1,
                    disabled: 0
                }
            }
        }
		frm.fields_dict['items'].grid.get_field('item_price').get_query = function(frm, cdt, cdn) {
            let d = locals[cdt][cdn];
            return {
                filters:{
					price_list: cur_frm.doc.price_list,
                    customer: cur_frm.doc.client,
					selling: 1,
                    item_code: d.item_code
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
		days = frappe.meta.get_docfield("Contract Item","days", frm.doc.name);
		days.hidden = 1;
		management_fee_percentage = frappe.meta.get_docfield("Contract Item","management_fee_percentage", frm.doc.name);
		management_fee = frappe.meta.get_docfield("Contract Item","management_fee", frm.doc.name);
		if(!frm.doc.is_invoice_for_airport){
			management_fee_percentage.hidden = 1;
			management_fee.hidden = 1;
		}
		if(frm.doc.is_invoice_for_airport){
			management_fee_percentage.hidden = 0;
			management_fee.hidden = 0;
		}
		frm.refresh_field("items");

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
	},
	is_invoice_for_airport: function(frm){
		var management_fee_percentage,management_fee;
		management_fee_percentage = frappe.meta.get_docfield("Contract Item","management_fee_percentage", frm.doc.name);
		management_fee = frappe.meta.get_docfield("Contract Item","management_fee", frm.doc.name);
		if(!frm.doc.is_invoice_for_airport){
			management_fee_percentage.hidden = 1;
			management_fee.hidden = 1;
		}
		else{
			management_fee_percentage.hidden = 0;
			management_fee.hidden = 0;
		}
	},
	engagement_type: (frm)=>{
		// disable is auto renewal if engagement type is one-off
		if(frm.doc.engagement_type=='One-off'){
			frm.toggle_enable('is_auto_renewal', 0);
			frm.toggle_display('is_auto_renewal', 0);
		} else {
			frm.toggle_enable('is_auto_renewal', 1);
			frm.toggle_display('is_auto_renewal', 1);
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
		let d = locals[cdt][cdn];
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
						'description'
					]
				},
				callback:function(s){
					if (!s.exc) {
						if(s.message){
							frappe.model.set_value(d.doctype, d.name, "item_name", s.message.description);
							frm.refresh_field("items");
						}
					}
				}
			});
			frappe.model.set_value(d.doctype, d.name, "item_price", null);
			frappe.model.set_value(d.doctype, d.name, "uom", null);
			frappe.model.set_value(d.doctype, d.name, "gender", null);
			frappe.model.set_value(d.doctype, d.name, "shift_hours", 0);
			frappe.model.set_value(d.doctype, d.name, "days_off", 0);
			frappe.model.set_value(d.doctype, d.name, "price_list_rate", 0);
			frappe.model.set_value(d.doctype, d.name, "rate", 0);
		}

	},
	management_fee_percentage: function(frm, cdt, cdn){
		let d = locals[cdt][cdn];
		let management_fee = d.price_list_rate * (flt(d.management_fee_percentage / 100))
		frappe.model.set_value(d.doctype, d.name, "management_fee", management_fee);
		frappe.model.set_value(d.doctype, d.name, "rate", d.price_list_rate + management_fee);
		frm.refresh_field("items");
	},
})
frappe.ui.form.on('Contract Asset', {
	item_code: function(frm, cdt, cdn) {
		let d = locals[cdt][cdn];
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
						'stock_uom',
						'sales_uom'
					]
				},
				callback:function(s){
					if (!s.exc) {
						if(s.message){
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
		if(d.item_code && d.uom){
			frappe.call({
				method: 'frappe.client.get_value',
				args:{
					'doctype':'Item Price',
					'filters':{
						'item_code': d.item_code,
						'price_list': frm.doc.price_list,
						'customer': frm.doc.client,
						'uom': d.uom,
						'selling': 1
					},
					'fieldname':[
						'price_list_rate'
					]
				},
				callback:function(s){
					if (!s.exc) {
						if(s.message){
							frappe.model.set_value(d.doctype, d.name, "unit_rate", s.message.price_list_rate);
							frm.refresh_field("assets");
						}
						else{
							frappe.model.set_value(d.doctype, d.name, "unit_rate", 0);
							frappe.msgprint("Rate not found for item" + d.item_code)
						}
					}
				}
			});
		}

	},
	uom: function(frm, cdt, cdn){
		let d = locals[cdt][cdn];
		if(d.item_code && d.uom){
			frappe.call({
				method: 'frappe.client.get_value',
				args:{
					'doctype':'Item Price',
					'filters':{
						'item_code': d.item_code,
						'price_list': frm.doc.price_list,
						'customer': frm.doc.client,
						'uom': d.uom,
						'selling': 1
					},
					'fieldname':[
						'price_list_rate'
					]
				},
				callback:function(s){
					if (!s.exc) {
						if(s.message){
							frappe.model.set_value(d.doctype, d.name, "unit_rate", s.message.price_list_rate);
							frm.refresh_field("assets");
						}
						else{
							frappe.model.set_value(d.doctype, d.name, "unit_rate", 0);
							frappe.msgprint("Rate not found for item" + d.item_code)
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
