frappe.ui.form.on('Asset', {
    available_for_use_date: function(frm) {
        var available_for_use_date = new Date(frm.doc.available_for_use_date);
        var depreciation_start_date = new Date(available_for_use_date.getFullYear(), available_for_use_date.getMonth()+1, 0);
        depreciation_start_date = moment(depreciation_start_date).format("YYYY-MM-DD");
        $.each(frm.doc.finance_books || [], function(i, d) {
            d.depreciation_start_date = depreciation_start_date;
		});
		refresh_field("finance_books");
	}
});