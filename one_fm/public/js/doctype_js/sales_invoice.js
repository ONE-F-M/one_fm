frappe.ui.form.on('Sales Invoice', {
    validate: function(frm){
        if(frm.doc.project){
            frappe.call({
                method: 'frappe.client.get_value',
                args:{
                    'doctype':'Project',
                    'filters':{
                        'name': frm.doc.project
                    },
                    'fieldname':[
                        'income_account',
                        'cost_center'
                    ]
                },
                callback:function(s){
                    if (!s.exc) {
                        $.each(frm.doc.items || [], function(i, v) {
                            frappe.model.set_value(v.doctype, v.name,"income_account",s.message.income_account)
                            frappe.model.set_value(v.doctype, v.name,"cost_center",s.message.cost_center)
                        })
                        frm.refresh_field("items");
                    }
                }
            });
        }      
    },
	refresh(frm) {
        frm.set_df_property('contracts', 'read_only', 1);
        frm.cscript.delivery_note_btn = function() {
            var me = this;
            this.$delivery_note_btn = this.frm.add_custom_button(__('Delivery Note'),
                function() {
                    erpnext.utils.map_current_doc({
                        method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
                        source_doctype: "Delivery Note",
                        target: me.frm,
                        date_field: "posting_date",
                        setters: {
                            customer: me.frm.doc.customer || undefined,
                            project: me.frm.doc.project || undefined
                        },
                        get_query: function() {
                            var filters = {
                                docstatus: 1,
                                company: me.frm.doc.company,
                                is_return: 0
                            };
                            if(me.frm.doc.customer) filters["customer"] = me.frm.doc.customer;
                            return {
                                query: "one_fm.one_fm.delivery_note_custom.get_delivery_notes_to_be_billed",
                                filters: filters
                            };
                        }
                    });
                }, __("Get items from"));
        }
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
        frm.fields_dict['items'].grid.get_field('income_account').get_query = function() {
            return {    
                filters:{
                    root_type:'Income',
                    is_group: 0
                }
            }
        }
        frm.refresh_field("items");
    },
    customer: function(frm){
        if(frm.doc.project){
            frappe.call({
                method: 'frappe.client.get_value',
                args:{
                    'doctype':'Price List',
                    'filters':{
                        'project': frm.doc.project,
                        'enabled':1,
                        'selling':1
                    },
                    'fieldname':[
                        'name'
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
                    'doctype':'Price List',
                    'filters':{
                        'project': frm.doc.project,
                        'enabled':1,
                        'selling':1
                    },
                    'fieldname':[
                        'name'
                    ]
                },
                callback:function(s){
                    if (!s.exc) {
                        //console.log(s.message);
                        if(s.message){
                            var selling_price_list = s.message.name;
                            frm.set_value("selling_price_list",selling_price_list);
                            frm.refresh_field("selling_price_list");
                        }
                        else{
                            frm.set_value("selling_price_list",null);
                            frm.refresh_field("selling_price_list");
                        }
                    }
                }
            });
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
                        //console.log(s.message);
                        if(s.message){
                            var contracts = s.message.name;
                            frm.set_value("contracts",contracts);
                            frm.refresh_field("contracts");
                        }
                    }
                }
            });
        }
    },
    contracts: function(frm,cdt,cdn){
        if(frm.doc.contracts){
            frappe.call({
                method: "one_fm.operations.doctype.contracts.contracts.get_contracts_items",
                args:{
                    'contracts': frm.doc.contracts
                },
                callback:function(s){
                    if(!s.exc){
                        if(s.message != undefined){
                            frm.clear_table("items");
                            frm.refresh_field("items");
                            for (var i=0; i<s.message.length; i++){
                                var d = frm.add_child("items");
                                var item = s.message[i];
                                frappe.model.set_value(d.doctype, d.name, "item_code", item.item_code);
                                frappe.model.set_value(d.doctype, d.name, "qty", item.qty);
                                frappe.model.set_value(d.doctype, d.name, "uom", item.uom);
                                frm.refresh_field("items");
                            }
                        }                      
                    }
                }
            })
        }
    }
});
