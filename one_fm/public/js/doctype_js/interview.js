frappe.ui.form.on('Interview', {
	refresh: function (frm) {
		frappe.model.get_value("Job Applicant", {"name": frm.doc.job_applicant}, "one_fm_hiring_method", 
		function(res) {
			if(res.one_fm_hiring_method == "Bulk Recruitment"){
				// Bulk Recruitment: feedback is auto-created from Interview Console
				frm.remove_custom_button('Submit Feedback');
				remove_custom_button_from_mobile_view(frm, "Submit Feedback");
				
				// Show editable text box for Interview Summary
				frm.toggle_display('interview_summary', true);
				frm.toggle_display('interview_summary_render', false);
				frm.set_df_property('interview_summary', 'label', 'Interview Summary');
			} else {
				// Non-Bulk: remove standard Submit Feedback and conditionally add custom Submit Interview Feedback
				frm.remove_custom_button('Submit Feedback');
				remove_custom_button_from_mobile_view(frm, "Submit Feedback");

				let allowed_interviewers = [];
				frm.doc.interview_details.forEach(values => {
					allowed_interviewers.push(values.interviewer);
				});
		
				if (frm.doc.docstatus != 2 && !frm.doc.__islocal){
					if ((allowed_interviewers.includes(frappe.session.user))) {
						frappe.db.get_value('Interview Feedback', {'interviewer': frappe.session.user, 'interview': frm.doc.name, 'docstatus': 1}, 'name', (r) => {
							if (Object.keys(r).length === 0) {
								frm.add_custom_button(__('Submit Interview Feedback'), function () {
									frappe.call({
										method: 'one_fm.hiring.utils.get_interview_skill_and_question_set',
										args: {
											interview_round: frm.doc.interview_round,
											interviewer: frappe.session.user,
											interview_name: frm.doc.name,
										},
										callback: function (r) {
											if(r.message){
												frm.events.show_custom_feedback_dialog(frm, r.message[1], r.message[0], r.message[2]);
											}
											frm.refresh();
										},
										freeze: true,
										freeze_message: __("Fetch interview details..!")
									});
								}).addClass('btn-primary');
							}
						});
					}							
				}				
			}	
		})
	},

	// Override: show actual score % for Bulk Recruitment only
	calculate_reviews_per_rating(frm) {
		const reviews_per_rating = [0, 0, 0, 0, 0];
		if (!frm.feedback || !frm.feedback.length) {
			frm.reviews_per_rating = reviews_per_rating;
			return;
		}

		// Check if this is a Bulk Recruitment interview
		frappe.model.get_value("Job Applicant", {"name": frm.doc.job_applicant}, "one_fm_hiring_method",
		function(res) {
			if (res && res.one_fm_hiring_method === "Bulk Recruitment") {
				// Bulk: show actual console score percentage
				frm.feedback.forEach((x) => {
					let score_pct = flt(x.total_score * 20, 1); // 4.95 * 20 = 99%
					let star_idx = Math.min(Math.floor(x.total_score - 1), 4);
					if (star_idx < 0) star_idx = 0;
					reviews_per_rating[star_idx] = score_pct;
				});
			} else {
				// Non-Bulk: use Frappe's default star distribution
				frm.feedback.forEach((x) => {
					reviews_per_rating[Math.floor(x.total_score - 1)] += 1;
				});
				let total = frm.feedback.length;
				for (let i = 0; i < reviews_per_rating.length; i++) {
					reviews_per_rating[i] = flt((reviews_per_rating[i] * 100) / total, 1);
				}
			}
			frm.reviews_per_rating = reviews_per_rating;
			// Re-render feedback with updated percentages
			frm.events.render_feedback(frm);
		});
	},
	show_custom_feedback_dialog: function (frm, data, question_data, feedback_exists) {
		let fields = frm.events.get_fields_for_feedback();
		fields.push({
			fieldtype: 'Data',
			fieldname: 'parent',
			hidden: 1,
			label: __('Parent')
		})
		fields.push({
			fieldtype: 'Data',
			fieldname: 'name',
			hidden: 1,
			label: __('Name')
		})
		var dialog_fields = [
			{
				fieldname: 'skill_set',
				fieldtype: 'Table',
				label: __('Skill Assessment'),
				cannot_add_rows: false,
				in_editable_grid: true,
				reqd: 1,
				fields: fields,
				data: data
			}
		]
		if(question_data && question_data.length > 0){
			let question_fields = frm.events.get_fields_for_questions();
			dialog_fields.push({
				fieldname: 'questions',
				fieldtype: 'Table',
				label: __('Question Assessment'),
				cannot_add_rows: false,
				in_editable_grid: true,
				reqd: 1,
				fields: question_fields,
				data: question_data
			})
		}
		dialog_fields.push(
			{
				fieldname: 'result',
				fieldtype: 'Select',
				options: ['', 'Cleared', 'Rejected'],
				label: __('Result')
			},
			{
				fieldname: 'feedback',
				fieldtype: 'Small Text',
				label: __('Feedback')
			}
		)


		let d = new frappe.ui.Dialog({
			title: __('Submit Feedback'),
			fields: dialog_fields,
			size: 'large',
			minimizable: true,
			primary_action_label: __("Save"),
			primary_action: function(values) {
				create_interview_feedback(frm, values, feedback_exists, 'save');
			},
			secondary_action_label: __("Save and Submit"),
			secondary_action: function() {
				create_interview_feedback(frm, d.get_values(), feedback_exists, 'submit');
				d.hide();
			}
		});
		d.show();
	},

	get_fields_for_questions: function () {
		return [{
			fieldtype: 'Data',
			fieldname: 'questions',
			in_list_view: 1,
			label: __('Question'),
		}, {
			fieldtype: 'Data',
			fieldname: 'answer',
			label: __('Answer'),
		}, {
			fieldtype: 'Float',
			fieldname: 'weight',
			label: __('Weight'),
		}, {
			fieldtype: 'Small Text',
			fieldname: 'applicant_answer',
			label: __('Applicant Answer'),
			in_list_view: 1,
			reqd: 1,
		}, {
			fieldtype: 'Float',
			fieldname: 'score',
			label: __('Score'),
			in_list_view: 1,
			reqd: 1,
		}, {
			fieldtype: 'Data',
			fieldname: 'parent',
			hidden: 1,
			label: __('Parent')
		}, {
			fieldtype: 'Data',
			fieldname: 'name',
			hidden: 1,
			label: __('Name')
		}];

	}

});

var remove_custom_button_from_mobile_view = function(frm, label) {
	// Find the span element with the specified data-label attribute
	var span_element = $(`.menu-item-label[data-label='${encodeURIComponent(label)}']`);
	// Get the parent li element
	var parent_li_element = span_element.closest("li");
	// Hide the parent li element
	parent_li_element.hide();
}

var create_interview_feedback = function(frm, values, feedback_exists, save_submit) {
	var args = {
		data: values,
		interview_name: frm.doc.name,
		interviewer: frappe.session.user,
		job_applicant: frm.doc.job_applicant,
		method: save_submit
	}
	if(feedback_exists){
		args['feedback_exists'] = feedback_exists
	}
	frappe.call({
		method: 'one_fm.hiring.utils.create_interview_feedback',
		args: args
	}).then(() => {
		frm.refresh();
	});
}
