frappe.pages['employee-management'].on_page_load = function(wrapper) {
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
    let argsObject = {employee_id: employee_id};

    if(['enrolled', 'cell_number'].includes(action_type)) {
        if(action_type === 'enrolled') {
            argsObject.field = 'enrolled'
             argsObject.value = 0;
             // make api call
             makeCall(api, argsObject);
        } else if(action_type === 'cell_number') {
            inputDialog(api, action_type, 'Phone Number', argsObject);
        }
    } else if(action_type === 'status') {
        // make api call
        makeCall(api, argsObject);
    }


}

const actions = {
    status: 'enrollment_status',
    enrolled: 'update_employee',
    cell_number: 'update_employee',
}

const inputDialog = (api, field, title, argsObject) => {
    let d = new frappe.ui.Dialog({
        title: 'Enter details',
        fields: [
            {
                label: title,
                fieldname: field,
                fieldtype: 'Data',
                reqd: 1,
            }
        ],
        primary_action_label: 'Continue',
        primary_action(values) {
            argsObject.field = field;
            argsObject.value = values[field];
            makeCall(api, argsObject);
            d.hide();
        }
    });

    d.show();
}

const makeCall = (api, argsObject) => {
    frappe.confirm('Are you sure you want to proceed?',
        () => {
            frappe.call({
                method: "one_fm.api.v1.utils."+api, //dotted path to server method
                args: argsObject,
                callback: function(r) {
                    // code snippet
                    frappe.msgprint(r.message);
                }
            });
        }, () => {
            // action to perform if No is selected
    })
}