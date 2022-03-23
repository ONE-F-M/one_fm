frappe.ui.form.on('Interview', {
	refresh: function (frm) {
		frm.remove_custom_button('Submit Feedback')
		let allowed_interviewers = [];
		frm.doc.interview_details.forEach(values => {
			allowed_interviewers.push(values.interviewer);
		});
		if (frm.doc.docstatus != 2 && !frm.doc.__islocal) {
			if ((allowed_interviewers.includes(frappe.session.user))) {
				frappe.db.get_value('Interview Feedback', {'interviewer': frappe.session.user, 'interview': frm.doc.name, 'docstatus': 1}, 'name', (r) => {
					if (Object.keys(r).length === 0) {
						frm.add_custom_button(__('Submit Interview Feedback'), function () {
							frappe.call({
								method: 'one_fm.hiring.utils.get_interview_skill_and_question_set',
								args: {
									interview_round: frm.doc.interview_round
								},
								callback: function (r) {
									if(r.message){
										frm.events.show_custom_feedback_dialog(frm, r.message[1], r.message[0]);
									}
									frm.refresh();
								}
							});
						}).addClass('btn-primary');
					}
				});
			}
		}
	},
	show_custom_feedback_dialog: function (frm, data, question_data) {
		let fields = frm.events.get_fields_for_feedback();
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
			primary_action: function(values) {
				frappe.call({
					method: 'one_fm.hiring.utils.create_interview_feedback',
					args: {
						data: values,
						interview_name: frm.doc.name,
						interviewer: frappe.session.user,
						job_applicant: frm.doc.job_applicant
					}
				}).then(() => {
					frm.refresh();
				});
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
			fieldtype: 'Data',
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
		}];

	},
});
