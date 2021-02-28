// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cleaning Object Tasks', {
	// refresh: function(frm) {

	// }
	task_time_calculation: function(frm){
		
		if(frm.doc.task_rate == undefined){
			var tasktime = frm.doc.task_time;
			frm.set_value("object_task_time", tasktime);
		}
		else {
			var tasktime = frm.doc.size * frm.doc.task_rate;
			frm.set_value("object_task_time", tasktime);
		}
		

	},
	object_name: function(frm) {

		frm.trigger("task_time_calculation");

	},

	task: function(frm) {
		if(frm.doc.task){
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Cleaning Master Tasks',
					filters: {name: frm.doc.cleaning_tools}
				},
				callback: function(r) {
						if(r.message && r.message.cleaning_tools){
							r.message.cleaning_tools.forEach((item, i) =>{
							
							var cleaning_tools = frm.add_child('cleaning_tools');
							cleaning_tools.tool = item.tool;
							cleaning_tools.tool_type = item.tool_type;
							cleaning_tools.quantity = item.quantity;

							});
							
						}
						else{
							frm.set_value('cleaning_tools', '');
						}
						frm.refresh_fields();
				}
			});

			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Cleaning Master Tasks',
					filters: {name: frm.doc.cleaning_consumables}
				},
				callback: function(r) {
						if(r.message && r.message.cleaning_consumables){
							r.message.cleaning_consumables.forEach((item, i) =>{
							
							var cleaning_consumables = frm.add_child('cleaning_consumables');
							cleaning_consumables.consumable = item.consumable;
							cleaning_consumables.consumable_type = item.consumable_type;
							cleaning_consumables.quantity = item.quantity;

							});
							
						}
						else{
							frm.set_value('cleaning_consumables', '');
						}
						frm.refresh_fields();
				}
			});

			
		}

		frm.trigger("task_time_calculation");

		
	},


		

	
	



});
