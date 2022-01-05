// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Operations Site', {
	refresh: function(frm){
		quick_entry_shifts_and_posts(frm);
		frm.set_query("project", function() {
			return {
				"filters": [
					["Project", "project_type", "=", "External"],
				]
			}
		});

		// Remove and change it
		let {changes_log} = frm.doc;
		let changes = ``;
		let ids = ``;
		if(changes_log.length > 0){
			for(let i=0;i<changes_log.length;i++){
				let {name, message, assigned_to} = changes_log[i]
				if(assigned_to == frappe.session.user){
					changes += `<span>${message}<span>\n`;
					ids += `${name},`;
				}
			}
		}
		console.log(changes);
		if(changes && ids){
			frm.add_custom_button(
				__('Review Changes'),
				() => {
					frappe.confirm(
						changes,
						function(){
							frappe.msgprint(__('Changes approved.'));
							changes_action(frm, "Approved", ids);
							window.close();
						},
						function(){
							frappe.msgprint(__('You have rejected the changes. They have been reverted.'));
							changes_action(frm, "Rejected", ids);
							window.close();
						}
					)
				}
			).addClass('btn-primary');
		}
	},
})

function quick_entry_shifts_and_posts(frm){
	if(!frm.doc.__islocal){
		frm.add_custom_button(
			'Add Posts in multiple shifts',
			() => {
				let post_dialog = new frappe.ui.Dialog({
					'fields': [
						{
							'label': 'Select Shifts',
							'fieldname': 'shifts',
							'fieldtype': 'Table',
							'fields': [
								{
									fieldtype:'Link',
									label: __('Operations Shift'),
									fieldname:'shift',
									in_list_view:1,
									get_query: function(){
										return {
											"filters": [
												["Operations Shift", "site", "=", frm.doc.name],
											]
										}
									},
									options: 'Operations Shift',
									onchange:function(){}
								},
							],
							get_data: function() {
								return this.data;
							},
							data: [],
						},
						{'label': 'Post Location', 'fieldname': 'post_location', 'fieldtype': 'Select', 'options': 'Internal\nExternal'},
						{'label': 'Gender', 'default': 'Both', 'fieldname': 'gender', 'fieldtype': 'Select', 'options': 'Male\nFemale\nBoth'},
						{'fieldname': 'cb2', 'fieldtype': 'Column Break'},
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
						console.log(values);
						let {qty, post_names} = values;
						if(post_names === undefined || qty !== post_names.length){frappe.msgprint(__('Please make sure the number of posts and Post names are same.'))};
						frappe.call({
							method:'one_fm.operations.doctype.operations_site.operations_site.create_posts',
							args: {
								data: values,
								site: frm.doc.name,
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
}

function changes_action(frm, action, ids){
	frappe.call('one_fm.operations.doctype.operations_site.operations_site.changes_action', {
		action, ids, parent: frm.doc.name
	}).then((r) => {
		console.log(r);
		frm.reload_doc();
	});
}
frappe.ui.form.on('POC', {
	form_render: function(frm, cdt, cdn) {
		let doc = locals[cdt][cdn];
		if(doc.poc !== undefined){
			get_contact(doc);
		}
	},
	before_poc_remove: function(frm, cdt, cdn){
		if(!frappe.user_roles.includes("Shift Supervisor") && !frappe.user_roles.includes("Site Supervisor")){
			frappe.throw(__("You are not allowed to make changes to POC list."))
		}
	},
	poc: function(frm, cdt, cdn){
		let doc = locals[cdt][cdn];
		if(doc.poc !== undefined){
			get_contact(doc);
		}
	}
});

function get_contact(doc){
	let operations_site_poc = doc.poc;
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Contact',
			name: operations_site_poc
		},
		callback: function(r) {
			if(!r.exc) {
				set_contact(r.message);
			}
		}
	});
}

function set_contact(doc){
	let {email_ids, phone_nos} = doc;
	console.log(email_ids, phone_nos);
	let contact_details = ``;
	for(let i=0; i<email_ids.length;i++){
		contact_details += `<p>Email: ${email_ids[i].email_id}</p>\n`;
	}

	for(let j=0; j<phone_nos.length;j++){
		contact_details += `<p>Phone: ${phone_nos[j].phone}</p>\n`;
	}
	console.log(contact_details);
	$('div[data-fieldname="contact_html"]').empty().append(`<div class="address-box">${contact_details}</div>`);
}
