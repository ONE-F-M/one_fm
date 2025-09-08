// Copyright (c) 2021, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Roster Post Actions', {
	refresh: function(frm) {
		frm.add_custom_button(__('Take Action'), function() {
			const operationsRole = encodeURIComponent(frm.doc.operations_role || '');
			const shift = encodeURIComponent(frm.doc.operations_shift || '');
		
			const url = `/app/roster?main_view=roster&sub_view=post&operations_role=${operationsRole}&shift=${shift}`;
			window.open(url, '_blank');
		});
	}
});
