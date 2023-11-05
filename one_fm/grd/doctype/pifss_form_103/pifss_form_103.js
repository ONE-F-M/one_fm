frappe.ui.form.on('PIFSS Form 103', {
	
	onload: function(frm){
		frm.set_query("employee", function() {//filtering employee field to list only kuwaiti employee as this process only for Kuwaiti's
			return {
				"filters": {
					"one_fm_nationality": "Kuwaiti",
				}
			};
		});
		frm.set_query("pifss_authorized_signatory", function() {
			return {//setting default value in a company field to be `ONE Facilities Management`
				"filters": {
					"company": "ONE Facilities Management",
					"is_active": 1,
				}
			};
		})	
		
	},
	
	refresh: function(frm){
		if(!frm.doc.__islocal){
			frm.set_df_property("request_type","read_only", 1);
		} 
		if(frm.doc.company_name){
			frappe.call({//This method runs on `refresh` and it passes (company name) and fetch list of `authorized_signatory_name_arabic` and setting it to `signatory_name` field
				method: "one_fm.grd.doctype.pifss_form_103.pifss_form_103.get_signatory_name",
				args:{
					'parent': frm.doc.company_name,
					},
				callback:function(r){
					frm.set_df_property('signatory_name', "options", r.message);
					frm.refresh_field("signatory_name");
					}
				});
		}
		else{
			frm.set_df_property('signatory_name', "options", null);
			frm.refresh_field("signatory_name");
		}
		if(frm.doc.status == "Awaiting Response" && frm.doc.notify_grd_operator == 0){
			// send message box to grd user once state of the document is `Awaiting Response` which means waiting for pifss website response (Accept-Reject) for employee request (Registration - End of Service)
			send_message(frm);
		}
		if (frm.doc.docstatus ==1 && frm.doc.request_type == "End of Service" && frm.doc.status != "Rejected") {
			
			frm.add_custom_button(__('PAM - Work Permit Cancellation'),
				function(){// on_submit of `End of Service` record a button `PAM - Work Permit Cancellation` will show to cancel employee work permit
					
					frappe.model.open_mapped_doc({
					method: "one_fm.grd.utils.mappe_to_work_permit_cancellation",
					frm: frm
          			});
				}).addClass('btn-primary');
				
		}if (frm.doc.docstatus == 1 && frm.doc.request_type == "Registration" && frm.doc.status != "Rejected") {
			
			frm.add_custom_button(__('PAM - Work Permit Registration'),
				function(){// on_submit of `Registration` record a button `PAM - Work Permit Registration` will show to create employee work permit
					
					frappe.model.open_mapped_doc({
					method: "one_fm.grd.utils.mappe_to_work_permit_registration",
					frm: frm
          			});
				}).addClass('btn-primary');			
		} 
		if (frm.doc.docstatus == 1 && frm.doc.workflow_state == "Rejected") {
			
			frm.add_custom_button(__('Re-Apply PIFSS Form 103'),
				function(){// This Method runs when operator re-apply for a rejected PIFSS Form 103
					frappe.call({
					method: "one_fm.grd.doctype.pifss_form_103.pifss_form_103.create_103_form",
					args: {
						'param': frm.doc.employee,
						'dateofrequest': frm.doc.date_of_request,
						'rt': frm.doc.request_type,
						'cn': frm.doc.company_name,
						'sn': frm.doc.signatory_name,
						'sf': frm.doc.attach_signed_form,

					},
					callback: function(r){
						if(r.message){
							var doclist = frappe.model.sync(r.message);
							frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
						}

					}
          			});
				}).addClass('btn-primary');			
		} 
	},
	company_name: function(frm){
		if(frm.doc.company_name){
			frappe.call({// This method runs on setting `company_name` value and it passes (company name) and fetch list of `authorized_signatory_name_arabic` and setting it to `signatory_name` field
				method: "one_fm.grd.doctype.pifss_form_103.pifss_form_103.get_signatory_name",
				args:{
					'parent': frm.doc.company_name,
					},
				callback:function(r){
					frm.set_df_property('signatory_name', "options", r.message);
					frm.refresh_field("signatory_name");
					}
				});
		}
		else{
			frm.set_df_property('signatory_name', "options", null);
			frm.refresh_field("signatory_name");
		}
	},
	employee: function(frm) {// This method fetches the attached documents in employee doctype to PIFSS Form 103 record based upon `request_type`
		let {employee, request_type} = frm.doc;
		if(employee && request_type === "Registration"){
			frappe.db.get_doc("Employee", employee)
			.then(res => {
				let {one_fm_employee_documents} = res;
				one_fm_employee_documents.forEach(function(i, v){
					if(i.document_name == "Birth Certificate"){
						frm.set_value("date_of_birth_certificate", i.attach);
					}else if(i.document_name == "Nationality Proof"){
						frm.set_value("nationality_proof", i.attach);	
					}else if(i.document_name == "Civil ID"){
						frm.set_value("civil_id_copy", i.attach);
					}else if(i.document_name == "Work Contract"){
						frm.set_value("employment_contract", i.attach);
					}else if(i.document_name == "Social Security Clearance"){
						frm.set_value("social_security_clearance", i.attach);
					}
				})
			})
		}if(employee && request_type === "End of Service"){
			frappe.db.get_doc("Employee", employee)
			.then(res => {
				let {one_fm_employee_documents} = res;
				one_fm_employee_documents.forEach(function(i, v){
					if(i.document_name == "Birth Certificate"){
						frm.set_value("date_of_birth_certificate", i.attach);
					}else if(i.document_name == "Nationality Proof"){
						frm.set_value("nationality_proof", i.attach);	
					}else if(i.document_name == "Civil ID"){
						frm.set_value("civil_id_copy", i.attach);
					}else if(i.document_name == "Resignation Form"){
						frm.set_value("attach_resignationtermination", i.attach);
					}
				})
			})
		}
		set_employee_details(frm);

	},
	request_type: function(frm) {// Customize naming series upon `request_type`
		let {request_type} = frm.doc;
		if(request_type === "Registration"){
			frm.set_value("naming_series", "REG-.{employee}.-");
		}else if(request_type === "End of Service"){
			frm.set_value("naming_series", "END-.{employee}.-");
		}
	},
	signatory_name: function(frm){// This method fetches user_id from based on the selected authorized name
		if(frm.doc.signatory_name){
		frappe.call({
			method: "one_fm.grd.doctype.pifss_form_103.pifss_form_103.get_signatory_user",
			args:{
				'user_name':frm.doc.signatory_name,
				},
			callback:function(r){
				frm.set_value('user',r.message[0]);
				frm.set_value('authorized_signature',r.message[1]);
				frm.refresh_field("user");
				frm.refresh_field("authorized_signature");
				}
			});
	}
	else{
		frm.set_value('user'," ")
		frm.refresh_field("user");
	}
},
user: function(frm){
	frm.set_value('notify_for_signature',0)
	frm.set_value('signature_date',frappe.datetime.now_date())
	frm.set_value('employee_signature_date',frappe.datetime.now_date())
	
},
reference_number: function(frm){
	if(frm.doc.reference_number){
		set_registered_date_on_pifss(frm);
	}
	
},
attach_end_of_service_from_pifss_website: function(frm){// Auto set datatime field 
	if(frm.doc.attach_end_of_service_from_pifss_website){
		frm.set_value('attach_on_end_of_service',frappe.datetime.now_datetime())
	}
},
attach_registration_from_pifss_website: function(frm){// Auto set datatime field 
	if(frm.doc.attach_registration_from_pifss_website){
		frm.set_value('attach_on_registration',frappe.datetime.now_datetime())
	}
},

});
var set_employee_details = function(frm){
    
    if(frm.doc.employee){
        frappe.call({
            method:"frappe.client.get_value",//api calls
            args: {
                doctype:"Employee",
                filters: {
                name: frm.doc.employee
                },
                fieldname:["employee_name","one_fm_first_name_in_arabic","one_fm_second_name_in_arabic","one_fm_third_name_in_arabic","one_fm_last_name_in_arabic","one_fm_civil_id","cell_number","permanent_address","date_of_birth","nationality_no","nationality_subject","date_of_naturalization","date_of_joining","one_fm_pam_designation","one_fm_basic_salary"]
            }, 
            callback: function(r) { 
        
                // set the returned value in a field
				frm.set_value('employee_name', r.employee_name);
				frm.set_value('first_name', r.one_fm_first_name_in_arabic);
				frm.set_value('second_name', r.one_fm_second_name_in_arabic);
				frm.set_value('third_name', r.one_fm_third_name_in_arabic);
				frm.set_value('last_name', r.one_fm_last_name_in_arabic);
				frm.set_value('civil_id', r.message.one_fm_civil_id);
				frm.set_value('mobile', r.cell_number);
				frm.set_value('address', r.permanent_address);
				frm.set_value('date_of_birth', r.date_of_birth);
				frm.set_value('nationality_no', r.nationality_no);
				frm.set_value('nationality_subject', r.nationality_subject);
				frm.set_value('date_of_naturalization', r.date_of_naturalization);
                frm.set_value('date_of_joining', r.message.date_of_joining);
				frm.set_value('subscription_start_date', r.message.date_of_joining);
				frm.set_value('position', r.message.one_fm_pam_designation);
				frm.set_value('employment_contract', r.message.one_fm_basic_salary);
            }
        })
    }
};
var send_message = function(frm){
	if(frm.doc.workflow_state == "Awaiting Response"){
		frappe.msgprint({
			title: __('Message'),
			indicator: 'green',
			message: __('You Will be Recieving Notification to Check Employee Status via PIFSS Website')
		});
		frm.set_value("notify_grd_operator", 1);
	}
	
};
var set_registered_date_on_pifss = function(frm){
	if(frm.doc.reference_number){// Auto set datatime field 
	frm.set_value('registered_on',frappe.datetime.now_datetime())
	}
};
