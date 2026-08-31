// Copyright (c) 2021, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Preparation Record',{
	//set total amunt per employee on the selection of the process
	renewal_or_extend: function(frm, cdt, cdn){
		set_preparation_record_costing(frm, cdt, cdn);
	},
	no_of_years: function(frm, cdt, cdn){
		set_preparation_record_costing(frm, cdt, cdn);
	},
	work_permit_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		caclulate_renewal_extension_cost_total(frm, child);
	},
	medical_insurance_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		caclulate_renewal_extension_cost_total(frm, child);
	},
	residency_stamp_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		caclulate_renewal_extension_cost_total(frm, child);
	},
	civil_id_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		caclulate_renewal_extension_cost_total(frm, child);
	},
	employee: function(frm, cdt, cdn){
		// Debounced batch fetch to avoid multiple quick calls
		if(!frm._employee_dates_timeout){
			frm._employee_dates_timeout = setTimeout(() => {
				fetch_employee_dates_batch(frm);
				frm._employee_dates_timeout = null;
			}, 300);
		}
	}
});

// WI-002031: the Actions whose master fee row is keyed by the number of years too. Kept
// in step with YEAR_SCOPED_ACTIONS in preparation.py and with the costing table's own
// depends_on.
const YEAR_SCOPED_ACTIONS = ['Renewal (Kuwaiti)', 'Renewal (Non-Kuwaiti)'];
const COST_COMPONENT_FIELDS = [
	'work_permit_amount',
	'medical_insurance_amount',
	'residency_stamp_amount',
	'civil_id_amount'
];

var set_preparation_record_costing = function(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	if(!row.renewal_or_extend){
		return;
	}

	// The years only mean something for a renewal. Cleared otherwise, because the field is
	// hidden rather than emptied when the Action changes, and a stale "1 Year" left on an
	// Extend row is a year the master lookup would have been scoped by.
	if(YEAR_SCOPED_ACTIONS.includes(row.renewal_or_extend)){
		if(!row.no_of_years){
			frappe.model.set_value(row.doctype, row.name, 'no_of_years', '1 Year');
		}
	} else if(row.no_of_years){
		frappe.model.set_value(row.doctype, row.name, 'no_of_years', '');
	}

	// Cleared before the fetch, not inside a successful callback. Switching to an Action
	// with no master row configured used to leave the fees of the previous Action sitting
	// in the row, which is exactly the case the story calls out.
	COST_COMPONENT_FIELDS.forEach(field => frappe.model.set_value(row.doctype, row.name, field, 0));
	frappe.model.set_value(row.doctype, row.name, 'total_amount', 0);
	frm.refresh_field('preparation_record');

	frappe.call({
		// WI-002092: the row's fees, already multiplied out for a multi-year renewal. The
		// master lookup returns the annual rate, which is not what the row carries.
		method: 'one_fm.grd.doctype.preparation.preparation.get_preparation_row_costing',
		args: {'renewal_or_extend': row.renewal_or_extend, 'no_of_years': row.no_of_years},
		callback: function(r) {
			if(!r.message){
				// WI-002092: say so rather than leave four zeros and no explanation. The
				// commonest cause is a renewal whose master row is configured for a
				// different number of years than the row is asking for.
				frappe.show_alert({
					message: __('No master fee row in HR Settings for {0}{1}.', [
						row.renewal_or_extend,
						row.no_of_years ? __(' at {0}', [row.no_of_years]) : ''
					]),
					indicator: 'orange'
				}, 7);
				return;
			}
			var cost = r.message;
			COST_COMPONENT_FIELDS.forEach(field =>
				frappe.model.set_value(row.doctype, row.name, field, cost[field] || 0));
			frm.refresh_field('preparation_record');
		}
	});
};

var caclulate_renewal_extension_cost_total = function(frm, child) {
	var total_cost = 0;
	if(child.work_permit_amount && child.work_permit_amount > 0){
		total_cost += child.work_permit_amount;
	}
	if(child.medical_insurance_amount && child.medical_insurance_amount > 0){
		total_cost += child.medical_insurance_amount;
	}
	if(child.residency_stamp_amount && child.residency_stamp_amount > 0){
		total_cost += child.residency_stamp_amount;
	}
	if(child.civil_id_amount && child.civil_id_amount > 0){
		total_cost += child.civil_id_amount;
	}
	frappe.model.set_value(child.doctype, child.name, 'total_amount', total_cost);
	frm.refresh_field('preparation_record');
};

// WI-002101: narrow the Action dropdown to what this kind of batch may carry. The server
// re-checks on validate - rows also arrive from the monthly schedule, from imports and from
// the API, none of which see a dropdown.
var set_action_options = function(frm){
	if(!frm.doc.category){
		// Nothing chosen yet: leave every Action on offer rather than an empty dropdown the
		// operator cannot explain.
		frm.fields_dict.preparation_record.grid.update_docfield_property(
			'renewal_or_extend', 'options', frm._all_actions);
		return;
	}

	frappe.call({
		method: 'one_fm.grd.doctype.preparation.preparation.get_actions_for_category',
		args: {category: frm.doc.category},
		callback: function(r){
			if(!r.message){
				return;
			}
			frm.fields_dict.preparation_record.grid.update_docfield_property(
				'renewal_or_extend', 'options', [''].concat(r.message).join('\n'));
			frm.refresh_field('preparation_record');
		}
	});
};

//Set renewal for all employee to facilitate process
frappe.ui.form.on("Preparation", {
	onload: frm => {
		// The full list, kept so it can be put back when the Category is cleared.
		frm._all_actions = frm.fields_dict.preparation_record.grid
			.get_docfield('renewal_or_extend').options;
	},
	category: frm => {
		set_action_options(frm);
	},
	refresh : frm=>{
		set_action_options(frm);

		if(frm.doc.docstatus==1){
			if(!frappe.user.has_role("HR Manager")){
				cur_frm.fields_dict.preparation_record.grid.update_docfield_property("renewal_or_extend", "allow_on_submit", 0);
				cur_frm.fields_dict.preparation_record.grid.update_docfield_property("no_of_years", "allow_on_submit", 0);
				cur_frm.fields_dict.preparation_record.grid.update_docfield_property("work_permit_amount", "allow_on_submit", 0);
				cur_frm.fields_dict.preparation_record.grid.update_docfield_property("medical_insurance_amount", "allow_on_submit", 0);
				cur_frm.fields_dict.preparation_record.grid.update_docfield_property("residency_stamp_amount", "allow_on_submit", 0);
				cur_frm.fields_dict.preparation_record.grid.update_docfield_property("civil_id_amount", "allow_on_submit", 0);
				
				// Fetch dates on refresh (covers load & reload)
				fetch_employee_dates_batch(frm);
			}
		}

	},
	set_renewal_for_all: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'set_renewal_for_all_preparation_record',
			args: {'renew_all': frm.doc.set_renewal_for_all},
			callback: function(r) {
				frm.refresh_field('preparation_record');
			}
		})
	},
});


function fetch_employee_dates_batch(frm){
	if(!frm.doc.preparation_record || frm.doc.preparation_record.length === 0){
		return;
	}
	if(frm.is_new()){
		return; // cannot DB set unsaved rows
	}
	frappe.call({
		method: 'one_fm.grd.doctype.preparation.preparation.update_preparation_employee_dates',
		args: { preparation: frm.doc.name },
		freeze: false,
		callback: function(r){
			// We avoid local field mutation to keep form clean.
			// Optionally, refresh grid rows that were updated so user sees values.
			if(r.message && r.message.updated_rows && r.message.updated_rows.length){
				// Reload only affected child rows values from DB
				// r.message.updated_rows.forEach(rowname => {
				// 	frappe.model.remove_from_locals('Preparation Record', rowname); // force re-fetch
				// });
				frm.refresh_field('preparation_record');
			}
		}
	});
}
