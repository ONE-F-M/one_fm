frappe.ui.form.on('Employee', {
	refresh: function(frm) {
		frm.trigger('set_queries');
		frm.trigger('custom_buttons');
	},
	set_queries: frm => {
		// set bank account query
		frm.set_query('bank_account', function() {
			return {
				filters: {
					"party_type": frm.doc.doctype,
					"party": frm.doc.name
				}
			};
		});
	},
	custom_buttons: frm => {
		// add custom buttons to employee doctype
		if (!frm.is_new()){
			// bank account
			let bank_account_btn = document.querySelectorAll('button.btn.btn-new.btn-secondary.btn-xs.icon-btn[data-doctype="Bank Account"]');
			if(bank_account_btn){
					bank_account_btn[0].remove();
			}
			// end modify bank account link
			// add bank account button
			frm.add_custom_button('Bank Account', ()=>{
				frappe.new_doc('Bank Account', {
					party_type:frm.doc.doctype,
					party:frm.doc.name,
					account_name:frm.doc.employee_name,
				})
			}, 'Create');
		}

	}
});


frappe.ui.form.on('Employee Incentive', {
	refresh: function(frm) {
		frm.trigger('set_queries');
	},
	set_queries: frm => {
		// set leave policy query
		frm.set_query('leave_policy', function() {
			return {
				filters: {
					"docstatus": 1
				}
			};
		});
	}
});
