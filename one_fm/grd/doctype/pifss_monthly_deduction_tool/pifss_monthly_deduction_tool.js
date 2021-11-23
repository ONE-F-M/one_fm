// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('PIFSS Monthly Deduction Tool', {
	refresh: function(frm){
		// `on_submit` of the `PIFSS Monthly Deduction Tool` it will create button to link it with pifss monthly deduction record
		if(frm.doc.docstatus === 1){
			frm.add_custom_button(__('Go to PIFSS Monthly Deduction'),
			function(){
			frappe.set_route("Form", "PIFSS Monthly Deduction", frm.doc.new_pifss_monthly_deduction)
			}).addClass('btn-primary'); 
  		 }
	}
});
