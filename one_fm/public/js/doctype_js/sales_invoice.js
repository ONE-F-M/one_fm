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
        setup_contract_item_category_requirements(frm) 
        setup_contract_item_category_filter(frm);
        toggle_items_add_row(frm);
        add_get_items_from_purchase_invoice(frm);
        add_get_items_from_contracts(frm); // Story 2
        show_currency_exchange_info(frm);
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
        
        // Story 3 & 5: Persist rate and currency protection on reload
        let has_contract_item = (frm.doc.items || []).some(d => d.custom_contract_item);
        if (has_contract_item) {
            if (frm.fields_dict.items && frm.fields_dict.items.grid) {
                frm.fields_dict.items.grid.update_docfield_property("rate", "read_only", 1);
            }
            frm.set_df_property("currency", "read_only", 1);
        }

    },
    onload: function(frm){
        toggle_items_add_row(frm);
    },
    custom_contract_item_categorywise_summary_on_form_rendered: function(frm) {
        toggle_items_add_row(frm);
    },
    customer: function(frm){
        setup_contract_item_category_filter(frm);
        clear_contract_categories(frm);
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
        setup_contract_item_category_filter(frm);
        clear_contract_categories(frm);
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
    currency: function(frm) {
        if (frm.doc.currency && frm.doc.company) {
            frappe.call({
                method: "erpnext.setup.utils.get_exchange_rate",
                args: {
                    from_currency: frm.doc.currency,
                    to_currency: frappe.get_doc("Company", frm.doc.company).default_currency,
                    transaction_date: frm.doc.posting_date,
                    args: "for_selling"
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('conversion_rate', r.message);
                    }
                }
            });
        }
    },
    custom_refundable: function(frm) {
        update_all_items_field(frm, 'custom_refundable', frm.doc.custom_refundable);
        setup_contract_item_category_requirements(frm);
        setup_contract_item_category_filter(frm);
    },
    custom_margin_type: function(frm) {
        update_all_items_field(frm, 'margin_type', frm.doc.custom_margin_type);
    },
    custom_margin_rate_or_amount: function(frm) {
        update_all_items_field(frm, 'margin_rate_or_amount', frm.doc.custom_margin_rate_or_amount);
    }


    // add_timesheet_amount: function(frm){
    //     add_timesheet_rate(frm);
    // }
});


frappe.ui.form.on('Sales Invoice Item', {
    items_add: function(frm, cdt, cdn) {
        setup_contract_item_category_requirements(frm);
        
        if (frm.doc.custom_refundable) {
            frappe.model.set_value(cdt, cdn, 'custom_refundable', frm.doc.custom_refundable);
        }
        
        if (frm.doc.custom_margin_type) {
            frappe.model.set_value(cdt, cdn, 'margin_type', frm.doc.custom_margin_type);
        }
        
        if (frm.doc.custom_margin_rate_or_amount) {
            frappe.model.set_value(cdt, cdn, 'margin_rate_or_amount', frm.doc.custom_margin_rate_or_amount);
        }
    },
    
    custom_refundable: function(frm, cdt, cdn) {
        calculate_margin_for_item(frm, cdt, cdn);
    },
    
    margin_type: function(frm, cdt, cdn) {
        calculate_margin_for_item(frm, cdt, cdn);
    },
    
    margin_rate_or_amount: function(frm, cdt, cdn) {
        calculate_margin_for_item(frm, cdt, cdn);
    },
    
    rate: function(frm, cdt, cdn) {
        calculate_margin_for_item(frm, cdt, cdn);
    },
    
    custom_contract_item: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (row.custom_contract_item) {
            frm.fields_dict.items.grid.update_docfield_property("rate", "read_only", 1);
        }
    }
});

frappe.ui.form.on('Sales Taxes and Charges', {
    taxes_add: function(frm, cdt, cdn) {
        // Story 4: Default Add or Deduct to Deduct for new rows (as per Frappe behavior, defaults can also be set from the field property itself)
        frappe.model.set_value(cdt, cdn, 'custom_add_or_deduct', 'Deduct');
    },
    
    custom_add_or_deduct: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        // We only change the sign to ensure it's correct for the chosen operation.
        // On Net Total uses rate as percentage, and Frappe standard expects tax_rate to be positive
        // or negative based on whether it adds or deducts.
        
        let rate = flt(row.rate);
        
        if (row.custom_add_or_deduct === 'Deduct' && rate > 0) {
            frappe.model.set_value(cdt, cdn, 'rate', -rate);
        } else if (row.custom_add_or_deduct === 'Add' && rate < 0) {
            frappe.model.set_value(cdt, cdn, 'rate', Math.abs(rate));
        }
        
        // Also fix tax_amount if it's independently calculated/modified
        let tax_amount = flt(row.tax_amount);
        if (row.custom_add_or_deduct === 'Deduct' && tax_amount > 0) {
            frappe.model.set_value(cdt, cdn, 'tax_amount', -tax_amount);
        } else if (row.custom_add_or_deduct === 'Add' && tax_amount < 0) {
            frappe.model.set_value(cdt, cdn, 'tax_amount', Math.abs(tax_amount));
        }
    },
    
    rate: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        let rate = flt(row.rate);
        
        if (row.custom_add_or_deduct === 'Deduct' && rate > 0) {
            frappe.model.set_value(cdt, cdn, 'rate', -rate);
        }
    },
    
    tax_amount: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        let tax_amount = flt(row.tax_amount);
        
        if (row.custom_add_or_deduct === 'Deduct' && tax_amount > 0) {
            frappe.model.set_value(cdt, cdn, 'tax_amount', -tax_amount);
        }
    }
});


function toggle_items_add_row(frm) {
    if (frm.doc.custom_contract_item_categorywise_summary && 
        frm.doc.custom_contract_item_categorywise_summary.length > 0) {
        frm.set_df_property('items', 'cannot_add_rows', 1);
        frm.fields_dict['items'].grid.cannot_add_rows = true;
        frm.fields_dict['items'].grid.read_only = true;
        frm.refresh_field('items');
    } else {
        frm.set_df_property('items', 'cannot_add_rows', 0);
        frm.fields_dict['items'].grid.cannot_add_rows = false;
        frm.fields_dict['items'].grid.read_only = false;
        frm.refresh_field('items');
    }
}

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

function setup_contract_item_category_requirements(frm) {
    if (frm.doc.custom_refundable) {
        frm.fields_dict.items.grid.update_docfield_property(
            'custom_contract_item_category',
            'only_select',
            1
        );
    }
    
    frm.refresh_field('items');
}


function add_get_items_from_purchase_invoice(frm) {
    if (frm.doc.docstatus === 0) {
        frm.add_custom_button(__('Purchase Invoice'), function() {
            show_purchase_invoice_selector(frm);
        }, __('Get Items From'));
    }
}

function show_purchase_invoice_selector(frm) {
    frappe.call({
        method: 'one_fm.overrides.purchase_invoice.get_all_refundable_purchase_invoices',
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let customers = [...new Set(r.message.map(inv => inv.customer).filter(c => c))];
                customers.sort();
                
                let fields = [
                    {
                        fieldname: 'customer_filter',
                        fieldtype: 'Select',
                        label: __('Filter by Customer'),
                        options: ['All', ...customers],
                        default: 'All',
                        onchange: function() {
                            filter_purchase_invoices(this.value, r.message, dialog);
                        }
                    },
                    {
                        fieldname: 'html_invoices',
                        fieldtype: 'HTML'
                    }
                ];

                let dialog = new frappe.ui.Dialog({
                    title: __('Select Purchase Invoice'),
                    fields: fields,
                    size: 'extra-large',
                    primary_action_label: __('Get Items'),
                    primary_action: function() {
                        let selected = [];
                        dialog.$wrapper.find('input.pi-checkbox:checked').each(function() {
                            selected.push($(this).val());
                        });
                        
                        if (selected.length === 0) {
                            frappe.msgprint(__('Please select at least one Purchase Invoice'));
                            return;
                        }
                        
                        fetch_items_from_purchase_invoices(frm, selected);
                        dialog.hide();
                    }
                });

                let html = build_purchase_invoice_table(r.message);
                dialog.fields_dict.html_invoices.$wrapper.html(html);
                
                setup_select_all_checkbox(dialog);
                
                dialog.show();
            } else {
                frappe.msgprint(__('No refundable Purchase Invoices found with pending quantities'));
            }
        }
    });
}

function build_purchase_invoice_table(invoices) {
    let html = `
        <div style="max-height: 500px; overflow-y: auto;">
            <table class="table table-bordered table-hover">
                <thead style="sticky; top: 0; background-color: white; z-index: 10;">
                    <tr>
                        <th width="5%">
                            <input type="checkbox" id="select-all-pi" class="select-all-checkbox">
                        </th>
                        <th width="15%">Name</th>
                        <th width="12%">Posting Date</th>
                        <th width="20%">Supplier</th>
                        <th width="18%">Customer</th>
                        <th width="15%">Project</th>
                        <th width="10%">Site</th>
                        <th width="5%">Currency</th>
                    </tr>
                </thead>
                <tbody id="pi-table-body">
    `;
    
    invoices.forEach(function(inv) {
        html += `
            <tr class="pi-row" data-customer="${inv.customer || ''}">
                <td><input type="checkbox" class="pi-checkbox" value="${inv.name}"></td>
                <td><a href="/app/purchase-invoice/${inv.name}" target="_blank">${inv.name}</a></td>
                <td>${frappe.datetime.str_to_user(inv.posting_date)}</td>
                <td>${inv.supplier || ''}</td>
                <td>${inv.customer || ''}</td>
                <td>${inv.project || ''}</td>
                <td>${inv.site || ''}</td>
                <td>${inv.currency || ''}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    return html;
}

function setup_select_all_checkbox(dialog) {
    dialog.$wrapper.on('change', '#select-all-pi', function() {
        let is_checked = $(this).prop('checked');
        dialog.$wrapper.find('.pi-checkbox:visible').prop('checked', is_checked);
    });

    dialog.$wrapper.on('change', '.pi-checkbox', function() {
        let total_visible = dialog.$wrapper.find('.pi-checkbox:visible').length;
        let total_checked = dialog.$wrapper.find('.pi-checkbox:visible:checked').length;
        
        dialog.$wrapper.find('#select-all-pi').prop('checked', total_visible === total_checked && total_visible > 0);
    });
}

function filter_purchase_invoices(customer, all_invoices, dialog) {
    if (customer === 'All') {
        dialog.$wrapper.find('.pi-row').show();
    } else {

        dialog.$wrapper.find('.pi-row').each(function() {
            let row_customer = $(this).data('customer');
            if (row_customer === customer) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    }

    dialog.$wrapper.find('#select-all-pi').prop('checked', false);
}


function fetch_items_from_purchase_invoices(frm, purchase_invoice_names) {
    frappe.call({
        method: 'one_fm.overrides.purchase_invoice.make_sales_invoice_from_purchase_invoice',
        args: {
            source_names: purchase_invoice_names,
            target_doc: frm.doc
        },
        freeze: true,
        freeze_message: __('Fetching items from Purchase Invoices...'),
        callback: function(r) {
            if (r.message) {
                let doc = r.message;
                
                if (!frm.doc.customer && doc.customer) {
                    frm.doc.customer = doc.customer;
                }
                
                if (!frm.doc.currency && doc.currency) {
                    frm.doc.currency = doc.currency;
                }
                
                if (doc.conversion_rate) {
                    frm.doc.conversion_rate = doc.conversion_rate;
                }
                
                if (!frm.doc.project && doc.project) {
                    frm.doc.project = doc.project;
                }
                
                if (!frm.doc.custom_site && doc.custom_site) {
                    frm.doc.custom_site = doc.custom_site;
                }
                
                frm.refresh_field('customer');
                frm.refresh_field('currency');
                frm.refresh_field('conversion_rate');
                frm.refresh_field('project');
                frm.refresh_field('custom_site');

                frm.clear_table('items');

                $.each(doc.items || [], function(i, item) {
                    if (!item.item_code || !item.qty || item.qty <= 0) {
                        return;
                    }
                    
                    let row = frm.add_child('items');
                    
                    Object.keys(item).forEach(key => {
                        if (key !== 'name' && key !== 'doctype' && key !== 'parent' && 
                            key !== 'parentfield' && key !== 'parenttype' && key !== 'idx' &&
                            key !== '__islocal' && key !== '__unsaved') {
                            row[key] = item[key];
                        }
                    });
                });
                
                frm.refresh_field('items');
                
                frm.doc.total = doc.total;
                frm.doc.net_total = doc.net_total;
                frm.doc.total_taxes_and_charges = doc.total_taxes_and_charges || 0;
                frm.doc.grand_total = doc.grand_total;
                frm.doc.rounded_total = doc.rounded_total;
                frm.doc.outstanding_amount = doc.outstanding_amount;
                
                frm.refresh_field('total');
                frm.refresh_field('net_total');
                frm.refresh_field('grand_total');
                
                frm.dirty();
                
                frappe.show_alert({
                    message: __('Items from {0} Purchase Invoice(s) added successfully', [purchase_invoice_names.length]),
                    indicator: 'green'
                }, 5);
                
                check_currency_differences(frm);
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __('Validation Error'),
                indicator: 'red',
                message: r.message || __('Failed to fetch items from Purchase Invoices')
            });
        }
    });
}


function check_currency_differences(frm) {
    let currencies = new Set();
    
    $.each(frm.doc.items || [], function(i, item) {
        if (item.custom_pi_currency) {
            currencies.add(item.custom_pi_currency);
        }
    });
    
    if (currencies.size > 1 || (currencies.size === 1 && !currencies.has(frm.doc.currency))) {
        frappe.msgprint({
            title: __('Currency Conversion Applied'),
            indicator: 'blue',
            message: __('Items from Purchase Invoices with different currencies have been converted using current exchange rates. Please verify the rates and amounts.')
        });
    }
}


function show_currency_exchange_info(frm) {
    if (frm.doc.docstatus === 0 && frm.doc.items && frm.doc.items.length > 0) {
        let has_currency_conversion = false;
        
        $.each(frm.doc.items || [], function(i, item) {
            if (item.custom_pi_exchange_rate && item.custom_pi_exchange_rate != 1.0) {
                has_currency_conversion = true;
                return false;
            }
        });
        
        if (has_currency_conversion) {
            frm.dashboard.add_comment(__('This invoice contains items converted from different currencies'), 'blue', true);
        }
    }
}


function update_all_items_field(frm, field_name, value) {
    if (frm.doc.items && frm.doc.items.length > 0) {
        $.each(frm.doc.items, function(i, item) {
            frappe.model.set_value(item.doctype, item.name, field_name, value);
        });
        frm.refresh_field('items');
    }
}

function calculate_margin_for_item(frm, cdt, cdn) {
    let item = locals[cdt][cdn];
    
    if (item.custom_refundable && item.margin_type && item.margin_rate_or_amount && item.rate) {
        let rate_with_margin = item.rate;
        
        if (item.margin_type === 'Percentage') {
            rate_with_margin = flt(item.rate) * (1 + flt(item.margin_rate_or_amount) / 100);
        } else if (item.margin_type === 'Amount') {
            rate_with_margin = flt(item.rate) + flt(item.margin_rate_or_amount);
        }
        
        frappe.model.set_value(cdt, cdn, 'rate_with_margin', rate_with_margin);
    } else if (!item.custom_refundable) {
        frappe.model.set_value(cdt, cdn, 'rate_with_margin', 0);
    }
}

function setup_contract_item_category_filter(frm) {
    if (frm.doc.custom_refundable) {
        frm.set_query('custom_contract_item_category', 'items', function(doc, cdt, cdn) {
        if (!doc.customer || !doc.project) {
            frappe.msgprint(__('Please select Customer and Project first'));
            return { filters: { 'name': ['=', ''] } }; 
        }
        
        return {
            query: 'one_fm.overrides.sales_invoice.get_filtered_contract_item_categories',
            filters: {
                'customer': doc.customer,
                'project': doc.project
            }
        };
    });

    }
}

function clear_contract_categories(frm) {
    if (frm.doc.items && frm.doc.custom_refundable) {
        frm.doc.items.forEach(function(item) {
            frappe.model.set_value(item.doctype, item.name, 'custom_contract_item_category', '');
        });
    }
}

// Story 2: Get Items From -> Contracts
function add_get_items_from_contracts(frm) {
    if (!frm.doc.customer || frm.doc.docstatus !== 0) return;
    
    frm.add_custom_button(__('Contracts'), function() {
        show_contract_selector(frm);
    }, __('Get Items From'));
}

function show_contract_selector(frm) {
    frappe.call({
        method: "one_fm.overrides.get_items_from_contracts.get_active_contracts_for_customer",
        args: {
            customer: frm.doc.customer
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let options = r.message.map(d => ({
                    label: d.name + (d.project ? ` (${d.project})` : ""),
                    value: d.name
                }));
                
                let d = new frappe.ui.Dialog({
                    title: __('Select Contract'),
                    fields: [
                        {
                            label: 'Contract',
                            fieldname: 'contract',
                            fieldtype: 'Select',
                            options: options,
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Next'),
                    primary_action: function(values) {
                        d.hide();
                        show_invoice_period_dialog(frm, values.contract);
                    }
                });
                d.show();
            } else {
                frappe.msgprint(__('No Active Contracts found for this Customer.'));
            }
        }
    });
}

function show_invoice_period_dialog(frm, contract) {
    const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const current_year = new Date().getFullYear();
    const years = [current_year - 1, current_year, current_year + 1];
    
    let current_month = months[new Date().getMonth()];
    
    let d = new frappe.ui.Dialog({
        title: __('Select Invoice Period'),
        fields: [
            {
                label: 'Month',
                fieldname: 'month',
                fieldtype: 'Select',
                options: months,
                default: current_month,
                reqd: 1
            },
            {
                label: 'Year',
                fieldname: 'year',
                fieldtype: 'Select',
                options: years,
                default: current_year,
                reqd: 1
            }
        ],
        primary_action_label: __('Get Items'),
        primary_action: function(values) {
            d.hide();
            fetch_items_from_contract(frm, contract, values.month, values.year);
        }
    });
    d.show();
}

function fetch_items_from_contract(frm, contract, month, year) {
    frappe.call({
        method: "one_fm.overrides.get_items_from_contracts.get_contract_invoice_items",
        args: {
            contract: contract,
            month: month,
            year: year
        },
        freeze: true,
        freeze_message: __('Fetching Contract Items and calculating Attendance...'),
        callback: function(r) {
            if (r.message) {
                let data = r.message;
                
                if (data.items && data.items.length > 0) {
                    frappe.run_serially([
                        () => frm.set_value("project", data.project),
                        () => frm.set_value("custom_site", data.site),
                        
                        // Story 5: Pre-set and read-only lock currency field from selected contract
                        () => frm.set_value("currency", data.currency),
                        () => frm.set_df_property("currency", "read_only", 1),
                        
                        () => {
                            data.items.forEach(item => {
                                let row = frm.add_child("items");
                                $.extend(row, item); 
                            });
                            frm.refresh_field("items");
                        }
                    ]);
                } else {
                    frappe.msgprint(__('No billable items found for the selected period.'));
                }
            }
        }
    });
}

