$.extend(frappe.meta, {
    // get_print_formats: function(doctype) {
    //     var print_format_list = ["Standard"];
    //     var default_print_format = locals.DocType[doctype].default_print_format;
    //     let enable_raw_printing = frappe.model.get_doc(":Print Settings", "Print Settings").enable_raw_printing;
    //     var print_formats = frappe.get_list("Print Format", {doc_type: doctype})
    //         .sort(function(a, b) { return (a > b) ? 1 : -1; });
    //     $.each(print_formats, function(i, d) {
    //         if (
    //             !in_list(print_format_list, d.name)
    //             && d.print_format_type !== 'JS'
    //             && (cint(enable_raw_printing) || !d.raw_printing)
    //         ) {
    //             print_format_list.push(d.name);
    //         }
    //     });

    //     if(default_print_format && default_print_format != "Standard") {
    //         var index = print_format_list.indexOf(default_print_format);
    //         print_format_list.splice(index, 1).sort();
    //         print_format_list.unshift(default_print_format);
    //     }

    //     if(cur_frm.doc.format){ //newly added if condition
    //         var index = print_format_list.indexOf(cur_frm.doc.format);
    //         print_format_list.splice(index, 1).sort();
    //         print_format_list.unshift(cur_frm.doc.format);
    //     }

    //     return print_format_list;
    // },
});
frappe.ui.form.on('Sales Invoice', {
    validate: function(frm){
        if(frm.doc.__islocal || frm.doc.docstatus==0){
            if(frm.doc.project){
                // set_income_account_and_cost_center(frm);
            }
        }
        
    },
	refresh(frm) {
        if(frm.doc.customer){
            frm.set_query("project", function() {
                return {
                    filters:{
                        customer: frm.doc.customer
                    }
                };
            });
            frm.refresh_field("project");
            fetch_advances(frm)
            
            
            
        }
        
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
        // filter contracts
        frm.set_query('contracts', () => {
            frm.set_value('contracts', '');
            return {
                filters: {
                    client: frm.doc.customer,
                    workflow_state: 'Active'
                }
            }
        })
    },
    project: function(frm){
        //clear timesheet detalis and total billing amount
        frm.clear_table("timesheets");
        frm.set_value("total_billing_amount",null);
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
                        
                        if(frm.doc.selling_price_list == null){
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

    contracts: function(frm){
        if(frm.doc.contracts){
            
            frm.clear_table("items");
            frm.refresh_field("items");
            //get contracts service items
            get_contracts_items(frm);
            //get contracts consumable items
            get_contracts_asset_items(frm);
        }
    },
    // add_timesheet_amount: function(frm){
    //     add_timesheet_rate(frm);
    // }
});
// frappe.ui.form.on('Sales Invoice Item', {
//     item_code:function(frm,cdt,cdn){
//         var d = locals[cdt][cdn];
//         frappe.call({
//             method: 'frappe.client.get_value',
//             args:{
//                 'doctype':'Item',
//                 'filters':{
//                     'item_code': d.item_code,
//                 },
//                 'fieldname':[
//                     'is_stock_item'
//                 ]
//             },
//             callback:function(s){
//                 if (!s.exc) {
//                     if(s.message != undefined){
//                         if(s.message.is_stock_item == 0){
//                             get_timesheet_details(frm,d.item_code);
//                         }
//                     }
//                 }
//             }
//         });  
//         //frappe.model.set_value(d.doctype, d.name,"test_item",d.item_code);
//     }
// });
var set_income_account_and_cost_center = function(frm){
    
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
};
let settle_invoice = function(d,frm){ 
    let values = d.get_values()
    if (values.settlement_amount >= values.total_advance_amount){
        frappe.throw("Settlement Amount cannot be greater than the total advance amount")
    }
    if (values.settlement_amount > values.outstanding){
        frappe.throw("Settlement Amount cannot be greater than the total outstanding amount")
    }
    
    frappe.call({
        method: 'one_fm.one_fm.sales_invoice_custom.allocate_advances',
        args:{
            'frm_id':frm.doc.name,
            'amount':values.settlement_amount
        },
        callback:function(s){
            if (!s.exc) {
               frappe.msgprint("Allocations Made Successfully")
            }
            }
        });

    d.hide();
}
let settle_advances = function(frm){
    
    if((frm.doc.docstatus == 1) && (frm.doc.outstanding_amount>0) && (frm.doc.balance_in_advance_account>0)){
    
        cur_frm.add_custom_button(__("Payment from Unearned Revenue"), function(){
            var d = new frappe.ui.Dialog({
                'fields': [
                    {'fieldname': 'customer_name', 'fieldtype': 'Data','read_only':1,'label':'Customer Name','default':frm.doc.customer_name},
                    {'fieldname': 'outstanding', 'fieldtype': 'Currency','read_only':1,'label':'Outstading Amount','default':frm.doc.outstanding_amount},
                    {'fieldname': 'total_advance_amount','read_only':1, 'fieldtype': 'Currency','label':'Total Advance Amount','default':frm.doc.balance_in_advance_account},
                    {'fieldname': 'settlement_amount', 'fieldtype': 'Currency','label':'Settlement Amount'},
                   
                ],
                primary_action: function(){
                    settle_invoice(d,frm);
                }
            });
            
            d.show();
        }, __("Create"));
    }
    
}

let fetch_advances  =  function(frm){
    if((frm.doc.customer) && (!frm.doc.name.includes("new"))){
        frappe.call({
            method: 'one_fm.one_fm.sales_invoice_custom.get_customer_advance_balance',
            args:{
                'customer':frm.doc.customer,
            },
            callback:function(s){
                if (!s.exc) {
                    frm.doc.balance_in_advance_account = s.message
                    // frm.doc.automatic_settlement = ""
                    // frm.doc.settlement_amount = ""
                    frm.refresh_field('balance_in_advance_account')
                    frm.refresh_field('settlement_amount')
                    if((frm.doc.balance_in_advance_account> 1)  && !(frm.doc.active_modal)){
                        frm.doc.active_modal = 1
                        frm.set_intro(`${frm.doc.customer} has ${cur_frm.doc.currency}${cur_frm.doc.balance_in_advance_account} in their advance account.\nYou can use it to settle this invoice by setting the 
                        'Settle From Unearned Revenue' field to Yes. If the form is submitted, Click on 'Payment from Unearned Revenue' button in the Create button grid`)
                        settle_advances(frm)
                    }
                }
            }
        });
    }
}
//Add timesheet amount
var add_timesheet_rate = function(frm){
    
    $.each(frm.doc.items || [], function(i, v) {
        var amount = 0;
        $.each(frm.doc.timesheets || [], function(i, d) {
            if(d.item == v.item_code){
                amount += d.billing_amount;
            }
        })
        if(amount != 0){
            frappe.model.set_value(v.doctype, v.name,"rate",flt(amount/v.qty))
        }
    })
    frm.refresh_field("items");
};
var get_timesheet_details =  function(frm,item) {
    frappe.call({
        method: 'one_fm.one_fm.sales_invoice_custom.get_projectwise_timesheet_data',
        args:{
            'project': frm.doc.project,
            'item_code': item,
            'posting_date': frm.doc.posting_date
        },
        callback:function(s){
            if (!s.exc) {
                
                if(s.message != undefined && s.message.length > 0){
                    add_timesheet_data(frm,s.message,item);
                }
            }
        }
    });
};
var add_timesheet_data = function(frm,timesheet_data,item_code){
    for (var i=0; i<timesheet_data.length; i++){
        var d = frm.add_child("timesheets");
        var item = timesheet_data[i];
        frappe.model.set_value(d.doctype, d.name, "time_sheet", item.parent);
        frappe.model.set_value(d.doctype, d.name, "billing_hours", item.billing_hours);
        frappe.model.set_value(d.doctype, d.name, "billing_amount", item.billing_amt);
        frappe.model.set_value(d.doctype, d.name, "timesheet_detail", item.name);
        frappe.model.set_value(d.doctype, d.name, "item", item_code);
        frm.refresh_field("timesheets");
    }
};
var get_contracts_asset_items = function(frm){
    
    frappe.call({
        method: "one_fm.operations.doctype.contracts.contracts.get_contracts_asset_items",
        args:{
            'contracts': frm.doc.contracts
        },
        callback:function(s){
            if(!s.exc){
                if(s.message != undefined){
                   
                    for (var i=0; i<s.message.length; i++){
                        var d = frm.add_child("items");
                        var item = s.message[i];
                        //facing challange here
                        //d.item_code = item.item_code;
                        //d.qty = item.qty;
                        //d.uom = item.uom;
                        frappe.model.set_value(d.doctype, d.name, "item_code", item.item_code);
                        frappe.model.set_value(d.doctype, d.name, "qty", item.qty);
                        //frappe.model.set_value(d.doctype, d.name, "uom", item.uom);
                        frm.refresh_field("items");
                    }
                    //loop again and set qty and uom .....not good
                }                      
            }
        }
    })
};
var get_contracts_items = function(frm){
    
    frappe.call({
        method: "one_fm.operations.doctype.contracts.contracts.get_contracts_items",
        args:{
            'contracts': frm.doc.contracts
        },
        callback:function(s){
            if(!s.exc){
                if(s.message != undefined){
                    
                    
                    $.each(s.message, function(i, d) {
                        var row = frappe.model.add_child(frm.doc, "Sales Invoice Item", "items");
                        frappe.model.set_value(row.doctype, row.name, "item_code", d.item_code)
                        frappe.model.set_value(row.doctype, row.name, "qty", d.qty)
                        frappe.model.set_value(row.doctype, row.name, "rate", d.price_list_rate)
                        frappe.model.set_value(row.doctype, row.name, "uom", d.uom)
                    });
                    
                }                      
            }
        }
    })
};
