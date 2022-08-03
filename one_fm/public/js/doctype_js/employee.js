frappe.ui.form.on('Employee', {
	refresh: function(frm) {
		hideFields(frm);
		frm.trigger('set_queries');
		set_mandatory(frm);
	},
	status: function(frm){
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
	if (['Left', 'Court Case', 'Absconding', 'Vacation'].includes(frm.doc.status)){
		toggle_required(frm, 0);
	} else {
		toggle_required(frm, 1);
	}
}

// TOGGLE REQUIRED
let toggle_required = (frm, state) => {
	['leave_policy', 'project', 'site', 'shift', 'permanent_address', 'cell_number',
	'last_name_in_arabic'].forEach((item, i) => {
		frm.toggle_reqd(item, state);
	});
}


// Hide un-needed fields
const hideFields = frm => {
    $("[data-doctype='Employee Checkin']").hide();
}