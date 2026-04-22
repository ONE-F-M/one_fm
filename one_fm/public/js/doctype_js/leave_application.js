frappe.ui.form.on("Leave Application", {
    before_workflow_action:async function(frm) {
        if (frm.selected_workflow_action === "Accept Proposed Dates") {
            frm.set_value("from_date", frm.doc.custom_propose_from_date);
            frm.set_value("to_date", frm.doc.custom_propose_to_date);
            frm.set_value("total_leave_days", frm.doc.custom_total_propose_leave_days);
            frm.refresh_field("from_date");
            frm.refresh_field("to_date");
            frm.refresh_field("total_leave_days");
            frappe.msgprint("Leave updated");
        }
        if (frm.selected_workflow_action == 'Cancel') {
            try {
                await new Promise((resolve, reject) => {
                    frappe.dom.unfreeze();
                    frappe.prompt(
                        [
                            {
                                label: 'Reason for Cancelling',
                                fieldname: 'reason',
                                fieldtype: 'Small Text',
                                reqd: 1
                            }
                        ],
                        function(values) {
                            if (!values.reason || values.reason.length <= 10 || values.reason.trim() === "" || values.reason.trim().length < 3) {
                                frappe.msgprint({
                                    title: __('Too Short'),
                                    message: __('Please ensure to provide a description of the reason'),
                                    indicator: 'red'
                                });
                            } else {
                                frappe.dom.freeze();
                                frm.set_value('custom_reason_for_cancel', values.reason);
                                frm.refresh_field("custom_reason_for_cancel");
                                frm.save()
                                    .then(resolve)
                                    .catch(reject);
                            }
                        },
                        'Enter Reason',
                        'Proceed to Leave Cancellation'
                    );
                });
            } catch (error) {
                frappe.dom.unfreeze();
                frappe.throw(error?.message || 'Something went wrong in cancelling leave. Try again later');
            }
        }
        if (frm.selected_workflow_action === "Propose New Dates") {
            try {
                await new Promise((resolve, reject) => {
                    frappe.dom.unfreeze();
                    handle_propose_new_date_action(frm)
                        .then(resolve)
                        .catch(reject);
                });
            } catch (error) {
                frappe.dom.unfreeze();
                frappe.throw(error?.message || 'Something went wrong while proposing new dates. Try again later');
            }
        }
        
    },  
    refresh: function(frm) {
        // frm.set_intro("Please save the form after adding a new row to the Proof Documents table before attaching the document")
        if (!frm.is_new()){
            frappe.call({
                method: 'one_fm.utils.enable_edit_leave_application',
                args: {
                    doc: frm.doc
                },
                callback: function(r) {
                    var fields = ['is_proof_document_required', 'from_date','leave_approver']
                    for (var i in fields){
                        if (r && r.message) {
                            cur_frm.set_df_property(fields[i],  'read_only', 0);
                        }
                        else{
                            cur_frm.set_df_property(fields[i],  'read_only', 1);
                            cur_frm.set_df_property(fields[i],  'read_only_depends_on', "eval:doc.workflow_state=='Open' || doc.workflow_state=='Approved' || doc.workflow_state=='Rejected'");
                        }
                    }

                }
            })
            // check approvers
            if(frm.doc.workflow_state=='Open' && frappe.session.user!=frm.doc.leave_approver){
                $('.actions-btn-group').hide();
            }
            if (frm.doc.workflow_state=='Open' && frappe.user.has_role('HR Manager')){
                $('.actions-btn-group').show();
                // $('.btn .btn-primary .btn-sm').show();
            }
        }
        if (frm.doc.status == 'Approved' && frm.doc.__onload && frm.doc.__onload.attendance_not_created){
          frm.add_custom_button(__('Update Attendance'),
            function () {
              frappe.call({
                doc: frm.doc,
                method: 'update_attendance',
                callback: function(r) {
                  frm.reload_doc();
                }
              });
            }
          );
        }
        updateCustomIsPaidVisibility(frm)
        manage_leave_extension(frm)
        // Leave Handover Creation
		if (frm.doc.status == 'Approved') {
			frm.add_custom_button(__('Leave Handover'), function() {
				frappe.call({
					method: 'one_fm.one_fm.doctype.leave_handover.leave_handover.get_handover_data',
					args: {
						leave_application: frm.doc.name
					},
					callback: function(r) {
						if (r.message) {
							frappe.model.with_doctype('Leave Handover', function() {
								var doc = frappe.model.get_new_doc('Leave Handover');
								doc.employee = r.message.employee;
								doc.employee_name = r.message.employee_name;
								doc.leave_application = r.message.leave_application;
								doc.leave_start_date = r.message.leave_start_date;
								doc.resumption_date = r.message.resumption_date;
								if (r.message.handover_items) {
									r.message.handover_items.forEach(item => {
										var child = frappe.model.add_child(doc, 'Handover Item', 'handover_items');
										child.reference_doctype = item.reference_doctype;
										child.reference_docname = item.reference_docname;
										child.role = item.role;
									});
								}
								frappe.set_route('Form', 'Leave Handover', doc.name);
							});
						}
					},
					freeze: true,
					freeze_message: __("Creating Leave Handover...")
				});
			}, __('Create'));

			if (frm.doc.custom_in_accommodation) {
				frm.add_custom_button(__('Accommodation Leave Movement'), function() {
					frappe.new_doc('Accommodation Leave Movement', {
						leave_application: frm.doc.name,
						employee: frm.doc.employee
					});
				}, __('Create'));
			}
		}
    },
    onload: function(frm) {
        $.each(frm.fields_dict, function(fieldname, field) {
          field.df.onchange = frm =>{
            if (cur_frm.doc.employee && cur_frm.doc.leave_type == "Sick Leave"){
                frappe.db.get_value("Employee", cur_frm.doc.employee, "is_in_kuwait").then(res=>{
                    res.message.is_in_kuwait ? cur_frm.set_value("is_proof_document_required", 1) : cur_frm.set_value("is_proof_document_required", 0)
                    cur_frm.refresh_field("is_proof_document_required")

                })
            }
          };
        });
        prefillForm(frm);
      },
    validate: function(frm) {
        validate_reliever(frm);
    },
    custom_reliever_: function(frm){
        validate_reliever(frm);
    },


    leave_type: function(frm) {
        updateCustomIsPaidVisibility(frm);
    },

    resumption_date: function(frm) {
        if (frm.doc.resumption_date && frm.doc.from_date) {
            let resumption = frappe.datetime.str_to_obj(frm.doc.resumption_date);
            let from_date = frappe.datetime.str_to_obj(frm.doc.from_date);

            if (resumption <= from_date) {
                frappe.msgprint(__('Resumption Date cannot be less than or equal to From Date'));
                frm.set_value("resumption_date", null);
                frm.set_value("to_date", null);
                frm.set_value("total_leave_days", 0);
                return;
            }

            let to_date = frappe.datetime.add_days(resumption, -1);
            frm.set_value("to_date", frappe.datetime.obj_to_str(to_date));
        }

        frm.trigger("make_dashboard");
        frm.trigger("half_day_datepicker");
        frm.trigger("calculate_total_days");
    }
})

async function handle_propose_new_date_action(frm) {
    return new Promise((resolve, reject) => {
        const dialog = new frappe.ui.Dialog({
            title: 'Confirm New Dates',
            fields: [
                {
                    fieldtype: 'Date',
                    fieldname: 'custom_propose_from_date',
                    label: 'Proposed From Date',
                    default: frm.doc.custom_propose_from_date,
                    reqd: 1,
                    change: () => calculate_days(frm, dialog)
                },
                {
                    fieldtype: 'Date',
                    fieldname: 'custom_propose_to_date',
                    label: 'Proposed To Date',
                    default: frm.doc.custom_propose_to_date,
                    reqd: 1,
                    change: () => calculate_days(frm, dialog)
                },
                {
                    fieldtype: 'Data',
                    fieldname: 'custom_total_propose_leave_days',
                    label: 'Total Number of Proposed Days',
                    read_only: 1,
                    default: '0'
                }
            ],
            primary_action_label: 'Confirm',
            primary_action(values) {
                const from_date = values.custom_propose_from_date;
                const to_date = values.custom_propose_to_date;
                const total_days = dialog.get_value('custom_total_propose_leave_days');

                validate_proposeddate(frm, from_date, to_date, dialog)
                    .then(is_valid => {
                        if (is_valid) {
                            frm.set_value('custom_propose_from_date', from_date);
                            frm.set_value('custom_propose_to_date', to_date);
                            frm.set_value('custom_total_propose_leave_days', total_days);
                            dialog.hide();
                            frappe.dom.freeze();
                            frm.save()
                                .then(() => {
                                    frappe.msgprint("New dates proposed successfully");
                                    resolve(frm.reload_doc());
                                })
                                .catch((err) => {
                                    frappe.throw(err.message || 'Error saving proposed dates');
                                    reject(err);
                                });
                        } else {
                            reject(new Error('Invalid date selection'));
                        }
                    })
                    .catch(reject);
            }
        });
        dialog.show();
    });
}



var prefillForm = frm => {
    const url = new URL(window.location.href);

    const params = new URLSearchParams(url.search);

    const doc_id = params.get('doc_id');
    const doctype = params.get('doctype');

    if (doctype == "Attendance Check"){
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                'doctype': doctype,
                'filters': {'name': doc_id},
                'fieldname': [
                    "employee"
                ]
            },
            callback: function(r) {
                if (r.message) {
                    cur_frm.set_value("employee", r.message.employee)

                }
            }
        });
    }

}


var validate_reliever = (frm) => {
    if (frm.doc.custom_reliever_){
        if (frm.doc.custom_reliever_ == frm.doc.employee){
            frappe.throw("Oops! You can't assign yourself as the reliever!")
        }
    }
}


var calculate_days = function (frm,dialog) {
    let from_date = dialog.get_value('custom_propose_from_date');
    let to_date = dialog.get_value('custom_propose_to_date');
    if (from_date && to_date && frm.doc.employee && frm.doc.leave_type) {
        return frappe.call({
            method: "hrms.hr.doctype.leave_application.leave_application.get_number_of_leave_days",
            args: {
                employee: frm.doc.employee,
                leave_type: frm.doc.leave_type,
                from_date: from_date,
                to_date: to_date
            },
            callback: function (r) {
                console.log(r)
                if (r && r.message) {
                    dialog.set_value('custom_total_propose_leave_days', r.message);
                }
            },
        });
    }
}



var validate_proposeddate = (frm, from_date, to_date, dialog) => {
    return new Promise((resolve, reject) => {
        let custom_total_propose_leave_days = dialog.get_value('custom_total_propose_leave_days');
        if (frappe.datetime.get_diff(to_date, from_date) < 0) {
            frappe.throw("Proposed From Date cannot be later than the To Date");
            return reject(false);
        }
        if (frappe.datetime.get_diff(from_date, frappe.datetime.now_date()) < 0) {
            frappe.throw("Proposed From Date cannot be in the past.");
            return reject(false);
        }
        if(frm.doc.custom_propose_from_date && frm.doc.custom_propose_from_date == from_date && frm.doc.custom_propose_to_date && frm.doc.custom_propose_to_date == to_date){
            frappe.throw("Same Date cannot be Proposed.");
            return reject(false);
        }
        frappe.db.get_value("Leave Type", frm.doc.leave_type, "one_fm_is_paid_annual_leave")
            .then(res => {
                if (res.message.one_fm_is_paid_annual_leave && frm.doc.total_leave_days >= 15) {
                    if (custom_total_propose_leave_days < 15) {
                        frappe.throw("You are not allowed to reduce the total leave days below 15 days. Please propose another period.");
                        return reject(false);
                    }
                }
                frappe.call({
                    method: "one_fm.overrides.leave_application.validate_leave_overlap",
                    args: {
                        employee: frm.doc.employee,
                        from_date: from_date,
                        to_date: to_date,
                        name: frm.doc.employee_name
                    },
                    callback: function(response) {
                        if (response.message === "valid") {
                            resolve(true);
                        } else {
                            // Show error message if overlap found
                            frappe.msgprint(response.message, __("Date Validation"));
                            reject(false);
                        }
                    }
                });
            })
    });
};

function updateCustomIsPaidVisibility (frm) {
    if (frm.doc.leave_type) {
        frappe.db.get_value("Leave Type", frm.doc.leave_type, "one_fm_is_paid_annual_leave")
            .then(res => {
                if (res.message) {
                    const isPaidAnnualLeave = res.message.one_fm_is_paid_annual_leave;
                    // Show or hide the custom_is_paid field based on the value
                    frm.set_df_property("custom_is_paid", "hidden", !isPaidAnnualLeave);
                    frm.refresh_field("custom_is_paid");
                }
            });
    } else {
        // Hide the field if no leave_type is selected
        frm.set_df_property("custom_is_paid", "hidden", 1);
        frm.refresh_field("custom_is_paid");
    }
}

function manage_leave_extension(frm) {
    if(!frm.is_new()) {
        frappe.call({
            doc: frm.doc,
            method: 'get_leave_extension_request',
            callback: async function(res) {
                const leaveExtensionRequest = res.message
                
                const thresholdDays = await frappe.db.get_single_value("HR and Payroll Additional Settings", "leave_extension_request_allowance") || 0;

                const today = frappe.datetime.get_today()
                const leavePostingDate = frm.doc.posting_date
                const permittedEndDate = frappe.datetime.add_days(frm.doc.to_date, thresholdDays)

                const isWithinPermittedDateRange = new Date(today) >= new Date(leavePostingDate) && new Date(today) <= new Date(permittedEndDate);

                if(frm.doc.leave_type === 'Annual Leave' && frm.doc.status === 'Approved' && isWithinPermittedDateRange && !leaveExtensionRequest) {
                    frm.add_custom_button(__('Create Leave Extension Request'),
                        function () {                            
                            let d = frappe.prompt([
                                {
                                    fieldname: 'new_resumption_date',
                                    label: 'New Resumption Date',
                                    fieldtype: 'Date',
                                    reqd: true,
                                    description: `Expected Resumption Date: ${frappe.datetime.str_to_user(frm.doc.resumption_date)}`
                                }
                            ],
                            function(values) {
                                frappe.call({
                                    doc: frm.doc,
                                    method: 'create_leave_extension_request',
                                    args: {
                                        new_resumption_date: values.new_resumption_date
                                    },
                                    callback: function(r) {
                                        frappe.set_route('Form', 'Leave Extension Request', r.message.name);
                                    },
                                    freeze: true,
                                    freeze_message: __('Creating Leave Extension..')
                                })
                            },
                            'Leave Extension Request',
                            'Submit');

                            if (frm.doc.resumption_date) {
                                let min_date = frappe.datetime.add_days(frm.doc.resumption_date, 1);
                                d.get_field('new_resumption_date').datepicker.update({
                                    minDate: frappe.datetime.str_to_obj(min_date)
                                });
                            }
                        }
                    );
                }
            }
          });
    }
}
