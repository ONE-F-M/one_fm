frappe.ui.form.on('Employee', {
	refresh: function(frm) {
		frm.trigger('set_queries');
		set_mandatory(frm);
	},
	set_queries: frm => {
		// set bank account query
		frm.set_query('bank_account', function() {
			return {
				filters: {
					"party_type": frm.doc.doctype,
					"party": frm.doc.name
				}
			};
		});
	}
});


frappe.ui.form.on('Employee Incentive', {
	refresh: function(frm) {
		frm.trigger('set_queries');
	},
	set_queries: frm => {
		// set leave policy query
		frm.set_query('leave_policy', function() {
			return {
				filters: {
					"docstatus": 1
				}
			};
		});
	}
});

// SET MANDATORY FIELDS
let set_mandatory = frm => {
	if (frm.doc.status != 'Left'){
		['leave_policy', 'project', 'site', 'shift', 'permanent_address', 'cell_number'].forEach((item, i) => {
			frm.toggle_reqd(item, 1);
		});

	}
}
