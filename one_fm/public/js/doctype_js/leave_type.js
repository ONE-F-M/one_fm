frappe.ui.form.on('Leave Type', {
	refresh: function(frm) {
		frm.set_query("salary_component", "one_fm_leave_payment_breakdown", function() {
			return {
				filters: {
					type:'Deduction'
				}
			};
		});
		frm.set_query("one_fm_paid_sick_leave_deduction_salary_component", function() {
			return {
				filters: {
					type:'Deduction'
				}
			};
		});
		frm.set_query("one_fm_paid_sick_leave_type_dependent", function() {
			return {
				filters: {
					one_fm_is_paid_sick_leave: true
				}
			};
		});
	},
	is_lwp: function(frm){
	    if(frm.doc.is_lwp){
	        frm.set_value('one_fm_is_paid_sick_leave', false);
	        frm.set_value('one_fm_is_paid_annual_leave', false);
	    }
	},
	one_fm_is_paid_sick_leave: function(frm){
	    if(frm.doc.one_fm_is_paid_sick_leave){
	        frm.set_value('one_fm_is_hajj_leave', false);
	        frm.set_value('one_fm_is_paid_annual_leave', false);
	    }
	},
	one_fm_is_paid_annual_leave: function(frm){
	    if(frm.doc.one_fm_is_paid_annual_leave){
	        frm.set_value('one_fm_is_paid_sick_leave', false);
	        frm.set_value('one_fm_is_hajj_leave', false);
	    }
	},
	one_fm_is_hajj_leave: function(frm){
	    if(frm.doc.one_fm_is_hajj_leave){
	        frm.set_value('one_fm_is_paid_sick_leave', false);
	        frm.set_value('one_fm_is_paid_annual_leave', false);
	    }
	}
});
