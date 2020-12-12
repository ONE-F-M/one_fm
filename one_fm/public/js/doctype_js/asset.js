frappe.ui.form.on('Asset', {
    available_for_use_date: function(frm) {
        var depreciation_start_date = moment(frm.doc.available_for_use_date).endOf('month').format('YYYY-MM-DD')
        $.each(frm.doc.finance_books || [], function(i, d) {
            d.depreciation_start_date = depreciation_start_date;
		});
		refresh_field("finance_books");
	}
});