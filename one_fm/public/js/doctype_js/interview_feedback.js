frappe.ui.form.on('Interview Feedback', {
	interview_round: function(frm) {
		if (!frm.doc.interview_round) {
			frappe.msgprint(__('Interview Round is missing.'));
			return;
		}
		frappe.call({
			method: 'one_fm.hiring.utils.get_interview_question_set',
			args: {
				interview_round: frm.doc.interview_round
			},
			callback: function(r) {
				frm.set_value('interview_question_assessment', r.message);
			}
		});
	},
});
