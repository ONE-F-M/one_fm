// Copyright (c) 2024, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee ID Migrator", {
    onload: function(frm) {
        frm.clear_table("remaining_employees");
        frm.refresh_field("remaining_employees");
        frm.save();
    },
    refresh: function(frm) {
        frm.fields_dict["migrate_remaining_employees"].$input.removeClass("btn-default");
        frm.fields_dict["migrate_remaining_employees"].$input.addClass("btn-primary");

	},
    migrate_remaining_employees(frm) {
        let d = new frappe.ui.Dialog({
            title: "Employee PK Migrator",
            fields: [
                {
                    label: "Status",
                    fieldname: "status",
                    fieldtype: "Select",
                    options: "Active\nVacation\nLeft\nAbsconding\nCourt Case",
                    description: "Migration will be executed for the selected status of employees."
                }
            ],
            size: "small",
            primary_action_label: "Run migration",
            primary_action(values) {
                d.hide();
                let {status} = values;
                var result = Object.groupBy(frm.doc.remaining_employees, emp => emp.status == status)
                let records = result.true;
                frm.call('execute_migration', {'employees': records});
            }
        });
        
        d.show();
    },
    get_remaining_employees (frm){
        frappe.call({
            method: "frappe.client.get_list",
            freeze: true,
            freeze_message: "Fetching employees..!",
            args: {
                "doctype": "Employee",
                "filters": {"name": ["LIKE", "HR-EMP%"]},
                "fields": ["name", "status", "employee_name", "employee_number"],
                "limit_page_length": 9999
            },
            callback: function(r) {
                if (!r.exc) {
                    let employees = r.message; 
                    
                    frm.clear_table("remaining_employees");
                    for(let i=0; i<employees.length; i++){
                        frm.add_child("remaining_employees", {
                            "employee": employees[i].name,
                            "employee_name": employees[i].employee_name,
                            "employee_pk": employees[i].employee_number,
                            "status": employees[i].status,
                        })
                    }
    
                    frm.refresh_field("remaining_employees");
                    frm.save();                
                }
            }
        });
    }
});
