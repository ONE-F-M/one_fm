// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

// frappe.ui.form.on('Economic Activity Table', {
// 	// refresh: function(frm) {

// 	// }
// });
frappe.ui.form.on("PAM File Modified",'Economic Activity Table',{
	licence_number:function(frm) {
			if (frm.doc.licence_number == 'T4 - 20201800005')
			{
				frm.set_value("activity_code","M594");
				frm.set_value("activity_description","Airport construction contracting");
				frm.set_value("amainly","Mainly");
			}
			else if (frm.doc.licence_number == 'Opera - 15201800010')
			{
				frm.set_value("activity_code","M1000");
				frm.set_value("activity_description","Guarding Facilities By Individuals");
				frm.set_value("amainly","Mainly");
			}
			else if (frm.doc.licence_number == 'Private - 2921143')
			{
				frm.set_value("activity_code","X6760");
				frm.set_value("activity_description","Public Utilities Department");
				frm.set_value("amainly","Mainly");
			   
			}
		}
	});