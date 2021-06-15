frappe.ui.form.on('Item Price', {
    refersh:function(frm){
        console.log('item price filter')
        frm.fields_dict['items'].grid.get_field('item_price').get_query = function(frm, cdt, cdn) {
            let d = locals[cdt][cdn];
            return {    
                filters:{
                    customer: frm.doc.client, 
					selling: 1,
                    item_code: d.item_code
                }
            }
        }
        frm.refresh_field("items");
    },
    item_code:function(frm){
        if(frm.doc.item_code){
            frappe.call({
                method: 'frappe.client.get_value',
                args:{
                    'doctype':'Item',
                    'filters':{
                        'item_code': frm.doc.item_code,
                        'subitem_group': 'Service',
                        'is_stock_item':0,
                        'is_sales_item':1
                    },
                    'fieldname':[
                        'is_stock_item'
                    ]
                },
                callback:function(s){
                    if(!s.exc) {
                        console.log(s.message)
                        if(s.message){
                            set_required_property(frm);
                            frm.set_df_property('post_detail', 'hidden', 0);
                        }
                        else{
                            remove_required_property(frm);
                            frm.set_df_property('post_detail', 'hidden', 1);
                        }                       
                    }
                }
            });
        }
    }
});

function set_required_property(frm){
    frm.set_df_property('uom', 'reqd', true);
    frm.set_df_property('gender', 'reqd', true);
    frm.set_df_property('shift_hours', 'reqd', true);
    frm.set_df_property('days_off', 'reqd', true);
    frm.set_df_property('customer', 'reqd', true);
}

function remove_required_property(frm){
    frm.set_df_property('uom', 'reqd', false);
    frm.set_df_property('gender', 'reqd', false);
    frm.set_df_property('shift_hours', 'reqd', false);
    frm.set_df_property('days_off', 'reqd', false);
    frm.set_df_property('customer', 'reqd', false);
}
