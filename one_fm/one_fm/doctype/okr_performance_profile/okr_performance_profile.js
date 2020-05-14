// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('OKR Performance Profile', {
	refresh: function(frm) {
		if(!frm.is_new()){
			frm.set_df_property('okr_title_section', 'hidden', true);
		}
    set_objective_option_to_kr(frm);
		set_objectoves_description(frm);
		frm.fields_dict.help_text.html(get_help_text_html());
	},
	description: function(frm) {
		set_objectoves_description(frm);
	}
});

var get_help_text_html = function() {
	return `\
			<p>Objective:</p>\
			<ol>\
			<li>On this job what types of projects and tasks would this person be assigned?</li>\
			<li>Why would a top person who's not looking, would see this as a better career opportunity than the person's current role or some competing opportunity for other than a big monetary increase?</li>\
			</ol>\
			<p>Key Results:</p>\
			<ol>\
			<li>What the candidate would need to accomplish in doing this work that indicates this person is a great performer?</li>\
			</ol>
	`;
};

var set_objectoves_description = function(frm) {
	let description = frm.doc.description?frm.doc.description:'';
	frm.fields_dict.objective_description.html(description);
};

frappe.ui.form.on('OKR Performance Profile Objective', {
	objective: function(frm) {
    set_objective_option_to_kr(frm);
	}
});

var set_objective_option_to_kr = function(frm) {
  var options = [''];
  frm.doc.objectives.forEach((item, i) => {
    options[i+1] = item.objective
  });
  frappe.meta.get_docfield("OKR Performance Profile Key Result", "objective", frm.doc.name).options = options;
  frm.refresh_field('key_results');
};
