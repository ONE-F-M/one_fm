// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Agency Country Process', {
	refresh: function(frm) {

	}
});




frappe.ui.form.on("Agency Process Details", "total_duration", function (frm, cdt, cdn) {
    var total_duration_hour = 0;
    $.each(frm.doc.agency_process_details || [], function (i, d) {
        if(d.total_duration){
            total_duration_hour += flt(d.total_duration);
        }
    });
    frm.set_value("total_duration", total_duration_hour);
});


frappe.ui.form.on("Agency Process Details", "validate", function (frm, cdt, cdn) {
    var total_duration_hour = 0;
    $.each(frm.doc.agency_process_details || [], function (i, d) {
        if(d.total_duration){
            total_duration_hour += flt(d.total_duration);
        }
    });
    frm.set_value("total_duration", total_duration_hour);
});

