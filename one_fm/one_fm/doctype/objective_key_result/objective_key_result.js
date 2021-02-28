// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Objective Key Result', {
	refresh: function(frm) {
		if(!frm.is_new()){
			frm.set_df_property('okr_title_section', 'hidden', true);
		}
	set_objective_option_to_kr(frm);
	set_objective_link(frm);
		set_objectoves_description(frm);
	},
	description: function(frm) {
		set_objectoves_description(frm);
	},
	start_date: function(frm) {
		set_objective_link(frm);
	},
	end_date: function(frm){
		set_objective_link(frm);
	}
});

var set_objectoves_description = function(frm) {
	let description = frm.doc.description?frm.doc.description:'';
	frm.fields_dict.objective_description.html(description);
};

frappe.ui.form.on('OKR Performance Profile Objective', {
	objective: function(frm) {
    set_objective_option_to_kr(frm);
	},
	from_date: function(frm, cdt, cdn) {
		calculate_time_frame(frm, cdt, cdn);
	},
	to_date: function(frm, cdt, cdn) {
		calculate_time_frame(frm, cdt, cdn);
	},
	objective_linking_with: function(frm) {
		frappe.db.get_list('OKR Performance Profile Objective', {
			fields: ['objective'],

		}).then(records => {
			console.log(records);
		})

	}
});

var calculate_time_frame = function(frm, cdt, cdn) {
	var child = locals[cdt][cdn];
	if(child.from_date && child.to_date){
		frappe.model.set_value(child.doctype, child.name, 'time_frame', frappe.datetime.get_diff(child.to_date, child.from_date));
	}
	frm.refresh_field('objectives');
};

var set_objective_option_to_kr = function(frm) {
  var options = [''];
  frm.doc.objectives.forEach((item, i) => {
    options[i+1] = item.objective
  });
  frappe.meta.get_docfield("OKR Performance Profile Key Result", "objective", frm.doc.name).options = options;
  frm.refresh_field('key_results');
};

var set_objective_link = function(frm) {
	console.log(frm.doc.start_date);
	console.log(frm.doc.end_date);
	if (frm.doc.start_date && frm.doc.end_date){
		frappe.call({
			// Need to pass the arguments
			method: 'one_fm.one_fm.doctype.objective_key_result.objective_key_result.get_objectives',
			args: {'start_date': frm.doc.start_date , 'end_date': frm.doc.end_date} ,
			callback: function(r) {
				console.log(r.message);
				if(r.message){
					var options = [''];
					var data = r.message;
				  data.forEach((item, i) => {
					options[i+1] = item.objective
				  });
				  console.log(options);
				  frappe.meta.get_docfield("OKR Performance Profile Objective", "objective_link", frm.doc.name).options = options;
				  frm.refresh_field('objective_link');
				}
				else{
					frm.refresh_field('objective_link');
				}
			}
		});

	}
	
};



