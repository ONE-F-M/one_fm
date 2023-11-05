// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cleaning SOP', {
	refresh: function(frm) {
		setfilters(frm)
		
	}


});

var setfilters = function(frm){
	
	frm.set_query("task_name", 'tasks_table', function(frm,cdt,cdn) {
		var d = locals[cdt][cdn];
		if (d.is_instruction) {
			return {
				filters: {
				  'task_type': 'Instructions'
				}
			}
		
		} 
	  });
}



frappe.ui.form.on("Cleaning SOP Task Child Table",{ 
	object_task_time: function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
  
	var hour = 0;
	var minute = 0;
	var second = 0;

	frm.doc.tasks_table.forEach(function(d) { 
		var splittime = d.object_task_time.split(':');

		hour += parseInt(splittime[0]);
		minute += parseInt(splittime[1]);
		second += parseInt(splittime[2]);
	});

	minute = minute/60;
	second =second/60;
	var totaltaskhour = hour + parseInt(minute);
	var totaltaskminute = Math.ceil((minute % 1)*60) + parseInt(second);
	var totaltasksecond = Math.ceil((second % 1)*60) 

	console.log(minute)
	console.log(totaltaskminute)
	console.log(totaltasksecond)

	frm.set_value('total_time', +totaltaskhour+':'+totaltaskminute+':'+totaltasksecond);
	frm.refresh_field('total_time');
	}
	
  
  });


frappe.ui.form.on('Cleaning SOP Task Child Table', {
	is_instruction: function(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "task_name", "")
		var d = locals[cdt][cdn];
		if(d.is_instruction) {
			frappe.model.set_value(cdt, cdn, "doctype_link", "Cleaning Master Tasks")
			// setfilters(frm, cdt,cdn)	
			
		} else {
			frappe.model.set_value(cdt, cdn, "doctype_link", "Cleaning Object Tasks")
			frappe.model.set_value(cdt, cdn, "task_name", "")
		}
		refresh_field("tasks_table")
	},
	task_name: function(frm, cdt, cdn) {
		
		var d = locals[cdt][cdn];
		if(d.task_name && d.doctype_link) {

			frappe.call({
				method:"frappe.client.get",
				args: {
					doctype: d.doctype_link,
					name: d.task_name,
                },
				callback: function(r) {
					if(!r.exc) {
					var data = r.message
					if (d.doctype_link == "Cleaning Master Tasks" ) {
						// frappe.model.set_value(cdt, cdn, "object_name", "" )
						// frappe.model.set_value(cdt, cdn, "size", "")
						// frappe.model.set_value(cdt, cdn, "space", "")
						frappe.model.set_value(cdt, cdn, "object_task_time", data.task_time);
					}
					else if (d.doctype_link == "Cleaning Object Tasks" ){
						frappe.model.set_value(cdt, cdn, "object_name", data.object_name );
						frappe.model.set_value(cdt, cdn, "size", data.size);
						frappe.model.set_value(cdt, cdn, "space", data.space);
						frappe.model.set_value(cdt, cdn, "object_task_time", data.object_task_time);

					}
						
					}
				}
			}
		
			);	
		} else {
			frappe.model.set_value(cdt, cdn, "object_name", "")
			frappe.model.set_value(cdt, cdn, "size", "")
			frappe.model.set_value(cdt, cdn, "space", "")
			frappe.model.set_value(cdt, cdn, "object_task_time", "")
			
		}
		refresh_field("tasks_table")
	},
})