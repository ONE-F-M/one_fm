// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cleaning SOP', {
	// refresh: function(frm) {

	// }


});

frappe.ui.form.on("Cleaning SOP Task Child Table",{ 
	object_task_time: function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
  
	var total = 0;
	frm.doc.tasks_table.forEach(function(d) { total += d.object_task_time; });
  
	console.log(total)
	frm.set_value('total_time', total);
	frm.refresh_field('total_time');
	}
	
  
  });
