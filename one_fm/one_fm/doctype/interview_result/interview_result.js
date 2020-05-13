// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Interview Result', {
	refresh: function(frm) {
    frm.set_query('interview_template', function () {
			return {
				filters: {
					'designation': ['in', [frm.doc.designation, '']]
				}
			};
		});
	},
  interview_template: function(frm) {
    set_interview_template(frm);
  }
});

frappe.ui.form.on('Interview Question Result', {
	score: function(frm) {
    calculate_total_and_avg_score(frm);
	}
});

var calculate_total_and_avg_score = function(frm) {
  var total = 0;
  var avg = 0;
  if(frm.doc.interview_question_result){
    frm.doc.interview_question_result.forEach((item) => {
      total += item.score;
    });
  }
  frm.set_value('total_score', total);
  if(total && frm.doc.interview_question_result.length > 0){
    avg = total/frm.doc.interview_question_result.length;
  }
  frm.set_value('average_score', avg);
};

var set_interview_template = function(frm) {
  frm.clear_table('interview_question_result');
  if(frm.doc.interview_template){
    frappe.call({
      method: 'frappe.client.get',
      args: {
        doctype: 'Interview',
        filters: {name: frm.doc.interview_template}
      },
      callback: function(r) {
        if(r && r.message && r.message.interview_questions){
          let interview_questions = r.message.interview_questions;
          interview_questions.forEach((item, i) => {
            let interview_question = frappe.model.add_child(frm.doc, 'Interview Question Result', 'interview_question_result');
            frappe.model.set_value(interview_question.doctype, interview_question.name, 'questions', item.questions);
            frappe.model.set_value(interview_question.doctype, interview_question.name, 'answer', item.answer);
            frappe.model.set_value(interview_question.doctype, interview_question.name, 'weight', item.weight);
          });
        }
        frm.refresh_field('interview_question_result');
      }
    });
  }
  else{
    frm.refresh_field('interview_question_result');
  }
};
