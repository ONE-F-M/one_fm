// Copyright (c) 2020, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Legal Investigation', {
	refresh: function(frm){
		// set_lead_filters(frm);
		if(!frm.doc.__islocal){
			set_employee_filters(frm);
			frm.set_df_property("session_summary", "read_only", true);
		}
	},
	start_date: function(frm) {
		validate_days_buffer(frm);
		validate_dates(frm);
	},
	end_date: function(frm) {
		validate_dates(frm);
	},
	investigation_lead: function(frm){
		if(frm.doc.investigation_lead){
			frappe.db.get_value("Employee", {"name": frm.doc.investigation_lead}, ["user_id"])
			.then(res => {
				console.log(res);
				frm.set_value("lead_user", res.message.user_id);
			})
		}
	}
});
function set_lead_filters(frm){
	frm.set_query("investigation_lead", function() {
        return {
            "filters": {
                "department": "Legal - ONEFM",
            }
        };
    });
}

function set_employee_filters(frm){
	let {doctype, name} = frm.doc;
	frm.set_query("employee_id", "legal_investigation_penalty" ,function() {
		return {
			query: "one_fm.legal.doctype.legal_investigation.legal_investigation.filter_employees",
			filters: {doctype, name}
		}
	});	
}

function validate_days_buffer(frm){
	let {start_date} = frm.doc;

	if(start_date ){
		let start = moment(start_date);
		var today = moment();
		
		if (start.diff(today, 'days') < 2){
			frm.set_value("start_date", today.add(2, 'days'));
			frappe.throw(__("Legal Investigation will start after 48 hours."))	
		}
	}
}

function validate_dates(frm){
	let {start_date, end_date} = frm.doc;
	if(start_date !== undefined && end_date !== undefined){
		let start = moment(start_date);
		let end = moment(end_date);
		if (start > end){
			frappe.throw(__("Start date cannot be after end date."))
		}
	}
}


frappe.ui.form.on('Legal Investigation Penalty', {
	use_penalty_details: function(frm, cdt, cdn){
		let row = locals[cdt][cdn];
		if(!row.use_penalty_details) return;

		let grid_row = frm.open_grid_row();
		let {reference_doctype, reference_docname} = frm.doc;
		let fields = ["third_party_damage", "penalty_location", "penalty_occurence_time", "shift", "site", "project", "site_location"];
		// HR Enquiry names the shift and site fields differently.
		let source = fieldname => reference_doctype === "HR Enquiry" && ["shift", "site"].includes(fieldname)
			? `operations_${fieldname}` : fieldname;
		frappe.db.get_value(reference_doctype, {'name': reference_docname}, fields.map(source))
		.then(res => {
			fields.forEach(fieldname => {
				row[fieldname] = res.message[source(fieldname)];
				grid_row.grid_form.fields_dict[fieldname].df.read_only = true;
			});
			frm.refresh_field('legal_investigation_penalty');
		})
	}
})
