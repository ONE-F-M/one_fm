// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Legal Investigation', {
	refresh: function(frm){
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
});

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