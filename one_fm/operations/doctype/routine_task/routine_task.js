// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Routine Task', {
	refresh: function(frm) {
		set_filters(frm);
		set_custom_buttons(frm);
	}
});

var set_custom_buttons = function(frm) {
	set_task_and_auto_repeat(frm);
	remove_task_and_auto_repeat(frm);
};

var remove_task_and_auto_repeat = function(frm) {
	if (frm.doc.task_reference || frm.doc.auto_repeat_reference){
		frm.add_custom_button(__("Remove Task and Auto Repeat"), function() {
			if(frm.is_dirty()){
				frappe.throw(__('Please Save the Document and Continue .!'))
			}
			else{
				frappe.call({
					method: "remove_task_and_auto_repeat",
					doc: frm.doc,
					callback: function(r){
						if(!r.exc){
							frm.reload_doc()
						}
					},
					freeze: true,
					freeze_message: __('Remove Task and Auto Repeat')
				});
			}
		});
	}
};

var set_task_and_auto_repeat = function(frm) {
	if (!frm.doc.task_reference && !frm.doc.auto_repeat_reference && !frm.doc.is_erp_process){
		frm.add_custom_button(__("Set Task and Auto Repeat"), function() {
			if(frm.is_dirty()){
				frappe.throw(__('Please Save the Document and Continue .!'))
			}
			else{
				frappe.call({
					method: "set_task_and_auto_repeat",
					doc: frm.doc,
					callback: function(r){
						if(!r.exc){
							frm.reload_doc()
						}
					},
					freeze: true,
					freeze_message: __('Setting up Task and Auto Repeat')
				});
			}
		});
	}
};

var set_filters = function(frm) {
	frm.set_query("erp_document", function() {
		return {
			query: "one_fm.operations.doctype.routine_task.routine_task.filter_routine_document",
			filters: {'parent': frm.doc.process_name}
		}
	});

	frm.set_query("task_type", function() {
		return {
			filters: {'is_routine_task': true}
		}
	});
};
