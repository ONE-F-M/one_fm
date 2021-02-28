// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Checkpoints Route Assignment', {
	validate : function (frm){
		if (frm.doc.never_ending == 0){
			if (frm.doc.start_date > frm.doc.end_date) {
				frappe.msgprint(__("End Date needs to be After Start Date"));
				frappe.validated = false;
			}

		}

		if (frm.doc.never_ending == 1){
			frm.set_value("end_date", "");
			cur_frm.refresh_field("end_date");
		}

		
		if (frm.doc.assign_to_employee == 0 && frm.doc.assign_to_post == 0){
			frappe.throw(__("Please Assign to Employee or Post"));
		}

		if (frm.doc.daily_repeat == 0 && frm.doc.weekly_repeat == 0){
			frappe.throw(__("Please Select Daily or Weekly Repeat"));
		}

	},
	
	
	loose_schedule: function(frm) {
		if (frm.doc.loose_schedule == 1) {
			cur_frm.clear_table("checkpoints_route_table");
			cur_frm.refresh_fields("checkpoints_route_table");
			frm.set_df_property("start_time", "reqd", 1);
			frm.set_df_property("end_time", "reqd", 1);
			frm.set_df_property("checkpoints_route_assignment_loose_schedule_table", "reqd", 1);
			frm.set_df_property("checkpoints_route_table", "reqd", 0);
            
		}

		if (frm.doc.loose_schedule == 0) {
			frm.set_value("start_time", "");
			frm.set_value("end_time", "");
			cur_frm.clear_table("checkpoints_route_assignment_loose_schedule_table");
			cur_frm.refresh_field("checkpoints_route_assignment_loose_schedule_table");
			frm.set_df_property("checkpoints_route_assignment_loose_schedule_table", "reqd", 0);
			frm.set_df_property("checkpoints_route_table", "reqd", 1);
			frm.set_df_property("start_time", "reqd", 0);
			frm.set_df_property("end_time", "reqd", 0);
            
		}

	},
	assign_to_employee: function(frm) {
		if (frm.doc.assign_to_employee == 1) {
			frm.set_value("assign_to_post", undefined);
			frm.set_value("post", "");
			frm.set_value("post_name", "");
			cur_frm.refresh_field("post");
			cur_frm.refresh_field("post_name");
			frm.set_df_property("employee", "reqd", 1);
			frm.set_df_property("post", "reqd", 0);
            
		}
	},
	assign_to_post: function(frm) {

		if (frm.doc.assign_to_post == 1) {
			frm.set_value("assign_to_employee", "0");
			frm.set_value("employee", "");
			frm.set_value("employee_name", "");
			cur_frm.refresh_fields("employee");
			cur_frm.refresh_fields("employee_name");
			frm.set_df_property("post", "reqd", 1);
			frm.set_df_property("employee", "reqd", 0);
            
		}

	},
	weekly_repeat: function(frm) {

		if (frm.doc.weekly_repeat == 1) {
			frm.set_value("daily_repeat", "0");
			cur_frm.refresh_fields("daily_repeat");
			frm.set_df_property("start_date", "reqd", 1);
			frm.set_df_property("end_date", "reqd", 1);
			frm.set_df_property("never_ending", "reqd", 1);
            
		}
	

		if (frm.doc.weekly_repeat == 0 && frm.doc.daily_repeat == 0) {
			frm.set_value("start_date", "");
			frm.set_value("end_date", "");
			frm.set_value("never_ending", "0");
			frm.set_value("hourly_repeat", "0");
			frm.set_value("repeat__duration_hour", "");
			frm.set_value("repeat_duration_minute", "");
			frm.set_df_property("start_date", "reqd", 0);
			frm.set_df_property("end_date", "reqd", 0);
			frm.set_df_property("never_ending", "reqd", 0);
            
		}

	},
	never_ending: function(frm) {
		if (frm.doc.never_ending == 1){
			frm.set_df_property("end_date", "reqd", 0);
			frm.set_df_property("end_date", "read_only", 1);
		}
		if (frm.doc.never_ending == 0){
			frm.set_df_property("end_date", "reqd", 1);
			frm.set_df_property("end_date", "read_only", 0);
		}
	},

	daily_repeat: function(frm) {

		if (frm.doc.daily_repeat == 1) {
			frm.set_value("weekly_repeat", "0");
			frm.set_value("sunday", "0");
			frm.set_value("monday", "0");
			frm.set_value("tuesday", "0");
			frm.set_value("wednesday", "0");
			frm.set_value("thursday", "0");
			frm.set_value("friday", "0");
			frm.set_value("saturday", "0");
			cur_frm.refresh_fields("weekly_repeat");
			cur_frm.refresh_fields("sunday");
			cur_frm.refresh_fields("monday");
			cur_frm.refresh_fields("tuesday");
			cur_frm.refresh_fields("wednesday");
			cur_frm.refresh_fields("thursday");
			cur_frm.refresh_fields("friday");
			cur_frm.refresh_fields("saturday");
			frm.set_df_property("start_date", "reqd", 1);
			frm.set_df_property("end_date", "reqd", 1);
			frm.set_df_property("never_ending", "reqd", 1);
            
		}

		if (frm.doc.weekly_repeat == 0 && frm.doc.daily_repeat == 0) {
			frm.set_value("start_date", "");
			frm.set_value("end_date", "");
			frm.set_value("never_ending", "0");
			frm.set_value("hourly_repeat", "0");
			frm.set_value("repeat__duration_hour", "");
			frm.set_value("repeat_duration_minute", "");
			frm.set_df_property("start_date", "reqd", 0);
			frm.set_df_property("end_date", "reqd", 0);
			frm.set_df_property("never_ending", "reqd", 0);
			frm.set_df_property("start_date", "reqd", 0);
			frm.set_df_property("end_date", "reqd", 0);
			frm.set_df_property("never_ending", "reqd", 0);
            
		}

	},

	hourly_repeat: function(frm) {
		if(frm.doc.hourly_repeat == 1){
			frm.set_df_property("repeat_duration", "reqd", 1);
			frm.set_df_property("repeat_end_time", "reqd", 1);
			frm.set_df_property("end_time", "read_only", 1);
			frm.set_value("repeat_end_time",frm.doc.end_time)

		}
		if(frm.doc.hourly_repeat == 0){
			frm.set_df_property("repeat_duration", "reqd", 0);
			frm.set_df_property("end_time", "read_only", 0);
			frm.set_df_property("repeat_end_time", "reqd", 0);
		}
	},

	setup: function(frm) {
		frm.set_query("project", function() {
			return {
				filters: {
					"project_type": 'External'
				}
					
				
			}
		});

		frm.set_query("site", function() {
			return {
				filters: {
					"project": frm.doc.project
				}
					
				
			}
		});

	}

});

// frappe.ui.form.on("Checkpoints Route Assignment", "validate", function(frm) {
	// if (frm.doc.start_date > frm.doc.end_date) {
	// 	frappe.msgprint(__("End Date needs to be After Start Date"));
	// 	frappe.validated = false;
	// }

	
// });