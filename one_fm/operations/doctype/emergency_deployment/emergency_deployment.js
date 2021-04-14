// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Emergency Deployment', {
	refresh: function(frm){
		frm.set_query("project", function() {
			return {
				filters:{
					project_type: 'External',
					customer: frm.doc.customer
										
				}
			};
		});
		frm.refresh_field("project");
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
	},
	project: function(frm){
		if(frm.doc.project){
			frappe.call({
				method: 'frappe.client.get_value',
				args:{
					'doctype':'Contracts',
					'filters':{
						'project': frm.doc.project
					},
					'fieldname':[
						'name',
						'due_date'
					]
				},
				callback:function(s){
					if (!s.exc) {
						if(s.message){
							frm.set_value("contracts",s.message.name);
							frm.set_value("due_date",s.message.due_date);
							frm.refresh_field("contracts");
							frm.refresh_field("due_date");
						}
					}
				}
			});
		}
	}
});
