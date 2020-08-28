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
							reqd: 1},
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
				msgprint('Password Managemet is already exist for this contract');
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
	}
});

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
