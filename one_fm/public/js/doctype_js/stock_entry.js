frappe.ui.form.on('Stock Entry', {
    refresh(frm) {
        
    }
})


frappe.ui.form.on('Stock Entry Detail', {
    t_warehouse(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.t_warehouse){
            frappe.db.get_value("Warehouse", row.t_warehouse, 'allow_zero_valuation_rate').then(res=>{
                if (res.message){
                    row.allow_zero_valuation_rate = res.message.allow_zero_valuation_rate;
                    row.basic_rate = 0;
                    row.basic_amount = 0;
                    row.amount = 0;
                    row.valuation_rate = 0;
                    row.additional_cost = 0;
                    frm.refresh_field('items');
                }
            })

        }
    },

    expense_account(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        if (frm.doc.stock_entry_type === "Material Issue"){
            frappe.db.get_value("Item", row.item_code, "difference_account").then(res=>{
                row.expense_account = res.message.difference_account
                 frm.refresh_field('items');
            })
        }
    }
})