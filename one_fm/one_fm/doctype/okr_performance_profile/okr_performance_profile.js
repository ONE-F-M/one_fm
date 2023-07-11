// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('OKR Performance Profile', {
	refresh: function(frm) {
		if(!frm.is_new()){
			frm.set_df_property('okr_title_section', 'hidden', true);
		}
    set_objective_option_to_kr(frm);
	
		set_objectoves_description(frm);
	},
	description: function(frm) {
		set_objectoves_description(frm);
	}
});

var set_objectoves_description = function(frm) {
	let description = frm.doc.description?frm.doc.description:'';
	frm.fields_dict.objective_description.html(description);
};

frappe.ui.form.on('OKR Performance Profile Objective', {
	objective: function(frm,cdt,cdn) {
		set_objective_option_to_kr(frm);
		
		update_existing_values(frm,cdt,cdn)
	},
	from_date: function(frm, cdt, cdn) {
		calculate_time_frame(frm, cdt, cdn);
	},
	to_date: function(frm, cdt, cdn) {
		calculate_time_frame(frm, cdt, cdn);
	}
});

var calculate_time_frame = function(frm, cdt, cdn) {
	var child = locals[cdt][cdn];
	if(child.from_date && child.to_date){
		frappe.model.set_value(child.doctype, child.name, 'time_frame', frappe.datetime.get_diff(child.to_date, child.from_date));
	}
	frm.refresh_field('objectives');
};

var update_existing_values = function(frm,cdt,cdn){
	
	
	var child = locals[cdt][cdn];
	let id = child.name
	
	if(!id.includes('new')){
		frm.doc.key_results.forEach((item,index,arr)=>{
			
			if(item.matched_row == id){
				item.objective = child.objective
			}
		})
		frm.refresh_fields()
	}

}
var set_objective_option_to_kr = function(frm) {
  var options = [''];
  frm.doc.objectives.forEach((item, i) => {
    options[i+1] = item.objective
  });

  frm.fields_dict.key_results.grid.update_docfield_property('objective','options',options);
  frm.refresh_field('key_results');
};
