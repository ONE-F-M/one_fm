frappe.ui.form.on('Asset', {
    available_for_use_date: function(frm) {
        var depreciation_start_date = moment(frm.doc.available_for_use_date).endOf('month').format('YYYY-MM-DD')
        $.each(frm.doc.finance_books || [], function(i, d) {
            d.depreciation_start_date = depreciation_start_date;
		});
		refresh_field("finance_books");
	},
	before_workflow_action:function(frm){
		var depreciation_start_date = 0;
		var transfer_date = 0;
		if(frm.doc.workflow_state == 'Received At Warehouse'){
			if(frm.doc.is_existing_asset == 0){
				$.each(frm.doc.asset_transfer || [], function(i, d) {
					if(d.idx == 2){
						depreciation_start_date = moment(d.transfer_date).endOf('month').format('YYYY-MM-DD');
						transfer_date = moment(d.transfer_date).format('YYYY-MM-DD');
					}
				});
				$.each(frm.doc.finance_books || [], function(i, d) {
					d.depreciation_start_date = depreciation_start_date;
				});
				refresh_field("finance_books");
				frm.set_value("available_for_use_date",moment(transfer_date).format('YYYY-MM-DD'));
				refresh_field("available_for_use_date");
				
			}
		}
	}
});
frappe.ui.form.on('Depreciation Schedule', {
	make_depreciation: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (!row.journal_entry) {
			frappe.call({
				method: "one_fm.one_fm.depreciation_custom.make_depreciation",
				args: {
					"asset_name": frm.doc.name,
					"date": row.schedule_date
				},
				callback: function(r) {
					frappe.model.sync(r.message);
					frm.refresh();
				}
			})
		}
    }
});
//