frappe.ui.form.on('Job Applicant', {
	onload: function(frm){
		//getting only accepted erf in the job applicant.
		frm.set_query("one_fm_erf", function() {
			return {
				"filters": {
					"status": "Accepted",
				}
			};
		});
	},
	refresh(frm) {
		// Changes the buttons for `PAM File Number` and `PAM Desigantion` once operator wants to changethe data of any
		if(frm.doc.pam_number_button == 0 || frm.is_new()){
			document.querySelectorAll("[data-fieldname='one_fm_change_pam_file_number']")[1].style.backgroundColor ="#3789ff";
		}if(frm.doc.pam_designation_button == 0 || frm.is_new()){
			document.querySelectorAll("[data-fieldname='one_fm_change_pam_designation']")[1].style.backgroundColor ="#3789ff";
			document.querySelectorAll("[data-fieldname='one_fm_change_pam_designation']")[1].style.marginLeft ='2em';
		}if(frm.doc.pam_number_button == 1 || !frm.is_new()){
			document.querySelectorAll("[data-fieldname='one_fm_change_pam_file_number']")[1].style.backgroundColor ="#ec645e";
		}if(frm.doc.pam_designation_button == 1 || !frm.is_new()){
			document.querySelectorAll("[data-fieldname='one_fm_change_pam_designation']")[1].style.backgroundColor ="#ec645e";
			document.querySelectorAll("[data-fieldname='one_fm_change_pam_designation']")[1].style.marginLeft ='2em';
		}
		document.querySelectorAll("[data-fieldname='one_fm_change_pam_file_number']")[1].style.margin ='1.6em';
		document.querySelectorAll("[data-fieldname='one_fm_change_pam_designation']")[1].style.marginLeft ='2em';
		frm.set_df_property('status', 'label', 'Final Status');
		frm.remove_custom_button("Job Offer");
		set_country_field_empty_on_load(frm);
		set_grd_field_properties(frm);

		hide_job_applicant_existing_fields(frm);
		set_read_only_fields_of_job_applicant(frm);
		set_mandatory_fields_of_job_applicant(frm);
		set_field_properties_on_agency_applying(frm);
		set_mandatory_fields_for_current_employment(frm);


		// if(frm.doc.one_fm_document_verification == 'Verified' || frm.doc.one_fm_document_verification == 'Verified - With Exception'){
			frm.set_df_property('one_fm_interview_schedules', 'hidden', false);
		// }
		// else{
		//frm.set_df_property('one_fm_interview_schedules_section', 'hidden', true);
		//frm.set_df_property('one_fm_interview_schedules', 'hidden', true);
		// }
		if(!frm.doc.__islocal){
			frm.remove_custom_button("Create Interview")
			frm.set_df_property('one_fm_erf', 'read_only', true);
			// add a standard menu item
			frm.add_custom_button(__('Send Career History'), function() {
					send_magic_link(frm, 'one_fm.templates.pages.career_history.send_career_history_magic_link');
					},'Action');
			frm.add_custom_button(__('Send Applicant Doc'), function() {
				send_magic_link(frm, 'one_fm.templates.pages.applicant_docs.send_applicant_doc_magic_link');
				},'Action');
			frm.add_custom_button(__(''), function() {
				},'Action').css({"padding": "0.01rem", "background-color":"gray"});

			// view career history button only when career history exist.
			if(frm.doc.one_fm_job_applicant_score.find(i => i.reference_dt == "Career History")){
			frm.add_custom_button(__('View Career History'), function() {
				view_career_history(frm);
				},'Action');
			} else {
			frm.add_custom_button(__('Create Career History'), function() {
				create_career_history(frm);
				},'Action');
			}
			frm.add_custom_button(__(''), function() {
			},'Action').css({"padding": "0.01rem", "background-color":"gray"});

			// view Interview button only when career history exist.
			if(frm.doc.one_fm_job_applicant_score.find(i => i.reference_dt == "Interview Result")){
				frm.add_custom_button(__('View Interview'), function() {
					view_interview(frm);
				},'Action');
			}
				frm.add_custom_button(__('Create An Interview'), function() {
					view_interview(frm);
				},'Action');

			frm.add_custom_button(__(''), function() {
			},'Action').css({"padding": "0.01rem", "background-color":"gray"});
			frm.add_custom_button(__('Best Reference'), function() {
				    view_best_reference(frm);
				  },'Action');
			frm.add_custom_button(__(''), function() {
			},'Action').css({"padding": "0.01rem", "background-color":"gray"});

			if (frm.doc.__onload && frm.doc.__onload.job_offer) {
				if(frm.doc.status != 'Accepted' && frm.doc.status != 'Rejected'){
					frm.add_custom_button(__('Accept Offer'), function() {
						update_job_offer_from_applicant(frm, 'Accepted');
		      		},"Action").css("background-color", "red");
					frm.add_custom_button(__('Reject Offer'), function() {
						update_job_offer_from_applicant(frm, 'Rejected');
		      		},"Action").addClass('btn-danger');
				}
				frm.add_custom_button(__(''), function() {
				},'Action').css({"padding": "0.01rem", "background-color":"gray"});
			}

			if(frm.doc.one_fm_applicant_status != 'Selected' && frm.doc.status != 'Rejected'){
				frm.add_custom_button(__('Select Applicant'), function() {
					if(frm.doc.day_off_category && frm.doc.number_of_days_off && frm.doc.number_of_days_off > 0){
						change_applicant_status(frm, 'one_fm_applicant_status', 'Selected');
					}
					else{
						frappe.throw(__("Please Update Day off Details to Proceed !!"));
					}
				},"Action");
				frm.add_custom_button(__('Reject Applicant'), function() {
					if (frm.doc.__onload && frm.doc.__onload.job_offer) {
						update_job_offer_from_applicant(frm, 'Rejected');
					}
					else{
						change_applicant_status(frm, 'status', 'Rejected');
					}
				},'Action');
			}
			frm.add_custom_button(__(''), function() {
			},'Action').css({"padding": "0.01rem", "background-color":"gray"});
			if(frm.doc.one_fm_applicant_status != 'Selected' && frm.doc.status != 'Rejected'){
				if (frappe.user.has_role("Hiring Manager")){
					frm.add_custom_button(__('Change ERF'), function() {
						change_applicant_erf(frm);
					},"Action");
				}
			}
    // }
		// if ((!frm.doc.__islocal) && (frm.doc.status == 'Accepted')) {
// 			frappe.db.get_value("Employee", {"job_applicant": frm.doc.name}, "name", function(r) {
// 				if(!r || !r.name){
// 					frm.add_custom_button(__('Create Employee'),
// 						function () {
// 							frappe.model.open_mapped_doc({
// 								method: "one_fm.hiring.utils.make_employee",
// 								frm: frm
// 							});
// 						}
// 					);
// 				}
// 			});
				}

	},
	one_fm_change_pam_file_number: function(frm){
		// on the change of pam desigantion change the button color and set the flag value
		let msg = __('Do You Want to Change PAM File Number?')
		frappe.confirm(
			msg,
			function(){//yes
				document.querySelectorAll("[data-fieldname='one_fm_change_pam_file_number']")[1].style.backgroundColor ="#ec645e";
				frm.set_value('pam_number_button',1);


			},
			function(){//no

			}
		);
	},
	one_fm_change_pam_designation: function(frm){
		// on the change of pam desigantion change the button color and set the flag value
		let msg = __('Do You Want to Change PAM Desigantion?')
		frappe.confirm(
			msg,
			function(){//yes
				document.querySelectorAll("[data-fieldname='one_fm_change_pam_designation']")[1].style.backgroundColor ="#ec645e";
				frm.set_value('pam_designation_button',1);

			},
			function(){//no

			}
		);

	},
	one_fm_first_name: function(frm) {
    set_applicant_name(frm);
  },
	one_fm_second_name: function(frm) {
    set_applicant_name(frm);
  },
	one_fm_third_name: function(frm) {
    set_applicant_name(frm);
  },
  one_fm_forth_name: function(frm) {
    set_applicant_name(frm);
  },
	one_fm_last_name: function(frm) {
    set_applicant_name(frm);
  },
	job_title: function(frm) {
		set_job_opening_to_applicant(frm);
	},
	one_fm_erf: function(frm) {
		set_erf_to_applicant(frm);
	},
	one_fm_source_of_hire: function(frm) {
		set_have_visa_field_properties(frm);
		set_required_documents(frm);
		if(frm.doc.one_fm_source_of_hire == 'One FM'){
			frm.set_value('one_fm_agency', '');
			frm.set_value('one_fm_is_agency_applying', false);
		}
		set_field_properties_on_agency_applying(frm)
	},
	one_fm_visa_type: function(frm) {
		set_required_documents(frm);
	},
	one_fm_i_am_currently_working: function(frm) {
		set_mandatory_fields_for_current_employment(frm);
	},
	one_fm_gender: function(frm) {
		set_height_field_property_from_gender(frm);
	},
	one_fm_email_id: function(frm) {
		set_job_applicant_email_id(frm);
	},
	one_fm_have_a_valid_visa_in_kuwait: function(frm) {
		set_visa_type_field_properties(frm);
		set_cid_field_properties(frm);
		if(!frm.doc.one_fm_have_a_valid_visa_in_kuwait){
			frm.set_value('one_fm_in_kuwait_at_present', false);
		}
	},
	one_fm_agency: function(frm) {
		if(frm.doc.one_fm_agency){
			frm.set_value('one_fm_is_agency_applying', true);
		}
		else{
			frm.set_value('one_fm_is_agency_applying', false);
		}
	},
	one_fm_is_agency_applying: function(frm) {
		set_field_properties_on_agency_applying(frm);
	},
	one_fm_cid_number: function(frm) {
		validate_cid(frm);
	},
	one_fm_date_of_birth: function(frm) {
		validate_cid(frm);
		validate_min_age(frm);
	},
	one_fm_height: function(frm) {
		validate_height_range(frm);
	},
	one_fm_passport_issued: function(frm) {
		validate_passport_date(frm);
	},
	one_fm_passport_expire: function(frm) {
		validate_passport_date(frm);
	},
	one_fm_employment_start_date: function(frm) {
		validate_employment_date(frm);
	},
	one_fm_employment_end_date: function(frm) {
		validate_employment_date(frm);
	},
	one_fm_notice_period_in_days: function(frm) {
		if(frm.doc.one_fm_i_am_currently_working && (frm.doc.one_fm_notice_period_in_days > 120)){
			frm.set_value('one_fm_notice_period_in_days', '');
			frappe.throw(__("We are not looking for a Job Applicant having notice period greater than 120 Days"));
		}
	},
	one_fm_applicant_is_overseas_or_local: function(frm) {
		if(frm.doc.one_fm_applicant_is_overseas_or_local){
			let msg = __('Do You Need to Set the Value to {0}', [frm.doc.one_fm_applicant_is_overseas_or_local])
			frappe.confirm(
				msg,
				function(){}, // Yes
				function(){
					// No
					frm.set_value('one_fm_applicant_is_overseas_or_local', '');
				}
			);
			if(frm.doc.one_fm_applicant_is_overseas_or_local == 'Overseas'){
				frm.set_value('one_fm_is_transferable', '');
			}
		}
		else{
			frm.set_value('one_fm_is_transferable', '');
		}
	},
	one_fm_is_transferable: function(frm) {
		if(frm.doc.one_fm_is_transferable){
			let msg = __('Do You Need to Set the Value to {0}', [frm.doc.one_fm_is_transferable])

			frappe.confirm(
				msg,
				function(){
					// Yes

				},
				function(){
					// No
					frm.set_value('one_fm_is_transferable', '');
				}
			)
		}
	},
	one_fm_nationality: function(frm) {
		if(frm.doc.one_fm_nationality && !frm.doc.one_fm_passport_holder_of || !frm.doc.one_fm_country_of_overseas){
			frappe.db.get_value('Nationality', frm.doc.one_fm_nationality, 'country', function(r) {
				if(r.country){
					if(!frm.doc.one_fm_passport_holder_of){
						frm.set_value('one_fm_passport_holder_of', r.country);
					}
					if(!frm.doc.one_fm_country_of_overseas){
						frm.set_value('one_fm_country_of_overseas', r.country);
					}
				}
			});
		}
	},
	one_fm_applicant_status: function(frm){
		if(frm.doc.one_fm_applicant_status != "Selected"){
			let hide_fields=['section_break_66'];
			set_hidden_fields(frm, hide_fields, true);
		}
	},
	save_me: function(frm){
		frm.save();
		if(frm.doc.accept_changes == 1 && frm.doc.reject_changes ==0){
			let msg = __('Notification Will Sent to Operator to Proceed, No internal issues.');
			frappe.confirm(msg,
				function(){//yes
						frappe.call({
							method: "one_fm.one_fm.utils.notify_operator_with_supervisor_response",
							args: {
								'name': frm.doc.name,
							}
						});
					},
				function(){}//No
			);
		}if(frm.doc.reject_changes == 1 && frm.doc.accept_changes ==0){
			let msg = __('Notification Will Sent to Operator to Review Your Suggested Changes.');
			frappe.confirm(msg,
				function(){//yes
						frappe.call({
							method: "one_fm.one_fm.utils.notify_operator_with_supervisor_response",
							args: {
								'name': frm.doc.name,
							}
							});
						},
				function(){}
			);
		}
	},
	accept_changes: function(frm){

		if(frm.doc.accept_changes == 1 && frm.doc.reject_changes == 0){
			let msg = __('Do You Want to Accept Changes Done By Operator?')
			frappe.confirm(
				msg,
				function(){
					// Yes

				},
				function(){
					// No

				}
			);
		}if(frm.doc.accept_changes == 1 && frm.doc.reject_changes == 1){
			frm.set_value('reject_changes', 0);
			let msg = __('Do You Want to Accept Changes Done By Operator?')
			frappe.confirm(
				msg,
				function(){
					// Yes


				},
				function(){
					// No

				}
			);
		}
	},
	reject_changes: function(frm){

		if(frm.doc.reject_changes == 1 && frm.doc.accept_changes == 0){
			let msg = __('Do You Want to Reject Changes Done By Operator?')
			frappe.confirm(
				msg,
				function(){
					// Yes

					//once the changes for pam number and pam desigantion is rejected the data will be stored in a hidden fields as referance
					if(frm.doc.one_fm_pam_designation){
						frm.set_value('one_fm_old_designation', frm.doc.one_fm_pam_designation);
					}
					if(frm.doc.one_fm_pam_designation){
						frm.set_value('one_fm_old_number', frm.doc.one_fm_file_number);
					}

				},
				function(){
					// No

				}
			);
		}if(frm.doc.reject_changes == 1 && frm.doc.accept_changes == 1){
			frm.set_value('accept_changes', 0);
			let msg = __('Do You Want to Reject Changes Done By Operator?')
			frappe.confirm(
				msg,
				function(){
					// Yes

					//once the changes for pam number and pam desigantion is rejected the data will be stored in a hidden fields as referance
					if(frm.doc.one_fm_pam_designation){
						frm.set_value('one_fm_old_designation', frm.doc.one_fm_pam_designation);
					}
					if(frm.doc.one_fm_pam_designation){
						frm.set_value('one_fm_old_number', frm.doc.one_fm_file_number);
					}

				},
				function(){
					// No

				}
			);
		}
	},
	one_fm_has_issue: function(frm){
		if(frm.doc.one_fm_has_issue && frappe.user.has_role("GRD Operator")){
		// check the Authorized signatory based on file number
			if((frm.doc.pam_number_button == 1) && (frm.doc.one_fm_pam_file_number)){
				// if PAM file Number has changes in job applicant, set the signatory names of the new file
				frappe.call({
					method: "one_fm.one_fm.utils.get_signatory_name",
					args:{
						'parent': frm.doc.one_fm_pam_file_number,
						'name': frm.doc.name,
						},
					callback:function(r){

						frm.set_df_property('one_fm_signatory_name', "options", r.message[0]);
						frm.set_value('one_fm_pam_authorized_signatory',r.message[1]);
						frm.refresh_field("one_fm_pam_authorized_signatory");
						frm.refresh_field("one_fm_signatory_name");
						}
					});
					frm.refresh_field("one_fm_pam_authorized_signatory");
					frm.refresh_field("one_fm_signatory_name");

			}
			if((frm.doc.pam_number_button == 0) && (frm.doc.one_fm_erf_pam_file_number)){
				// if PAM file Number has changes in job applicant, set the signatory names of the old file in erf
				frappe.call({
					method: "one_fm.one_fm.utils.get_signatory_name_erf_file",
					args:{
						'parent': frm.doc.one_fm_erf_pam_file_number,
						'name': frm.doc.name,
						},
					callback:function(r){
						frm.set_df_property('one_fm_signatory_name', "options", r.message[0]);
						frm.set_value('one_fm_pam_authorized_signatory',r.message[1]);
						frm.refresh_field("one_fm_pam_authorized_signatory");
						frm.refresh_field("one_fm_signatory_name");
						}
					});
					frm.refresh_field("one_fm_pam_authorized_signatory");
					frm.refresh_field("one_fm_signatory_name");

			}
		}
	},
	send_changes_to_supervisor: function(frm){
		frm.save();

		let msg = __('Do You Want to Notify GRD Supervisor With Your Changes?')
		frappe.confirm(
			msg,
			function(){//yes

				if(frm.doc.pam_designation_button ==1 && frm.doc.pam_number_button == 0){
					if(frm.doc.one_fm_old_designation != frm.doc.one_fm_pam_designation){
					frappe.call({
						method: "one_fm.one_fm.utils.notify_supervisor_change_pam_designation",
						args: {
							'name': frm.doc.name,
						}
						});
					}
					else{
						frappe.msgprint(__('No Changes In Designation.'));
					}
				}if(frm.doc.pam_number_button ==1 && frm.doc.pam_designation_button == 0){
					if(frm.doc.one_fm_old_number != frm.doc.one_fm_file_number){
					frappe.call({
						method: "one_fm.one_fm.utils.notify_supervisor_change_file_number",
						args: {
							'name': frm.doc.name,
						}
						});
					}else{
						frappe.msgprint(__('No Changes In PAM File Number.'));
					}

				}if(frm.doc.pam_number_button ==1 && frm.doc.pam_designation_button == 1){
					if((frm.doc.one_fm_old_number != frm.doc.one_fm_file_number) &&
					(frm.doc.one_fm_old_designation != frm.doc.one_fm_pam_designation)){
						frappe.call({
							method: "one_fm.one_fm.utils.notify_supervisor_change_file_number",
							args: {
								'name': frm.doc.name,
							}
						});
						frappe.call({
							method: "one_fm.one_fm.utils.notify_supervisor_change_pam_designation",
							args: {
								'name': frm.doc.name,
							}
						});
					}else if((frm.doc.one_fm_old_number != frm.doc.one_fm_file_number) &&
					(frm.doc.one_fm_old_designation == frm.doc.one_fm_pam_designation)){
						frappe.call({
							method: "one_fm.one_fm.utils.notify_supervisor_change_file_number",
							args: {
								'name': frm.doc.name,
							}
						});
					}else if((frm.doc.one_fm_old_number == frm.doc.one_fm_file_number) &&
					(frm.doc.one_fm_old_designation != frm.doc.one_fm_pam_designation)){
						frappe.call({
							method: "one_fm.one_fm.utils.notify_supervisor_change_pam_designation",
							args: {
								'name': frm.doc.name,
							}
						});
					}else{
						frappe.msgprint(__('No Changes In PAM File Number.'));
					}
				}

		},function(){
			// No

			}
		);

	}

});

var set_grd_field_properties = function(frm){
	// Hide GRD section if transferable not selected yet
	let hide_fields=['authorized_signatory','previous_company_details','authorized_signatory_section',
	'one_fm_has_issue','one_fm_type_of_issues','one_fm_pam_file_number','one_fm_pam_designation',
	'one_fm_previous_company_trade_name_in_arabic','one_fm__previous_company_authorized_signatory_name_arabic',
	'one_fm_previous_company_issuer_number','one_fm_government_project','one_fm_file_number','one_fm_change_pam_designation',
	'one_fm_change_pam_file_number','no_internal_issues','save_me','suggestions','one_fm_erf_pam_file_number','one_fm_erf_pam_designation','send_changes_to_supervisor',
	'accept_changes','reject_changes','one_fm_previous_company_pam_file_number','one_fm_signatory_name'];

	if(!frm.doc.one_fm_is_transferable || frm.doc.one_fm_is_transferable == 'Later'
	 || frm.doc.one_fm_is_transferable == 'No'){
		set_hidden_fields(frm, hide_fields, true);
	 }

	 // Hide irrelevant sections for GRD Operator and set read only option to the required fields
	 if(frm.doc.one_fm_is_transferable == "Yes" && frappe.user.has_role("GRD Operator")){
		let hide_fields=['one_fm_basic_skill_section','one_fm_uniform_measurements',
		'one_fm_work_details_section','section_break_6','section_break_88',
		'one_fm_educational_qualification_section','one_fm_current_employment_section_',
		'country_and_nationality_section','one_fm_language_section','one_fm_contact_details_section',
		'previous_work_details','one_fm_erf_application_details_section','one_fm_interview_and_career_history_score',
		'one_fm_interview_schedules_section'];

		let read_fields=['one_fm_in_kuwait_at_present','one_fm_cid_expire','one_fm_visa_type','one_fm_have_a_valid_visa_in_kuwait','one_fm_passport_type','one_fm_passport_expire','one_fm_passport_issued','one_fm_passport_holder_of','one_fm_place_of_birth','one_fm_height','one_fm_last_name_in_arabic','one_fm_forth_name_in_arabic','one_fm_third_name_in_arabic','one_fm_second_name_in_arabic','one_fm_first_name_in_arabic','one_fm_last_name','one_fm_forth_name','one_fm_third_name','one_fm_second_name','one_fm_first_name','source','job_title','one_fm_applicant_status','status','one_fm_application_id','email_id','applicant_name','one_fm_is_transferable','one_fm_applicant_is_overseas_or_local','one_fm_cid_number',
		'one_fm_duration_of_work_permit','one_fm_previous_designation','one_fm_work_permit_salary','one_fm_date_of_birth',
		'one_fm_nationality','one_fm_marital_status','one_fm_educational_qualification','one_fm_passport_number',
		'one_fm_gender','one_fm_religion'];

		set_read_only_fields(frm, read_fields, true);
		set_hidden_fields(frm, hide_fields, true);


	}

	//field only for grd supervisor
	if(frappe.user.has_role("GRD Operator")){
		let hide_fields=['save_me']
		set_hidden_fields(frm, hide_fields, true);
	}//field only for grd operator
	if(frappe.user.has_role("GRD Supervisor")){
		let hide_fields=['send_changes_to_supervisor']
		set_hidden_fields(frm, hide_fields, true);
	}//if not set by grd supervisor hide them
	if(!frappe.user.has_role("GRD Supervisor") && (!frm.doc.accept_changes || !frm.doc.reject_changes)){
		let hide_fields=['accept_changes','reject_changes']
		set_hidden_fields(frm, hide_fields, true);
	}
	//show the field for operator only
	if(!frappe.user.has_role("GRD Operator")){
		let hide_fields=['no_internal_issues']
		set_hidden_fields(frm, hide_fields, true);
	}
	//activate no internal issue checkbox
	if(frappe.user.has_role("GRD Supervisor") || frappe.user.has_role("GRD Operator")){
		if(frm.doc.reject_changes && ((frm.doc.pam_designation_button == 1) || (doc.pam_number_button ==1))){
			let hide_fields=['no_internal_issues']
			set_hidden_fields(frm, hide_fields, true);
		}
	}
	//Set GRD section as read only for recruiter role
	if(frm.doc.one_fm_has_issue && frappe.user.has_role("Senior Recruiter")||frappe.user.has_role("Recruiter")){
		let read_fields=['authorized_signatory','previous_company_details','authorized_signatory_section',
		'one_fm_has_issue','one_fm_type_of_issues','one_fm_pam_file_number','one_fm_pam_designation',
		'one_fm_previous_company_trade_name_in_arabic','one_fm__previous_company_authorized_signatory_name_arabic',
		'one_fm_previous_company_issuer_number','one_fm_government_project','one_fm_file_number','one_fm_change_pam_designation',
		'one_fm_change_pam_file_number','no_internal_issues','save_me','suggestions','one_fm_erf_pam_file_number','one_fm_erf_pam_designation','send_changes_to_supervisor',
		'accept_changes','reject_changes','one_fm_previous_company_pam_file_number','one_fm_signatory_name'];
		set_read_only_fields(frm, read_fields, true);
	}

};

var change_applicant_erf = function(frm) {
	var dialog = new frappe.ui.Dialog({
		title: 'Change ERF',
		fields: [
			{fieldtype: "Link", options: 'ERF', label: "New ERF", fieldname: "erf", reqd: true}
		],
		primary_action_label: __("Change ERF"),
		primary_action : function(){
			frappe.confirm(
				__('Are you sure to change ERF for the Job Applicant?'),
				function(){
					// Yes
					frm.set_value('one_fm_erf', dialog.get_value('erf'));
					dialog.hide();
				},
				function(){
					// No
					dialog.hide();
				}
			);
		}
	});
	dialog.show();
};

var change_applicant_status = function(frm, status_field, status) {
	let msg = __('Do you really want to make {0} the applicant?', [status])
	frappe.confirm(
		msg,
		function(){
			// Yes
			frm.set_value(status_field, status);
			frm.save();
		},
		function(){
			// No
		}
	);
};

var update_job_offer_from_applicant = function(frm, status) {
	let msg = __('Job Offer {0} ?', [status])
	frappe.confirm(
		msg,
		function(){
			// Yes
			frappe.call({
				method: 'one_fm.hiring.utils.update_job_offer_from_applicant',
				args: {'jo': frm.doc.__onload.job_offer, 'status': status},
				callback: function(r) {
					if(!r.exc){
						frm.reload_doc();
					}
				},
				freeze: true,
				freeze_message: __("Updating .....")
			});
		},
		function(){
			// No
		}
	);
};

frappe.ui.form.on('Job Applicant Required Document', {
	attach: function(frm, cdt, cdn){
    var child = locals[cdt][cdn];
		if(child.attach){
			frappe.model.set_value(child.doctype, child.name, 'received', true);
		}
		else{
			frappe.model.set_value(child.doctype, child.name, 'received', false);
		}
  },
	received: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(child.received && !child.attach){
			frappe.model.set_value(child.doctype, child.name, 'received', false);
			frappe.throw(__("Can not marked as received without attachment."));
		}
	}
});

frappe.ui.form.on('Job Applicant Interview Schedule', {
	action: function(frm, cdt, cdn) {
		if(frm.is_dirty()){
			frappe.msgprint(__('Please Save the Document for Further Action'));
		}
		else{
			var child = locals[cdt][cdn];
			frappe.route_options = {
				"job_applicant": frm.doc.name,
				"interview_type": child.interview_type,
				"interview_scheduled_date": child.scheduled_on,
				"interview_schedule": child.name
			};
			frappe.new_doc("Interview Result");
		}
	}
});

var validate_employment_date = function(frm) {
	if(frm.doc.one_fm_i_am_currently_working && (frm.doc.one_fm_employment_end_date < frm.doc.one_fm_employment_start_date)){
		frm.set_value('one_fm_employment_start_date', '');
		frappe.throw(__("Employment End Date cannot be before Employment Start Date"));
	}
};

var validate_passport_date = function(frm) {
	if(frm.doc.one_fm_passport_expire < frm.doc.one_fm_passport_issued){
		frm.set_value('one_fm_passport_expire', '');
		frappe.throw(__("Passport Expires on Date cannot be before Passport Issued on Date"));
	}
};

var validate_height_range = function(frm) {
	if(frm.doc.one_fm_height && frm.doc.one_fm_height <= 10){
		frm.set_value('one_fm_height', '');
		frappe.throw(__('Hieght Must be greter than 10cm.'));
	}
};

var validate_min_age = function(frm) {
	var minimum_age_required = 18;
	if(frm.doc.one_fm_erf && frm.doc.one_fm_gender){
		frappe.call({
			method: 'frappe.client.get',
			args: {doctype: 'ERF', filters:{name: frm.doc.one_fm_erf}},
			callback: function(r) {
				if(r& r.message && r.message.gender_height_requirement){
					var items = r.message.gender_height_requirement;
					items.forEach((item, i) => {
						if(item.gender == frm.doc.one_fm_gender && item.minimum_age > 0){
							minimum_age_required = minimum_age;
						}
					});
					validate_date_of_birth(frm, minimum_age_required);
				}
			}
		})
	}
	else{
		validate_date_of_birth(frm, minimum_age_required);
	}
};

var create_interview = function(frm) {
	frappe.new_doc("Interview Result", {"job_applicant": frm.doc.name});
};

var view_interview = function(frm) {
	frappe.route_options = {"job_applicant": frm.doc.name};
	frappe.set_route("List", "Interview Result");
};

var create_career_history = function(frm) {
	frappe.new_doc("Career History", {"job_applicant":frm.doc.name});
};

var send_magic_link = function(frm, method) {
	frappe.call({
		method: method,
		args: {'job_applicant': frm.doc.name},
		callback: function(r) {
			if(r && r.message){
				frappe.msgprint(__("Succesfully Send the Magic Link"));
			}
		},
		freeze: true,
		freeze_message: __("Sending the magic link ..!")
	});
};

var view_best_reference = function(frm) {
  frappe.route_options = {"job_applicant": frm.doc.name};
	frappe.set_route("List", "Best Reference");
};

var view_career_history = function(frm) {
	frappe.route_options = {"job_applicant": frm.doc.name};
	frappe.set_route("List", "Career History");
};

var validate_date_of_birth = function(frm, minimum_age_required) {
	if(frm.doc.one_fm_date_of_birth){
		let today = frappe.datetime.get_today()
		// Add minimum_age_required*12 Months to DOB to get date after 15 years
		let dob_present = frappe.datetime.add_months(frm.doc.one_fm_date_of_birth, minimum_age_required*12)
		// If today >= dob_present, then age is more than minimum_age_required years
		if(today < dob_present){
			frm.set_value('one_fm_date_of_birth', '');
			if(minimum_age_required == 18){
				frappe.throw(__("We Love to Work With Young Geniuses, Its Not Legal Though."));
			}
			else{
				frappe.throw(__("Minimum Age Should be {0} Years", [minimum_age_required]));
			}
		}
	}
};

var validate_cid = function(frm) {
	if(frm.doc.one_fm_cid_number){
		var valid_cid = true;
		if (frm.doc.one_fm_cid_number.length > 12){
			frappe.throw(__("Civil ID should be 12 Digit.!"));
		}
		else if (frm.doc.one_fm_cid_number.length == 12 && !isNumeric(frm.doc.one_fm_cid_number)){
			frappe.throw(__("Civil ID should be Numeric.!"));
		}
		else if (frm.doc.one_fm_cid_number.length == 12 && frm.doc.one_fm_date_of_birth){
			var date_string = is_dob_include_in_cid(frm.doc.one_fm_cid_number, frm.doc.one_fm_date_of_birth)
			if(!frm.doc.one_fm_cid_number.includes(date_string)){
				frappe.throw(__("Civil ID should includes Date of Birth in the format " + date_string + " .!"));
			}
		}
	}
	function isNumeric(num){
	  return !isNaN(num)
	}
};

var is_dob_include_in_cid = function(cid, dob) {
	let	date_ms = Date.parse(dob);
	let	date_obj = new Date();
	date_obj.setTime(date_ms);
	let	year = date_obj.getFullYear();
	let month = date_obj.getMonth()+1;
	let day = date_obj.getDate();
	if(month < 10){
		month = '0'+month.toString();
	}
	else{
		month = month.toString();
	}
	if(day < 10){
		day = '0'+day.toString();
	}
	else{
		day = day.toString();
	}
	year = year.toString().slice(-2);
	let date_string = year+month+day;
	return date_string;
};

var set_field_properties_on_agency_applying = function(frm) {
	// On Contact Section
	let fields = ['one_fm_contact_number'];
	let hide_fields = ['one_fm_contact_number', 'one_fm_secondary_contact_number', 'one_fm_country_code', 'one_fm_country_code_second'];
	if(frm.doc.one_fm_agency && frm.doc.one_fm_is_agency_applying){
		set_mandatory_fields(frm, fields, false);
		set_hidden_fields(frm, hide_fields, true);
		// frm.set_df_property('one_fm_contact_details_section', 'hidden', true);
	}
	else{
		set_hidden_fields(frm, hide_fields, false);
		// frm.set_df_property('one_fm_contact_details_section', 'hidden', false);
		set_mandatory_fields(frm, fields, true);
	}

	// On Work Details Section
	if(frm.doc.one_fm_is_agency_applying){
		frm.set_df_property('one_fm_work_details_section', 'hidden', true);
		let fields = ['one_fm_rotation_shift', 'one_fm_night_shift', 'one_fm_type_of_travel', 'one_fm_type_of_driving_license'];
		set_mandatory_fields(frm, fields, false);
	}
	else{
		if(frm.doc.one_fm_erf){
			frappe.call({
				method: 'frappe.client.get',
				args: {doctype: 'ERF', filters:{name: frm.doc.one_fm_erf}},
				callback: function(r) {
					if(r.message){
						var erf = r.message;
						set_work_details_section(frm, erf);
					}
				}
			});
		}
	}
};

var set_cid_field_properties = function(frm) {
	if(frm.doc.one_fm_have_a_valid_visa_in_kuwait){
		frm.set_df_property('one_fm_cid_number', 'reqd', true);
		frm.set_df_property('one_fm_cid_expire', 'reqd', true);
	}
	else{
		frm.set_df_property('one_fm_cid_number', 'reqd', false);
		frm.set_df_property('one_fm_cid_expire', 'reqd', false);
	}
};

var set_have_visa_field_properties = function(frm) {
	if(frm.doc.one_fm_source_of_hire == 'Local'){
		frm.set_value('one_fm_have_a_valid_visa_in_kuwait', true);
	}
};

var set_visa_type_field_properties = function(frm) {
	if(frm.doc.one_fm_have_a_valid_visa_in_kuwait){
		frm.set_df_property('one_fm_visa_type', 'reqd', true);
	}
	else{
		frm.set_df_property('one_fm_visa_type', 'reqd', false);
	}
};

var set_job_applicant_email_id = function(frm) {
	if(frm.doc.one_fm_email_id){
		frm.set_value('email_id', frm.doc.one_fm_email_id);
	}
	else{
		frm.set_value('email_id', '');
	}
};

var set_height_field_property_from_gender = function(frm) {
	if(frm.doc.one_fm_erf && frm.doc.one_fm_gender){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'ERF',
				filters: {name: frm.doc.one_fm_erf}
			},
			callback: function(r){
				let show_height_field = false;
				let mandatory_height_field = false;
				if(r.message && r.message.gender_height_requirement){
					let height_details = r.message.gender_height_requirement;
					height_details.forEach((item) => {
						if(item.gender == frm.doc.one_fm_gender && item.height > 0){
							show_height_field = true;
							if(item.is_height_mandatory){
								mandatory_height_field = true;
							}
						}
					});
				}
				frm.set_df_property('one_fm_height', 'hidden', show_height_field?false:true);
				frm.set_df_property('one_fm_height', 'reqd', mandatory_height_field?true:false);
			}
		});
	}
	else{
		frm.set_df_property('one_fm_height', 'hidden', true);
		frm.set_df_property('one_fm_height', 'reqd', false);
	}
};

var set_mandatory_fields_for_current_employment = function(frm) {
	let fields = ['one_fm_current_employer', 'one_fm_employment_start_date', 'one_fm_employment_end_date',
		'one_fm_current_job_title', 'one_fm_country_of_employment', 'one_fm_notice_period_in_days', 'one_fm_current_salary'];
	if(frm.doc.one_fm_i_am_currently_working){
		set_mandatory_fields(frm, fields, true);
	}
	else{
		set_mandatory_fields(frm, fields, false);
	}
};

var set_mandatory_fields = function(frm, fields, reqd) {
	fields.forEach((field) => {
		frm.set_df_property(field, 'reqd', reqd);
	});
};

var set_read_only_fields_of_job_applicant = function(frm) {
	let fields = ['status', 'one_fm_applicant_status', 'one_fm_application_id', 'job_title'];
	set_read_only_fields(frm, fields, true);
};

var set_read_only_fields = function(frm, fields, read_only) {
	fields.forEach((field) => {
		frm.set_df_property(field, 'read_only', read_only);
	});
};

var set_mandatory_fields_of_job_applicant = function(frm) {
	let fields = ['one_fm_last_name', 'one_fm_first_name', 'one_fm_passport_number', 'one_fm_place_of_birth', 'one_fm_email_id',
		'one_fm_marital_status', 'one_fm_passport_holder_of', 'one_fm_passport_issued', 'one_fm_passport_expire',
		'one_fm_gender', 'one_fm_religion', 'one_fm_date_of_birth', 'one_fm_educational_qualification', 'one_fm_university'];
	set_mandatory_fields(frm, fields, true);
};

var set_country_field_empty_on_load = function(frm) {
	let fields = ['one_fm_passport_holder_of', 'one_fm_country_of_employment'];
	if(frm.doc.__islocal){
		fields.forEach((field) => {
			frm.set_value(field, '');
		});
	}
};

var hide_job_applicant_existing_fields = function(frm) {
	let fields = ['applicant_name', 'email_id', 'cover_letter', 'resume_attachment', 'section_break_6', 'one_fm_height','one_fm_applicant_civil_id','one_fm_passport_applicant_number','one_fm_previous_company_authorized_signatory','Resume Link'];
	set_hidden_fields(frm, fields, true);
};

var set_hidden_fields = function(frm, fields, hidden) {
	fields.forEach((field) => {
		frm.set_df_property(field, 'hidden', hidden);
	});
};

var set_required_documents = function(frm) {
	frm.clear_table('one_fm_documents_required');
	let filters = {};
	if(frm.doc.one_fm_source_of_hire){
    let source_of_hire = 'Overseas';
    if(frm.doc.one_fm_source_of_hire == 'Local'){
			source_of_hire = 'Local';
		}
    else if(frm.doc.one_fm_source_of_hire == 'Local and Overseas' && frm.doc.one_fm_have_a_valid_visa_in_kuwait && frm.doc.one_fm_visa_type){
			source_of_hire = 'Local';
		}
    filters['source_of_hire'] = source_of_hire;
    if (source_of_hire == 'Local' && frm.doc.one_fm_visa_type){
			filters['visa_type'] = frm.doc.one_fm_visa_type;
		}
    else{
			filters['visa_type'] = '';
		}

		frappe.call({
			method: 'one_fm.one_fm.doctype.recruitment_document_checklist.recruitment_document_checklist.get_recruitment_document_checklist',
			args: {filters: filters},
			callback: function(r) {
				frm.clear_table('one_fm_documents_required');
				if(r.message && r.message.recruitment_documents){
					var document_checklist = r.message.recruitment_documents;
					document_checklist.forEach((checklist) => {
						let doc_required = frappe.model.add_child(frm.doc, 'Job Applicant Required Document', 'one_fm_documents_required');
						let fields = ['document_required', 'required_when', 'or_required_when', 'type_of_copy', 'or_type_of_copy',
							'not_mandatory']
						fields.forEach((field) => {
							frappe.model.set_value(doc_required.doctype, doc_required.name, field, checklist[field]);
						});
					});
				}
				frm.refresh_field('one_fm_documents_required');
			}
		});
	}
	frm.refresh_field('one_fm_documents_required');
};

var set_erf_to_applicant = function(frm) {
	if(frm.doc.one_fm_erf){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'ERF',
				filters: {'name': frm.doc.one_fm_erf}
			},
			callback: function(r) {
				if(r.message){
					var erf = r.message;
					set_pam_file_number_and_designation(frm,erf);
					set_uniform_fields(frm, erf);
					set_job_opening_form_erf(frm, erf);
					set_erf_basic_details(frm, erf);
					set_work_details_section(frm, erf);
					validate_date_of_birth(frm, erf.minimum_age_required);
				}
			}
		});
	}
};

var set_pam_file_number_and_designation = function(frm, erf){
	//fetching the pam file number and pam designation that will be set in the erf
	frm.set_value('one_fm_erf_pam_file_number',erf.pam_file_number);
	frm.set_value('one_fm_erf_pam_designation',erf.pam_designation);

};

var set_uniform_fields = function(frm, erf) {
	frm.set_value('one_fm_is_uniform_needed_for_this_job', erf.is_uniform_needed_for_this_job);
};

var set_job_opening_form_erf = function(frm, erf) {
	if(!frm.doc.job_title){
		frappe.call({
			method: 'frappe.client.get_value',
			args: {
				doctype: 'Job Opening',
				fieldname: 'name',
				filters: {one_fm_erf: erf.name}
			},
			callback: function(r) {
				if(r.message && r.message.name && !frm.doc.job_title){
					frm.set_value('job_title', r.message.name)
				}
			}
		});
	}
};

var set_work_details_section = function(frm, erf) {
	if(!frm.doc.one_fm_is_agency_applying){
		frm.set_df_property('one_fm_work_details_section', 'hidden', false);
		frm.set_df_property('one_fm_rotation_shift', 'reqd', erf.shift_working);
		frm.set_df_property('one_fm_rotation_shift', 'hidden', !erf.shift_working);
		frm.set_df_property('one_fm_night_shift', 'reqd', erf.night_shift);
		frm.set_df_property('one_fm_night_shift', 'hidden', !erf.night_shift);
		frm.set_df_property('one_fm_type_of_travel', 'reqd', erf.travel_required);
		frm.set_df_property('one_fm_type_of_travel', 'hidden', !erf.travel_required);
		if(erf.travel_required && erf.type_of_travel){
			let options = ['I Will Travel '+erf.type_of_travel, 'I Cant Travel '+erf.type_of_travel];
			frm.set_df_property('one_fm_type_of_travel', 'options', options)
		}
		frm.set_df_property('one_fm_type_of_driving_license', 'reqd', erf.driving_license_required);
		frm.set_df_property('one_fm_type_of_driving_license', 'hidden', !erf.driving_license_required);
	}
};

var set_erf_basic_details = function(frm, erf) {
	frm.set_value('one_fm_hiring_method', erf.hiring_method);
	if(erf.working_days && erf.off_days && erf.off_days > 0){
		frm.set_value('day_off_category', 'Monthly');
		frm.set_value('number_of_days_off', erf.off_days);
	}
};

var set_job_opening_to_applicant = function(frm) {
	if(frm.doc.job_title){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Job Opening',
				filters: {'name': frm.doc.job_title}
			},
			callback: function(r) {
				if(r.message){
					var job = r.message;
					frm.set_df_property('one_fm_erf', 'read_only', true);
					var fields = ['one_fm_erf', 'one_fm_source_of_hire', 'one_fm_sourcing_team']
					fields.forEach((field) => {
						frm.set_value(field, job[field]?job[field]:'');
					});
					set_job_basic_skill(frm, job);
					set_job_languages(frm, job);
				}
			}
		});
	}
};

var set_job_languages = function(frm, job) {
	if(job.one_fm_languages && job.one_fm_languages.length > 0){
		set_languages(frm, job.one_fm_languages);
	}
	else if(frm.doc.one_fm_erf) {
		frappe.call({
			method: 'frappe.client.get',
			args: {doctype: 'ERF', filters: {name:frm.doc.one_fm_erf}},
			callback: function(r) {
				if(r.message && r.message.languages){
					set_languages(frm, r.message.languages);
				}
			}
		});
	}
};

var set_languages = function(frm, languages) {
	// frappe.meta.get_docfield("Employee Language Requirement", 'language', frm.doc.name).read_only = 1;
	languages.forEach(function(language) {
		let lang = frappe.model.add_child(frm.doc, 'Employee Language Requirement', 'one_fm_languages');
		frappe.model.set_value(lang.doctype, lang.name, 'language', language.language);
		frappe.model.set_value(lang.doctype, lang.name, 'language_name', language.language_name);
	});
	frm.refresh_field('one_fm_languages');
};

var set_job_basic_skill = function(frm, job) {
	if(job.one_fm_designation_skill && job.one_fm_designation_skill.length > 0){
		set_designation_skill(frm, job.one_fm_designation_skill);
	}
	else if(frm.doc.one_fm_erf) {
		frappe.call({
			method: 'frappe.client.get',
			args: {doctype: 'ERF', filters: {name:frm.doc.one_fm_erf}},
			callback: function(r) {
				if(r.message && r.message.designation_skill){
					set_designation_skill(frm, r.message.designation_skill);
				}
			}
		});
	}
};

var set_designation_skill = function(frm, skills) {
	// frappe.meta.get_docfield("Designation Skill", 'skill', frm.doc.name).read_only = 1;
	skills.forEach(function(designation_skill) {
		let skill = frappe.model.add_child(frm.doc, 'Designation Skill', 'one_fm_designation_skill');
		frappe.model.set_value(skill.doctype, skill.name, 'skill', designation_skill.skill);
	});
	frm.refresh_field('one_fm_designation_skill');
};

var set_applicant_name = function(frm) {
  let name_fields = ['one_fm_second_name', 'one_fm_third_name','one_fm_forth_name', 'one_fm_last_name']
  let applicant_name = frm.doc.one_fm_first_name ?frm.doc.one_fm_first_name:'';
  name_fields.forEach((name_field) => {
    if(frm.doc[name_field]){
      applicant_name += ' '+frm.doc[name_field]
    }
  });
  frm.set_value('applicant_name', applicant_name);
};
