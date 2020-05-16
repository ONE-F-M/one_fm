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
  },
	get_best_reference: function(frm) {
		set_best_reference_table_property(frm);
	}
});

var set_best_reference_table_property = function(frm) {
	if(frm.doc.get_best_reference){
		frm.set_df_property('best_references', 'reqd', true);
		var references = ['Best Boss', 'Best Colleague', 'Best Employee'];
		references.forEach((item) => {
			let reference = frappe.model.add_child(frm.doc, 'Interview Best Reference', 'best_references');
			frappe.model.set_value(reference.doctype, reference.name, 'reference', item);
		});
	}
	else{
		frm.set_df_property('best_references', 'reqd', false);
		frm.clear_table('best_references');
	}
	frm.refresh_field('best_references');
};

frappe.ui.form.on('Interview Question Result', {
	score: function(frm, cdt, cdn) {
		validate_score_with_weight(frm, cdt, cdn);
    calculate_total_and_avg_score(frm);
	}
});

var validate_score_with_weight = function(frm, cdt, cdn) {
	var child = locals[cdt][cdn];
	if(child.weight && child.score){
		if(child.score > child.weight){
			frappe.model.set_value(child.doctype, child.name, 'score', '');
			frappe.throw(__("Score is cannot be Greater than Weight {0}", [child.weight]));
		}
	}
};

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
        frm.refresh_field('interview_question_result');
      }
    });
  }
  else{
    frm.refresh_field('interview_question_result');
  }
};
