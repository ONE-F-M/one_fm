// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Applicant Interview Sheet', {
	refresh: function(frm) {
    frm.set_query('interview_template', function () {
			return {
				filters: {
					'designation': ['in', [frm.doc.designation, '']],
					'for_interview_sheet': true
				}
			};
		});
	},
  interview_template: function(frm) {
    set_interview_template(frm);
  },
  job_applicant: function(frm) {
    set_career_history_details(frm);
  }
});

var set_career_history_details = function(frm) {
  if(frm.doc.job_applicant){
    frappe.call({
      method: 'one_fm.one_fm.doctype.career_history.career_history.get_career_history_as_html',
      args: {'job_applicant': frm.doc.job_applicant},
      callback: function(r) {
        if(r && r.message){
          frm.fields_dict.work_experience_details.html(r.message);
        }
      }
    })
  }
  else{
    frm.fields_dict.work_experience_details.html('');
  }
};

var set_interview_template = function(frm) {
  var sections = ['General', 'Attitude', 'Technical', 'Experience', 'Language'];
  sections.forEach((item) => {
    frm.clear_table('interview_sheet_'+item.toLowerCase());
  });
  if(frm.doc.interview_template){
    frappe.call({
      method: 'one_fm.one_fm.doctype.job_applicant_interview_sheet.job_applicant_interview_sheet.get_interview_template_details',
      args: {'template_name': frm.doc.interview_template},
      callback: function(r) {
        if(r && r.message){
          sections.forEach((item) => {
            if(r.message[item]){
              set_interview_sheet_child(frm, 'interview_sheet_'+item.toLowerCase(), 'Interview Sheet '+item, r.message[item]);
            }
          });
        }
      }
    });
  }
  else{
    sections.forEach((item) => {
      frm.refresh_field('interview_sheet_'+item.toLowerCase());
    });
  }
};

var set_interview_sheet_child = function(frm, table, table_doctype, template){
  frm.clear_table(table);
  if(template && template.interview_questions){
    let interview_questions = template.interview_questions;
    interview_questions.forEach((item, i) => {
      let interview_question = frappe.model.add_child(frm.doc, table_doctype, table);
      frappe.model.set_value(interview_question.doctype, interview_question.name, 'questions', item.questions);
      frappe.model.set_value(interview_question.doctype, interview_question.name, 'answer', item.answer);
      frappe.model.set_value(interview_question.doctype, interview_question.name, 'weight', item.weight);
      if(item.answer_based_on_weight_distribution == 1){
        frappe.model.set_value(interview_question.doctype, interview_question.name, 'answer_based_on_weight_distribution', item.answer_based_on_weight_distribution);
        frappe.model.set_value(interview_question.doctype, interview_question.name, 'answer_0', item.answer_0);
        frappe.model.set_value(interview_question.doctype, interview_question.name, 'answer_1', item.answer_1);
        frappe.model.set_value(interview_question.doctype, interview_question.name, 'answer_2', item.answer_2);
        frappe.model.set_value(interview_question.doctype, interview_question.name, 'answer_3', item.answer_3);
        frappe.model.set_value(interview_question.doctype, interview_question.name, 'answer_4', item.answer_4);
        frappe.model.set_value(interview_question.doctype, interview_question.name, 'answer_5', item.answer_5);
        frappe.model.set_value(interview_question.doctype, interview_question.name, 'exception', item.exception);
      }
    });
  }
  frm.refresh_field(table);
};
