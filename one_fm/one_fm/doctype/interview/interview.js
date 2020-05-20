// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Interview', {
	interview_type: function(frm) {
    set_interview_type_details(frm);
	},
  for_interview_sheet: function(frm) {
    clear_tables_based_on_for_interview_sheet(frm);
  }
});

var clear_tables_based_on_for_interview_sheet = function(frm) {
  if(frm.doc.for_interview_sheet){
    frm.clear_table('interview_questions');
    frm.clear_table('general_questions');
    frm.clear_table('attitude_questions');
    frm.clear_table('technical_questions');
  }
  else{
    var sections = ['General', 'Attitude', 'Technical', 'Experience', 'Language'];
    sections.forEach((item) => {
      frm.set_value(item.toLowerCase(), '');
    });
  }
};

var set_interview_type_details = function(frm) {
  // if(frm.doc.interview_type){
  //   frappe.db.get_value('Interview Type', frm.doc.interview_type, 'for_interview_sheet', function(r) {
  //     if(r && r.for_interview_sheet){
  //       frm.set_value('for_interview_sheet', r.for_interview_sheet);
  //     }
  //     else{
  //       frm.set_value('for_interview_sheet', r.for_interview_sheet);
  //     }
  //   });
  // }
  // else{
  //   frm.set_value('for_interview_sheet', false);
  // }
  if(frm.doc.interview_type){
    frappe.db.get_value('Interview Type', frm.doc.interview_type, 'is_bulk', function(r) {
      if(r && r.is_bulk){
        frm.set_value('is_bulk', r.is_bulk);
      }
      else{
        frm.set_value('is_bulk', r.is_bulk);
      }
    });
  }
  else{
    frm.set_value('is_bulk', false);
  }
};
