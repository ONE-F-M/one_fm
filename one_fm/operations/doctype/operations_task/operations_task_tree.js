frappe.provide("frappe.treeview_settings");

frappe.treeview_settings['Operations Task'] = {
	get_tree_nodes: "one_fm.operations.doctype.operations_task.operations_task.get_children",
	add_tree_node: "one_fm.operations.doctype.operations_task.operations_task.add_node",
	filters: [
		{
			fieldname: "project",
			fieldtype:"Link",
			options: "Operations Project",
			label: __("Operations Project"),
		},
		{
			fieldname: "task",
			fieldtype:"Link",
			options: "Operations Task",
			label: __("Operations Task"),
			get_query: function() {
				var me = frappe.treeview_settings['Operations Task'];
				var project = me.page.fields_dict.project.get_value();
				var args = [["Task", 'is_group', '=', 1]];
				if(project){
					args.push(["Task", 'project', "=", project]);
				}
				return {
					filters: args
				};
			}
		}
	],
	breadcrumb: "Projects",
	get_tree_root: false,
	root_label: "All Tasks",
	ignore_fields: ["parent_task"],
	onload: function(me) {
		frappe.treeview_settings['Operations Task'].page = {};
		$.extend(frappe.treeview_settings['Operations Task'].page, me.page);
		me.make_tree();
	},
	toolbar: [
		{
			label:__("Add Multiple"),
			condition: function(node) {
				return node.expandable;
			},
			click: function(node) {
				this.data = [];
				const dialog = new frappe.ui.Dialog({
					title: __("Add Multiple Tasks"),
					fields: [
						{
							fieldname: "multiple_tasks", fieldtype: "Table",
							in_place_edit: true, data: this.data,
							get_data: () => {
								return this.data;
							},
							fields: [{
								fieldtype:'Data',
								fieldname:"subject",
								in_list_view: 1,
								reqd: 1,
								label: __("Subject")
							}]
						},
					],
					primary_action: function() {
						dialog.hide();
						return frappe.call({
							method: "one_fm.operations.doctype.operations_task.operations_task.add_multiple_tasks",
							args: {
								data: dialog.get_values()["multiple_tasks"],
								parent: node.data.value
							},
							callback: function() { }
						});
					},
					primary_action_label: __('Create')
				});
				dialog.show();
			}
		}
	],
	extend_toolbar: true
};