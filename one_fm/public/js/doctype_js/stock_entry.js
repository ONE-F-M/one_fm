frappe.ui.form.on('Stock Entry', {
    // cdt is Child DocType name i.e Quotation Item
    // cdn is the row name for e.g bbfcb8da6a
    refresh(frm) {
        // console.log(frm.doc);
    }
})


frappe.ui.form.on('Stock Entry Detail', {
    // cdt is Child DocType name i.e Quotation Item
    // cdn is the row name for e.g bbfcb8da6a
    item_code(frm, cdt, cdn) {
        console.log(cdt, cdn);
        let row = frappe.get_doc(cdt, cdn);
    },
    t_warehouse(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.t_warehouse){
            frappe.db.get_value("Warehouse", row.t_warehouse, '')
        }
    }
})