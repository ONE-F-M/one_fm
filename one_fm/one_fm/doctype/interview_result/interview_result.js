// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Interview Result', {
	refresh: function(frm) {
    frm.set_query('interview_template', function () {
			return {
				filters: {
					'designation': ['in', [frm.doc.designation, '']],
					'interview_type': frm.doc.interview_type
				}
			};
		});
		frm.set_query('job_applicant', function () {
			return {
				filters: {
					'status': ['not in', ['Rejected']]
				}
			};
		});
		if(frm.is_new()){
			frm.set_value('interview_date', frappe.datetime.now_datetime());
		}
		set_experience_company_options(frm);
	},
  interview_template: function(frm) {
    set_interview_template(frm);
  },
	get_best_reference: function(frm) {
		set_best_reference_table_property(frm);
	},
	job_applicant: function(frm) {
		// set_job_applicant_interview_schedule_details(frm);
		set_career_history_details(frm);
		set_experience_company_options(frm);
	},
	interview_type: function(frm) {
		// set_job_applicant_interview_schedule_details(frm);
	},
	work_experience_score: function(frm) {
    calculate_total_and_avg_score(frm);
	},
	pass_to_next_interview: function(frm) {
		confirm_score_action(frm);
	},
	view_question: function(frm) {
		view_sample_question(frm);
	}
});

var view_sample_question = function(frm) {
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Interview',
			filters: {name: frm.doc.interview_template}
		},
		callback: function(r) {
			if(r && r.message){
				var dialog = new frappe.ui.Dialog({
					title: __("Question"),
					fields: [
						{
							"fieldtype": "HTML",
							"fieldname": "sample_question"
						}
					]
				});
				dialog.fields_dict.sample_question.$wrapper.html(frappe.render_template('sample_question', {doc:r.message}));
				dialog.show();
			}
		},
		freeze: true
	});
};

var confirm_score_action = function(frm) {
	if(frm.doc.pass_to_next_interview){
		let msg = __('Do You Need to Set the Value to {0}', [frm.doc.pass_to_next_interview])
		frappe.confirm(
			msg,
			function(){
				// Yes
				if(frm.doc.pass_to_next_interview == 'Reject'){
					frappe.msgprint(__('Applicant Will be Rejected on this Interview Submit.'));
				}
				if(frm.doc.pass_to_next_interview == 'Pass'){
					frm.save();
				}
			},
			function(){
				// No
				frm.set_value('pass_to_next_interview', '');
			}
		);
	}
};

var set_experience_company_options = function(frm) {
  if(frm.doc.job_applicant){
    frappe.call({
      method: 'one_fm.one_fm.doctype.career_history.career_history.get_career_history',
      args: {'job_applicant': frm.doc.job_applicant},
      callback: function(r) {
				var options = [''];
        if(r && r.message && r.message.career_history_company){
					r.message.career_history_company.forEach((item, i) => {
						options[i] = item.company_name;
					});
        }
				frappe.meta.get_docfield("Interview Experience Note", "company_name", frm.doc.name).options = options;
      }
    })
  }
  else{
    frappe.meta.get_docfield("Interview Experience Note", "company_name", frm.doc.name).options = [''];
  }
};

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

var set_job_applicant_interview_schedule_details = function(frm) {
	if(frm.doc.job_applicant){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Job Applicant',
				filters: {name: frm.doc.job_applicant}
			},
			callback: function(r) {
				if(r && r.message && r.message.one_fm_interview_schedules && r.message.one_fm_interview_schedules.length > 0){
					var schedules = r.message.one_fm_interview_schedules;
					var interview_types = [];
					schedules.forEach((item, i) => {
						if(frm.doc.interview_type && frm.doc.interview_type == item.interview_type){
							frm.set_value('interview_scheduled_date', item.scheduled_on);
						}
						interview_types[i] = item.interview_type;
					});
					frm.set_query('interview_type', function () {
						return {
							filters: {
							'name': ['in', interview_types]
							}
						};
					});
				}
			}
		});
	}
};

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

frappe.ui.form.on('Interview Sheet General', {
	score: function(frm, cdt, cdn) {
		validate_score_with_weight(frm, cdt, cdn);
    calculate_total_and_avg_score(frm);
	}
});

frappe.ui.form.on('Interview Sheet Attitude', {
	score: function(frm, cdt, cdn) {
		validate_score_with_weight(frm, cdt, cdn);
    calculate_total_and_avg_score(frm);
	}
});

frappe.ui.form.on('Interview Sheet Technical', {
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
	var no_of_questions = 0;
  var avg = 0;
	if(frm.doc.is_bulk){
		var sections = ['interview_sheet_general', 'interview_sheet_attitude', 'interview_sheet_technical'];
	  sections.forEach((item) => {
			if(frm.doc[item]){
				frm.doc[item].forEach((item) => {
					total += item.score;
				});
				no_of_questions += frm.doc[item].length;
			}
	  });
		total += frm.doc.work_experience_score?frm.doc.work_experience_score:0;
		no_of_questions += 1;
	}
	else if(frm.doc.interview_question_result){
		frm.doc.interview_question_result.forEach((item) => {
			total += item.score;
		});
		no_of_questions += frm.doc.interview_question_result.length;
	}
  frm.set_value('total_score', total);
  if(total && no_of_questions > 0){
    avg = total/no_of_questions;
  }
  frm.set_value('average_score', avg);
};

var set_interview_template = function(frm) {
  var sections = ['interview_question_result', 'interview_sheet_general', 'interview_sheet_attitude',
		'interview_sheet_technical', 'interview_experience_note'];
  sections.forEach((item) => {
    frm.clear_table(item);
  });
  if(frm.doc.interview_template){
		set_interview_questions(frm);
  }
  else{
		sections.forEach((item) => {
	    frm.refresh_field(item);
	  });
  }
};

var set_interview_questions = function(frm, is_bulk) {
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Interview',
			filters: {name: frm.doc.interview_template}
		},
		callback: function(r) {
			if(r && r.message){
				var is_bulk = r.message.is_bulk;
				frm.set_value('is_bulk', is_bulk);
				if(!is_bulk && r.message.interview_questions){
					set_interview_sheet_child(frm, 'interview_question_result', 'Interview Question Result', r.message.interview_questions);
				}
				else if(is_bulk){
					if(r.message.general_questions){
							set_interview_sheet_child(frm, 'interview_sheet_general', 'Interview Sheet General', r.message.general_questions);
					}
					if(r.message.attitude_questions){
							set_interview_sheet_child(frm, 'interview_sheet_attitude', 'Interview Sheet Attitude', r.message.attitude_questions);
					}
					if(r.message.technical_questions){
							set_interview_sheet_child(frm, 'interview_sheet_technical', 'Interview Sheet Technical', r.message.technical_questions);
					}
				}
			}
		}
	});
};

var set_interview_sheet_child = function(frm, table, table_doctype, interview_questions){
  frm.clear_table(table);
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
  frm.refresh_field(table);
};
