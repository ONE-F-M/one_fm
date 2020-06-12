// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Operations Shift', {
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
									console.log(this);
									return this.data;
								},
								data: [],
							},	
							{'fieldname': 'cb2', 'fieldtype': 'Column Break'},
							{'label': 'Post Type', 'fieldname': 'post_template', 'fieldtype': 'Link', 'options': 'Post Type', onchange: function(){
								let post_type = this.value;
								if(post_type !== undefined){
									frappe.call({
										method:'frappe.client.get',
										args: {
											doctype: 'Post Type',
											name: post_type,
										},
										callback: function(r) {
											if(!r.exc) {
												let {designations, skills} = r.message;
												console.log(designations, skills);
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
									console.log(this);
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
									console.log(this);
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
});