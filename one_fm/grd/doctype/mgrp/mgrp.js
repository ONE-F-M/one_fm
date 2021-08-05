// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('MGRP', {
	attach_mgrp_approval: function(frm){
		set_dates(frm);
	}
});

var set_dates = function(frm){
	frm.set_value('attached_on',frappe.datetime.now_datetime());
}