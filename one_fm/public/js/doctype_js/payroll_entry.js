frappe.ui.form.on('Payroll Entry', {
    refresh: function(frm) {
		if (frm.doc.salary_slips_created == 1){
			frm.add_custom_button(__("Download Payroll Bank Export"), function() {
				let payroll_entry = frm.doc.name
				window.open("/files/payroll-entry/" + payroll_entry + ".xlsx", "Download");
			}).addClass("btn-primary");
			frm.add_custom_button(__("Download Payroll Cash Export"), function() {
				let payroll_entry = "Cash-" + frm.doc.name
				window.open("/files/payroll-entry/" + payroll_entry + ".xlsx", "Download");
			}).addClass("btn-primary");
		}
		frm.set_indicator_formatter('employee',
				function(doc) {
					return (doc.justification_needed_on_deduction == 1) ? "orange" : "green";
				}
		);
    },
    email_missing_payment_information: (frm)=>{
        const table_fields = [
    			{
    				fieldname: "recipient", fieldtype: "Link",
    				in_list_view: 1, label: "Recipient",
    				options: "Employee", reqd: 1,
                    get_query: function() {
    					return {
    						"doctype": "Employee",
    						"filters": {
    							"designation": ['IN', 'HR And Finance Director'],
    						}
    					}
    				}
    			}
    		];
        let d = new frappe.ui.Dialog({
        title: 'Send email',
        fields: [
            {
                fieldname: "recipients",
                fieldtype: "Table",
                label: "Recipients",
                cannot_add_rows: false,
                cannot_delete_rows: false,
                in_place_edit: true,
                reqd: 1,
                data: [],
                fields: table_fields
            }
        ],
        primary_action_label: 'Submit',
        primary_action(values) {
            console.log(values);
            d.hide();
            if(values){
                frappe.call({
                    method: "one_fm.api.doc_methods.payroll_entry.email_missing_payment_information",
                    type: "POST",
                    args: {'recipients':values.recipients},
                    freeze: true,
                    freeze_message: "Sending",
                    callback: (r)=>{
                        console.log(r);
                    }
                })

            }
        }
    });

    d.show();

        return 'helo'
    }
});
