frappe.ui.form.on('Delivery Note', {
	refresh(frm) {
        // frm.set_df_property('contracts', 'read_only', 1);
        if(frm.doc.customer){
            frm.set_query("project", function() {
                return {
                    filters:{
                        customer: frm.doc.customer
                    }
                };
            });
            frm.refresh_field("project");
        }
        frm.fields_dict['items'].grid.get_field('site').get_query = function() {
            return {
                filters:{
					project: frm.doc.project
                }
            }
        }
        frm.refresh_field("site");
    },
    customer: function(frm){
        if(frm.doc.project){
            frappe.call({
                method: 'frappe.client.get_value',
                args:{
                    'doctype':'Contracts',
                    'filters':{
                        'name': frm.doc.contracts
                    },
                    'fieldname':[
                        'price_list'
                    ]
                },
                callback:function(s){
                    if (!s.exc) {
                        var selling_price_list = s.message.name;
                        frm.set_value("selling_price_list",selling_price_list);
                        frm.refresh_field("selling_price_list");
                    }
                }
            });
        }
        else{
            frm.set_value("selling_price_list",null);
            frm.refresh_field("selling_price_list");
        }
    },
    project: function(frm){
        if(frm.doc.project){
            frappe.call({
                method: 'frappe.client.get_value',
                args:{
                    'doctype':'Contracts',
                    'filters':{
                        'project': frm.doc.project,
                    },
                    'fieldname':[
                        'name'
                    ]
                },
                callback:function(s){
                    if (!s.exc) {
                        if(s.message){
                            var contracts = s.message.name;
                            frm.set_value("contracts",contracts);
                            frm.refresh_field("contracts");
                        }
                    }
                }
            });
            frappe.call({
                method: 'frappe.client.get_value',
                args:{
                    'doctype':'Contracts',
                    'filters':{
                        'name': frm.doc.contracts
                    },
                    'fieldname':[
                        'price_list'
                    ]
                },
                callback:function(s){
                    if (!s.exc) {
                        var selling_price_list = s.message.name;
                        frm.set_value("selling_price_list",selling_price_list);
                        frm.refresh_field("selling_price_list");
                    }
                }
            });
        }
    }
});
