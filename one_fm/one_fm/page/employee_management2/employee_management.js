frappe.pages['employee_management'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Employee Management',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').empty().append(frappe.render_template('employee_management'));
    // Add event listener

    $('#update-form').on('submit', function (e) {
        e.preventDefault();
        processForm()
    })

}

const processForm = () => {
    let employee_id = $('#employee_id')[0].value;
    let action_type = $('#action_type')[0].value;
    let api = actions[action_type];
    console.log(api)

    // make api call
    frappe.confirm('Are you sure you want to proceed?',
        () => {
        console.log("one_fm.api.v1.utils."+api)
            frappe.call({
                method: "one_fm.api.v1.utils."+api, //dotted path to server method
                args: {'employee_id': employee_id},
                callback: function(r) {
                    // code snippet
                    frappe.msgprint(r.message);
                }
            });
        }, () => {
            // action to perform if No is selected
    })
}

const actions = {
    status: 'enrollment_status',
    enrolled: 'update_employee',
    phone: 'update_employee',
}

