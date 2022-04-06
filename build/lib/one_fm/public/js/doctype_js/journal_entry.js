frappe.ui.form.on('Journal Entry', {
	validate: function(frm){
		$.each(frm.doc.accounts || [], function(i, d) {
			if (d.include_amount_in_sales_invoice && !d.project){
				frappe.msgprint(__("Row#{0} Please enter project.", [d.idx]));
				frappe.validated = false;
			}
			if (d.include_amount_in_sales_invoice && d.project && !d.item_code){
				frappe.msgprint(__("Row#{0} Please enter item_code.", [d.idx]));
				frappe.validated = false;
			}
			if (d.include_amount_in_sales_invoice && d.project == 'Incheon Korea Airport'){
				if(d.journal_entry_for == ''){
					frappe.msgprint(__("Row#{0} field journal entry for could not be blank.", [d.idx]));
					frappe.validated = false;
				}
				if(d.journal_entry_for == 'Leave' || d.journal_entry_for == 'Indemnity'  && !d.employee){
					frappe.msgprint(__("Row#{0} Please enter employee.", [d.idx]));
					frappe.validated = false;
				}
				if(d.journal_entry_for == 'Visa and Residency' && !d.purchase_request_ref){
					frappe.msgprint(__("Row#{0} Please enter purchase request ref.", [d.idx]));
					frappe.validated = false;
				}
			}
		})
	}
});
frappe.ui.form.on('Journal Entry Account', {
    include_amount_in_sales_invoice: function(frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if(d.include_amount_in_sales_invoice){
			frappe.model.set_value(d.doctype, d.name, "account", 'Refundable Expense - ONEFM');
			frm.refresh_field("accounts");
		}
		// const row = locals[cdt][cdn];
		// var current_row = frm.fields_dict["accounts"].grid.grid_rows_by_docname[row.name];
		// current_row.toggle_reqd("project", (row.include_amount_in_sales_invoice === 1));
	}
});