// Copyright (c) 2020, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Operations Shift', {
	onload: function (frm) {
		frm.__previous_shift_type = frm.doc.shift_type
	},

	refresh: function(frm) {
		if(!frm.doc.__islocal){
			frm.add_custom_button(
				'Add Posts',
				() => {
					let post_dialog = new frappe.ui.Dialog({
						'fields': [
							{'label': 'Number of Posts', 'fieldname': 'qty', 'fieldtype': 'Int'},
							{
								'label': 'Post Names',
								'fieldname': 'post_names',
								'fieldtype': 'Table',
								'fields': [
									{
										fieldtype:'Data',
										label: __('Post Name'),
										fieldname:'post_name',
										in_list_view:1,
										get_query: function(){},
										onchange:function(){}
									},
								],
								get_data: function() {
									
									return this.data;
								},
								data: [],
							},
							{'fieldname': 'cb2', 'fieldtype': 'Column Break'},
							{'label': 'Operations Role', 'fieldname': 'post_template', 'fieldtype': 'Link', 'options': 'Operations Role', onchange: function(){
								let operations_role = this.value;
								if(operations_role !== undefined){
									frappe.call({
										method:'frappe.client.get',
										args: {
											doctype: 'Operations Role',
											name: operations_role,
										},
										callback: function(r) {
											if(!r.exc) {
												let {designations, skills} = r.message;
												
												post_dialog.fields_dict["skills"].grid.remove_all();
												post_dialog.fields_dict["designations"].grid.remove_all();

												skills.forEach((skill) => {
													post_dialog.fields_dict["skills"].grid.df.data.push(skill);
												});
												post_dialog.fields_dict["skills"].grid.refresh();

												designations.forEach((designation) => {
													post_dialog.fields_dict["designations"].grid.df.data.push(designation);
												});
												post_dialog.fields_dict["designations"].grid.refresh();

											}
										}
									});
								}
							}},
							{'label': 'Post Location', 'fieldname': 'post_location', 'fieldtype': 'Select', 'options': 'Internal\nExternal'},
							{'label': 'Gender', 'default': 'Both', 'fieldname': 'gender', 'fieldtype': 'Select', 'options': 'Male\nFemale\nBoth'},
							{'label': 'Sale Item', 'fieldname': 'sale_item', 'fieldtype': 'Link', 'options':'Item'},
							{'fieldname': 'sb', 'fieldtype': 'Section Break'},
							{
								'label': 'Skills',
								'fieldname': 'skills',
								'fieldtype': 'Table',
								'fields': [
									{
										fieldtype:'Link',
										label: __('Skill'),
										fieldname:'skill',
										options: 'Skill',
										in_list_view:1,
										get_query: function(){},
										onchange:function(){}
									},
									{
										fieldtype:'Column Break',
										fieldname:'cb1',
										get_query: function(){},
										onchange:function(){}
									},
									{
										fieldtype:'Rating',
										label: __('Minimum Proficiency Required'),
										fieldname:'minimum_proficiency_required',
										in_list_view:1,
										get_query: function(){},
										onchange:function(){}
									},
								],
								data: [],
								get_data: function() {
									
									return this.data;
								},
							},
							{
								'label': 'Designations',
								'fieldname': 'designations',
								'fieldtype': 'Table',
								'fields': [
									{
										fieldtype:'Link',
										label: __('Designation'),
										fieldname:'designation',
										options: 'Designation',
										in_list_view:1,
										get_query: function(){},
										onchange:function(){}
									},
									{
										fieldtype:'Column Break',
										fieldname:'cb1',
										get_query: function(){},
										onchange:function(){}
									},
									{
										fieldtype:'Check',
										label: __('Primary'),
										fieldname:'primary',
										in_list_view:1,
										get_query: function(){},
										onchange:function(){}
									},
								],
								get_data: function() {
									
									return this.data;
								},
								data: [],
							},
							{'fieldname': 'sb1', 'fieldtype': 'Section Break'},
							{'label': 'Post Description', 'fieldname': 'post_description', 'fieldtype': 'Small Text'},
						],
						primary_action: function(){
							let values = post_dialog.get_values();
							let {qty, post_names} = values;
							if(post_names === undefined || qty !== post_names.length){frappe.msgprint(__('Please make sure the number of posts and Post names are same.'))};
							frappe.call({
								method:'one_fm.operations.doctype.operations_shift.operations_shift.create_posts',
								args: {
									data: values,
									site_shift: frm.doc.name,
									site: frm.doc.site,
									project: frm.doc.project
								},
								callback: function(r) {
									if(!r.exc) {
									post_dialog.hide();
									}
								}
							});
						}
					});
					post_dialog.show();
					post_dialog.$wrapper.find('.modal-dialog').css('width', '75%');

				}
			).addClass('btn-primary');
		}
	},
	before_save: function(frm) {
		validate_linked_schedules(frm);
	},
	automate_roster: function(frm) {
		// If the flag is set, do nothing to prevent looping
		if (frm.__is_resetting_value) {
			frm.__is_resetting_value = false;
			return;
		}
		if (frm.doc.automate_roster) {
			frappe.confirm(
				__('Are you sure you want to enable automated rostering for this Operations Shift?'),
				() => {
				},
				() => {
					frm.__is_resetting_value = true;
					frm.set_value('automate_roster', 0);
				}
			);
		} else {
			frappe.confirm(
				__('Are you sure you want to disable automated rostering for this Operations Shift?'),
				() => {
				},
				() => {
					frm.__is_resetting_value = true;
					frm.set_value('automate_roster', 1);
				}
			);
		}
	},
	shift_type: function (frm) {
		if (frm.__is_updating_shift_type) return;
	
		frm.__is_updating_shift_type = true;
	
		frappe.confirm(
			__('The Shift Type Change will reflect to the existing Employee Schedules and Shift Assignment starting from today. Are you sure you want to update Shift Type?'),
			() => {
				frm.__is_updating_shift_type = false;
			},
			() => {
				// Ensure operations execute sequentially, reducing unintended re-triggers
				frappe.run_serially([
					() => frm.set_value('shift_type', frm.__previous_shift_type),
					() => frm.refresh_field('shift_type'),
					() => {
						setTimeout(() => {
							frm.__is_updating_shift_type = false;
						}, 100);
					}
				]);
			}
		);
	}
	
});

function  validate_linked_schedules(frm){
	if (frm.doc.status == "Inactive" && !frm.__confirmed_inactive && !frm.is_new()){
		frappe.call({
			method: "one_fm.one_fm.utils.has_linked_schedules",
			args: {
				field: "Operations Shift",
				value: frm.doc.name,
			},
			callback: (response) => {
				if(response.message){
					frappe.confirm(
						"The future Employee Schedules linked to the Operations Shift will be deleted on confirmation. Do you want to proceed?",
						function () {
							frappe.call({
								method:"one_fm.one_fm.utils.delete_linked_schedules",
								args:{
									field: "Operations Shift",
									value: frm.doc.name
								},
								freeze: true,
								freeze_message:__("Deleting Linked Schedules ..."),
								callback: (response) => {
									frm.__confirmed_inactive = true;
									frm.save();
								}
							})
						},
						function () {
							frappe.validated = false;
							frm.reload_doc();
						}
					)
				} else {
					frappe.validated = true
				}
			}
		});
		frappe.validated=false		
	}

}
