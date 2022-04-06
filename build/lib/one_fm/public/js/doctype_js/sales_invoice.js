$.extend(frappe.meta, {
    get_print_formats: function(doctype) {
        var print_format_list = ["Standard"];
        var default_print_format = locals.DocType[doctype].default_print_format;
        let enable_raw_printing = frappe.model.get_doc(":Print Settings", "Print Settings").enable_raw_printing;
        var print_formats = frappe.get_list("Print Format", {doc_type: doctype})
            .sort(function(a, b) { return (a > b) ? 1 : -1; });
        $.each(print_formats, function(i, d) {
            if (
                !in_list(print_format_list, d.name)
                && d.print_format_type !== 'JS'
                && (cint(enable_raw_printing) || !d.raw_printing)
            ) {
                print_format_list.push(d.name);
            }
        });

        if(default_print_format && default_print_format != "Standard") {
            var index = print_format_list.indexOf(default_print_format);
            print_format_list.splice(index, 1).sort();
            print_format_list.unshift(default_print_format);
        }

        if(cur_frm.doc.format){ //newly added if condition
            var index = print_format_list.indexOf(cur_frm.doc.format);
            print_format_list.splice(index, 1).sort();
            print_format_list.unshift(cur_frm.doc.format);
        }

        return print_format_list;
    },
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
        frm.set_df_property('contracts', 'read_only', 1);
        // frm.cscript.delivery_note_btn = function() {
        //     var me = this;
        //     this.$delivery_note_btn = this.frm.add_custom_button(__('Delivery Note'),
        //         function() {
        //             erpnext.utils.map_current_doc({
        //                 method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
        //                 source_doctype: "Delivery Note",
        //                 target: me.frm,
        //                 date_field: "posting_date",
        //                 setters: {
        //                     customer: me.frm.doc.customer || undefined,
        //                     project: me.frm.doc.project || undefined
        //                 },
        //                 get_query: function() {
        //                     var filters = {
        //                         docstatus: 1,
        //                         company: me.frm.doc.company,
        //                         is_return: 0
        //                     };
        //                     if(me.frm.doc.customer) filters["customer"] = me.frm.doc.customer;
        //                     return {
        //                         query: "one_fm.one_fm.delivery_note_custom.get_delivery_notes_to_be_billed",
        //                         filters: filters
        //                     };
        //                 }
        //             });
        //         }, __("Get items from"));
        // }

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
        // frm.fields_dict['items'].grid.get_field('income_account').get_query = function() {
        //     return {
        //         filters:{
        //             root_type:'Income',
        //             is_group: 0
        //         }
        //     }
        // }
        // frm.refresh_field("items");
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
    // contracts: function(frm){
    //     if(frm.doc.contracts){
    //         frm.clear_table("items");
    //         frm.refresh_field("items");
    //         //get contracts service items
    //         get_contracts_items(frm);
    //         //get contracts consumable items
    //         get_contracts_asset_items(frm);
    //     }
    // },
    // add_timesheet_amount: function(frm){
    //     // add_timesheet_rate(frm);
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
//         frappe.model.set_value(d.doctype, d.name,"test_item",d.item_code);
//     }
// });
//
// var set_income_account_and_cost_center = function(frm){
//     console.log('set_income_account_and_cost_center');
//     frappe.call({
//         method: 'frappe.client.get_value',
//         args:{
//             'doctype':'Project',
//             'filters':{
//                 'name': frm.doc.project
//             },
//             'fieldname':[
//                 'income_account',
//                 'cost_center'
//             ]
//         },
//         callback:function(s){
//             if (!s.exc) {
//                 $.each(frm.doc.items || [], function(i, v) {
//                     frappe.model.set_value(v.doctype, v.name,"income_account",s.message.income_account)
//                     frappe.model.set_value(v.doctype, v.name,"cost_center",s.message.cost_center)
//                 })
//                 frm.refresh_field("items");
//             }
//         }
//     });
// };
//Add timesheet amount
// var add_timesheet_rate = function(frm){
//     console.log('add_timesheet_rate.........event');
//     $.each(frm.doc.items || [], function(i, v) {
//         var amount = 0;
//         $.each(frm.doc.timesheets || [], function(i, d) {
//             if(d.item == v.item_code){
//                 amount += d.billing_amount;
//             }
//         })
//         if(amount != 0){
//             frappe.model.set_value(v.doctype, v.name,"rate",flt(amount/v.qty))
//         }
//     })
//     frm.refresh_field("items");
// };
// var get_timesheet_details =  function(frm,item) {
//     frappe.call({
//         method: 'one_fm.one_fm.sales_invoice_custom.get_projectwise_timesheet_data',
//         args:{
//             'project': frm.doc.project,
//             'item_code': item,
//             'posting_date': frm.doc.posting_date
//         },
//         callback:function(s){
//             if (!s.exc) {
//                 console.log(s.message);
//                 if(s.message != undefined && s.message.length > 0){
//                     add_timesheet_data(frm,s.message,item);
//                 }
//             }
//         }
//     });
// };
// var add_timesheet_data = function(frm,timesheet_data,item_code){
//     for (var i=0; i<timesheet_data.length; i++){
//         var d = frm.add_child("timesheets");
//         var item = timesheet_data[i];
//         frappe.model.set_value(d.doctype, d.name, "time_sheet", item.parent);
//         frappe.model.set_value(d.doctype, d.name, "billing_hours", item.billing_hours);
//         frappe.model.set_value(d.doctype, d.name, "billing_amount", item.billing_amt);
//         frappe.model.set_value(d.doctype, d.name, "timesheet_detail", item.name);
//         frappe.model.set_value(d.doctype, d.name, "item", item_code);
//         frm.refresh_field("timesheets");
//     }
// };
// var get_contracts_asset_items = function(frm){
//     console.log('get_contracts_asset_items');
//     frappe.call({
//         method: "one_fm.operations.doctype.contracts.contracts.get_contracts_asset_items",
//         args:{
//             'contracts': frm.doc.contracts
//         },
//         callback:function(s){
//             if(!s.exc){
//                 if(s.message != undefined){
//                     console.log(s.message);
//                     for (var i=0; i<s.message.length; i++){
//                         var d = frm.add_child("items");
//                         var item = s.message[i];
//                         //facing challange here
//                         //d.item_code = item.item_code;
//                         //d.qty = item.qty;
//                         //d.uom = item.uom;
//                         frappe.model.set_value(d.doctype, d.name, "item_code", item.item_code);
//                         frappe.model.set_value(d.doctype, d.name, "qty", item.qty);
//                         //frappe.model.set_value(d.doctype, d.name, "uom", item.uom);
//                         frm.refresh_field("items");
//                     }
//                     //loop again and set qty and uom .....not good
//                 }
//             }
//         }
//     })
// };
// var get_contracts_items = function(frm){
//     console.log('get_contracts_items');
//     frappe.call({
//         method: "one_fm.operations.doctype.contracts.contracts.get_contracts_items",
//         args:{
//             'contracts': frm.doc.contracts
//         },
//         callback:function(s){
//             if(!s.exc){
//                 if(s.message != undefined){
//                     console.log(s.message);
//                     for (var i=0; i<s.message.length; i++){
//                         var d = frm.add_child("items");
//                         var item = s.message[i];
//                         frappe.model.set_value(d.doctype, d.name, "item_code", item.item_code);
//                         frappe.model.set_value(d.doctype, d.name, "qty", item.qty);
//                         //frappe.model.set_value(d.doctype, d.name, "uom", item.uom);
//                         frm.refresh_field("items");
//                     }
//                 }
//             }
//         }
//     })
// };
