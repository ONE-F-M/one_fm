// Copyright (c) 2020, one fm and contributors
// For license information, please see license.txt

frappe.ui.form.on('ERF', {
	refresh: function(frm) {
		if(frm.is_new()){
			frm.set_value('erf_requested_by', frappe.session.user);
		}
		if(frm.doc.docstatus==0){
			frm.set_intro(__("All fields are Mandatory."), 'yellow');
		}
		else{
			frm.set_intro(__(""));
		}
		frm.set_query('project', function () {
			return {
				filters: {
					'project_type': 'External'
				}
			};
		});
		set_shift_working_btn(frm);
		set_driving_license_required_btn(frm);
		set_is_uniform_needed_for_this_job_btn(frm);
		set_is_id_card_needed_for_employee_btn(frm);
		set_provide_health_insurance_btn(frm);
		set_provide_mobile_with_line_btn(frm);
		// set_provide_company_insurance_btn(frm);
		set_provide_salary_advance_btn(frm);
		set_provide_accommodation_by_company_btn(frm);
		set_provide_transportation_by_company_btn(frm);
		set_provide_vehicle_by_company_btn(frm);
		set_provide_laptop_by_company_btn(frm);
		set_email_access_needed_btn(frm);
		set_type_of_license_btn(frm);
		set_night_shift_btn(frm);
		set_shift_hours_btn(frm);
		set_travel_required_btn(frm);
		set_open_to_different_btn(frm);
		document.querySelectorAll('[data-fieldname = "okr_workshop_submit_to_hr"]')[1].classList.add('btn-primary');
		set_performance_profile_resource_btn(frm);
		if(frm.doc.__onload && 'okr_workshop_with_full_name' in frm.doc.__onload){
			frm.set_df_property('schedule_for_okr_workshop_with_recruiter', 'label',
				__('Set a Date With {0} For a Quick Workshop',[frm.doc.__onload.okr_workshop_with_full_name]))
		}
		if (frm.doc.docstatus == 1 && frm.doc.__onload && 'erf_approver' in frm.doc.__onload){
			if(frappe.session.user==frm.doc.__onload.erf_approver && frm.doc.status == "Draft"){
				frm.add_custom_button(__('Accept'), () => frm.events.confirm_accept_decline_erf(frm, 'Accepted', false)).addClass('btn-primary');
				frm.add_custom_button(__('Decline'), () => frm.events.decline_erf(frm, 'Declined')).addClass('btn-danger');
			}
		}
		if (frm.doc.docstatus == 1 && frm.doc.status == "Accepted"){
			if(frappe.session.user==frm.doc.erf_requested_by || frappe.session.user==frm.doc.recruiter_assigned || frappe.session.user==frm.doc.secondary_recruiter_assigned){
				frm.add_custom_button(__('Close ERF'), () => frm.events.close_erf(frm)).addClass('btn-primary');
			}
		}
		if (!frm.is_new() && frm.doc.docstatus == 0 && !frm.doc.draft_erf_to_hrm){
			frm.add_custom_button(__('Submit to HR'), () => frm.events.draft_erf_to_hrm(frm)).addClass('btn-primary');

		}
	},
	decline_erf: function(frm, status) {
		var d = new frappe.ui.Dialog({
			title : __("Decline ERF"),
			fields : [{
				fieldtype: "Small Text",
				label: "Reason for Decline",
				fieldname: "reason_for_decline",
				reqd : 1
			}],
			primary_action_label: __("Decline"),
			primary_action: function(){
				frm.events.confirm_accept_decline_erf(frm, status, d.get_value('reason_for_decline'));
				d.hide();
			},
		});
		d.show();
	},
	close_erf: function(frm) {
		if(frm.doc.erf_employee && frm.doc.erf_employee.length > 0){
			var msg = __("Do You Want to Close this ERF?<br>Candidates Required: {0}\
				<br>Employee Selected/Joined: {1}", [frm.doc.number_of_candidates_required, frm.doc.erf_employee.length])
			frappe.confirm(
				msg,
				function(){
					// Yes
					frappe.call({
						doc: frm.doc,
						method: 'accept_or_decline',
						args: {status: 'Closed'},
						callback(r) {
							if (!r.exc) {
								frm.reload_doc();
							}
						},
						freeze: true,
						freeze_message: __('Processing ..')
					});
				},
				function(){} // No
			);
		}
		else{
			frappe.throw(__("Please update Close With Employee Table to Close the ERF."))
		}
	},
	confirm_accept_decline_erf: function(frm, status, reason_for_decline) {
		let msg_status = 'Approve';
		if(status != 'Approved'){
			msg_status = (status == 'Accepted' ? 'Accept': 'Decline')
		}
		frappe.confirm(
			__('Do You Want to {0} this ERF', [msg_status]),
			function(){
				// Yes
				frappe.call({
					doc: frm.doc,
					method: 'accept_or_decline',
					args: {status: status, reason_for_decline: reason_for_decline},
					callback(r) {
						if (!r.exc) {
							frm.reload_doc();
						}
					},
					freeze: true,
					freeze_message: __('Processing ..')
				});
			},
			function(){} // No
		);
	},
	draft_erf_to_hrm: function(frm) {
		frappe.confirm(
			__('Do You Want to Draft ERF to HR Manager for Submit'),
			function(){
				// Yes
				frappe.call({
					doc: frm.doc,
					method: 'draft_erf_to_hrm_for_submit',
					callback(r) {
						if (!r.exc) {
							frm.reload_doc();
						}
					},
					freeze: true,
					freeze_message: __('Draft ERF to HR Manager..')
				});
			},
			function(){} // No
		);
	},
	erf_requested_by: function(frm) {
		frm.set_value('erf_requested_by_name', '');
		if(frm.doc.erf_requested_by){
			frappe.call({
				method: 'one_fm.one_fm.doctype.erf.erf.set_user_fullname',
				args: {'user': frm.doc.erf_requested_by},
				callback: function(r) {
					if(r && r.message){
						frm.set_value('erf_requested_by_name', r.message);
					}
				}
			});
		}
	},
	validate: function(frm) {
		if(frm.doc.gender_height_requirement){
			frm.doc.gender_height_requirement.forEach((item, i) => {
				validate_height_exist(frm, item.doctype, item.name);
			});
		}
	},
	onload: function(frm) {
		set_performance_profile_html(frm);
		// set_other_benefits(frm);
	},
	number_of_candidates_required: function(frm) {
    calculate_total_cost_in_salary(frm);
    // set_required_quantity_grd(frm);
	},
  salary_per_person: function(frm) {
    calculate_total_cost_in_salary(frm);
  },
  designation: function(frm) {
		set_default_details_form_designation(frm);
  },
	working_days: function(frm) {
		set_off_days(frm);
	},
	travel_required: function(frm) {
		set_travel_required_btn(frm);
		manage_type_of_travel(frm);
	},
	driving_license_required: function(frm) {
		set_driving_license_required_btn(frm);
		manage_type_of_license(frm);
	},
	grade: function(frm) {
		set_salary_structure(frm);
	},
	salary_structure: function(frm) {
		set_salary_structure_to_salary_details(frm);
	},
	base: function(frm) {
		set_salary_structure_to_salary_details(frm);
	},
	status: function(frm) {
		set_reason_for_decline_reqd(frm);
	},
	expected_date_of_deployment: function(frm) {
		validate_date(frm);
	},
	minimum_experience_required: function(frm) {
		validate_experience_with_min_age(frm);
		validate_experience_range(frm);
	},
	maximum_experience_required: function(frm) {
		validate_experience_with_max_age(frm);
		validate_experience_range(frm);
	},
	is_height_mandatory: function(frm) {
		set_is_hieght_mandatory_in_table(frm);
	},
	shift_working: function(frm) {
		set_shift_working_btn(frm);
	},
	night_shift: function(frm) {
		set_night_shift_btn(frm);
	},
	open_to_different: function(frm) {
		set_open_to_different_btn(frm);
	},
	create_project_for_recruiter: function(frm) {
		create_project(frm);
	},
	okr_workshop_submit_to_hr: function(frm) {
		create_event_for_okr_workshop(frm);
		if(!frm.doc.draft_erf_to_hrm){
			frm.events.draft_erf_to_hrm(frm);
		}
	},
	recruiter_assigned: function(frm) {
		if(frm.doc.recruiter_assigned && !frm.doc.project_for_recruiter){
			document.querySelectorAll('[data-fieldname = "create_project_for_recruiter"]')[1].classList.add('btn-primary');
		}
	},
	project: function(frm) {
		set_project_details_to_erf(frm);
	},
	provide_salary_advance: function(frm) {
		manage_provide_salary_advance(frm);
	}
});

var set_performance_profile_resource_btn = function(frm) {
	if(!frm.is_new() && frm.doc.docstatus<1){
		frm.add_custom_button(__('Get Hand book'), function(){
			resource_btn_action('one_fm.hiring.utils.get_performance_profile_resource', 'Hand book');
		}, "Performance Profile Resources");
		frm.add_custom_button(__('Get Guide'), function(){
			resource_btn_action('one_fm.hiring.utils.get_performance_profile_guid', 'Guide');
		}, "Performance Profile Resources");
	}
	function resource_btn_action(method, label) {
		frappe.call({
			method: method,
			callback: function(r) {
				if(r.message){
					window.open(r.message, '_blank');
					// window.open(r.message, '_self');
				}
				else{
					frappe.msgprint(__("There is no {0} configured in Hiring Settings.", [label]))
				}
			}
		});
	}
};

var set_project_details_to_erf = function(frm) {
	if(frm.doc.project){
		frappe.call({
			method: 'one_fm.one_fm.doctype.erf.erf.get_project_details',
			args: {'project': frm.doc.project},
			callback: function(r) {
				if(r.message){
					var project = r.message;
					if(project.location_list){
						set_filter_for_location(frm, project.location_list);
						if(project.location_list.length == 1){
							frm.set_value('location_of_work', project.location_list[0]);
						}
					}
				}
			},
			freeze: true,
			freeze_message: __('Fetching Data from Project to Set Default Data')
		});
	}
};

var set_filter_for_location = function(frm, location_list) {
	frm.set_query('location_of_work', function () {
		return {
			filters: {
				'name': ['in', location_list]
			}
		};
	});
};

var create_event_for_okr_workshop = function(frm) {
	frappe.call({
		doc: frm.doc,
		method: 'create_event_for_okr_workshop',
		callback: function(r) {
			if(r.message){
				frm.set_value('event_for_okr_workshop', r.message.name);
				frm.save();
			}
			else{
				frm.set_value('event_for_okr_workshop', '');
			}
		},
		freeze: true,
		freeze_message: __('Submit to HR, Creating event...')
	});
};

var create_project = function(frm) {
	var doc = frm.doc;
	var dialog = new frappe.ui.Dialog({
		title: __("Create Project"),
		fields: [
			{
				"fieldtype": "Data",
				"label": __("Project Name"),
				"fieldname": "project_name",
				"reqd": 1
			},
			{
				"fieldtype": "Link",
				"label": __("Project Template"),
				"fieldname": "project_template",
				"options": "Project Template"
			},
			{"fieldtype": "Column Break"},
			{
				"fieldtype": "Date",
				"label": __("Expected Start Date"),
				"fieldname": "expected_start_date"
			}
		]
	});
	dialog.set_primary_action(__('Create'), function() {
		var data = dialog.get_values();
		if(!data) return;
		frappe.call({
			method: "frappe.client.save",
			args: {
				doc: {
					doctype: 'Project',
					project_name: data.project_name,
					project_full_name: data.project_name,
					project_template: data.project_template,
					expected_start_date: data.expected_start_date
				}
			},
			callback:function(r){
				if(r.message){
					dialog.hide();
					frappe.show_alert(__("Project {0} Created.", [r.message.name]));
					frm.set_value('project_for_recruiter', r.message.name);
					frm.save();
				}
			},
			freeze: true,
			freeze_message: __("Creating Project..")
		});
	})
	dialog.show();
};

var set_performance_profile_html = function(frm) {
	var $wrapper = frm.fields_dict.performance_profile_html.$wrapper;
	$wrapper.empty();
	var performance_profile_html = `<div>
	<p style="font-size: 12px; color: #8d99a6;">
		Dear, ${frm.doc.erf_requested_by_name?frm.doc.erf_requested_by_name:''} you are the hiring manager for
		${frm.doc.designation?frm.doc.designation: 'the Designation'}.
		To get an Excellent Hire we will follow the
		<button class="btn btn-default btn-xs adlers_btn" type="button">Adlers</button>
		tried and tested formula of Performance-Based Hiring.
		This starts with creating a performance-based Job Description.
		Here's a Worksheet on Performance base Job Description  -
		<button class="btn btn-default btn-xs performance_profile_guid_btn" type="button">Guide</button>
	</p>
	<p style="font-size: 12px; color: #8d99a6;">
		You may also <button class="btn btn-default btn-xs performance_profile_hand_book_btn" type="button">download a handbook</button> so you can be prepared for the workshop.
	</p>
	<p style="font-size: 12px; color: #8d99a6;">
		You could write below in brief what the hired person will require to do.
		<button class="btn btn-default btn-xs performance_profile_star_eg_btn" type="button">Click here to get STAR Examples</button>
	</p>
	<p style="font-size: 12px; color: #8d99a6;">
		You can also help the HR Prepare -By filling the below
		<ol>
			<li style="font-size: 12px; color: #8d99a6;">
				What does the person hire need to accomplish primarily in the first 3 months to be accounted for as an
				excellent hire.
			</li>
			<li style="font-size: 12px; color: #8d99a6;">
				What is the Value Add This Job will give the Hire? For Eg, New skill learning, relaxed job anything.
			</li>
		</ol>
	</p>
	</div>`;
	$wrapper.html(performance_profile_html);
	$wrapper.on('click', '.performance_profile_hand_book_btn', function() {
		if(frm.doc.docstatus == 0){
			frappe.call({
				method: 'one_fm.hiring.utils.get_performance_profile_resource',
				callback: function(r) {
					if(r.message){
						window.open(r.message, '_blank');
						// window.open(r.message, '_self');
					}
					else{
						frappe.msgprint(__("There is no Hand book configured in Hiring Settings."));
					}
				}
			});
		}
	});
	$wrapper.on('click', '.performance_profile_guid_btn', function() {
		if(frm.doc.docstatus == 0){
			performance_profile_guid_html();
		}
	});
	$wrapper.on('click', '.adlers_btn', function() {
		if(frm.doc.docstatus == 0){
			set_adlers_html();
		}
	});
	$wrapper.on('click', '.performance_profile_star_eg_btn', function() {
		if(frm.doc.docstatus == 0){
			performance_profile_star_eg_html();
		}
	});
};

var performance_profile_star_eg_html = function() {
	var dialog = new frappe.ui.Dialog({
		title: __("STAR Examples"),
		fields: [
			{
				"fieldtype": "HTML",
				"fieldname": "star_eg_html"
			}
		]
	});
	let star_eg_html = `
		<p style="font-size: 12px; color: #8d99a6;">STAR Examples:</p>
		<ol>
		<li style="font-size: 12px; color: #8d99a6;">Project Accountant: Upgrade the international consolidations process by Q3 to ensure the preliminary close  figures are within 1-2% variance of the final close</li>
		<li style="font-size: 12px; color: #8d99a6;">Product Manager: Working with engineering, sales and operations prepare a product launch plan for the (product) within 90 days. Within (days) identify all critical design and test issues needed to ensure an on time product release to manufacturing.</li>
		<li style="font-size: 12px; color: #8d99a6;">Call Center Rep: with 30 days be in a position to handle 4-5 simoultaneous in-bound calls fully resolving 90% of calls within 4-5 Minutes</li>
		</ol>
	`
	dialog.fields_dict.star_eg_html.$wrapper.html(star_eg_html);
	dialog.show();
};

var set_adlers_html = function() {
	var dialog = new frappe.ui.Dialog({
		title: __("Adlers"),
		fields: [
			{
				"fieldtype": "HTML",
				"fieldname": "adlers_html"
			}
		]
	});
	let adlers_html = `
		<p style="font-size: 12px; color: #8d99a6;">
		Lou Adler is the CEO and founder of The Adler Group – a training and search firm helping companies implement
		Performance-based Hiring℠. Adler is the author of the Amazon top-10 best-seller, Hire With Your Head
		(John Wiley & Sons, 3rd Edition, 2007). His most recent book has just been published, The Essential Guide for
		Hiring & Getting Hired (Workbench, 2013). He is also the author of the award-winning Nightingale-Conant audio
		program, Talent Rules! Using Performance-based Hiring to Build Great. https://louadlergroup.com/
		</p>
	`
	dialog.fields_dict.adlers_html.$wrapper.html(adlers_html);
	dialog.show();
};

var performance_profile_guid_html = function() {
	var dialog = new frappe.ui.Dialog({
		title: __("Guide"),
		fields: [
			{
				"fieldtype": "HTML",
				"fieldname": "guid_html"
			}
		]
	});
	dialog.fields_dict.guid_html.$wrapper.html(frappe.render_template('guid_html'));
	dialog.show();
};

var set_open_to_different_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.open_to_different == 'Yes' ? true: false, 'open_to_different_html', 'open_to_different', 'Would you be open to see applicants with a track record of doing these types of work even if the person had a different mix of skills, exp ?');
};

var set_travel_required_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.travel_required, 'travel_required_html', 'travel_required', 'Is Travel a primary/critial Job Need?');
};

var set_shift_hours_btn = function(frm) {
	var $wrapper = frm.fields_dict.shift_hours_html.$wrapper;
	var selected = 'btn-primary';
	var val = frm.doc.shift_hours;
	if(val != 12 && val != 8 && val != 9){
		val = 'Custom';
		frm.set_df_property('shift_hours', 'hidden', false);
	}
	else{
		frm.set_df_property('shift_hours', 'hidden', true);
	}
	var shift_hours_html = `<div><label class="control-label" style="padding-right: 0px;">Shift Hours</label></div><div>
		<button class="btn btn-default btn-xs ${val=="12" ? selected: ''} shift_hours_btn_html" type="button" data-shift_hours='12'>12</button>
		<button class="btn btn-default btn-xs ${val=="9" ? selected: ''} shift_hours_btn_html" type="button" data-shift_hours='9'>9</button>
		<button class="btn btn-default btn-xs ${val=="8" ? selected: ''} shift_hours_btn_html" type="button" data-shift_hours='8'>8</button>
		<button class="btn btn-default btn-xs ${val=="Custom" ? selected: ''} shift_hours_btn_html" type="button" data-shift_hours='Custom'>Custom</button>
	</div>`;
	$wrapper
		.html(shift_hours_html);
	$wrapper.on('click', '.shift_hours_btn_html', function() {
		if(frm.doc.docstatus == 0){
			var $btn = $(this);
			$wrapper.find('.shift_hours_btn_html').removeClass('btn-primary');
			$btn.addClass('btn-primary');
			if($btn.attr('data-shift_hours') == 'Custom'){
				frm.set_df_property('shift_hours', 'hidden', false);
				frm.set_value('shift_hours', '');
			}
			else{
				frm.set_df_property('shift_hours', 'hidden', true);
				frm.set_value('shift_hours', $btn.attr('data-shift_hours'));
			}
		}
	});
};

var set_type_of_license_btn = function(frm) {
	var $wrapper = frm.fields_dict.type_of_license_html.$wrapper;
	if(frm.doc.driving_license_required){
		var selected = 'btn-primary';
		var val = frm.doc.type_of_license;
		var type_of_license_html = `<div><label class="control-label" style="padding-right: 0px;">Type of License</label></div><div>
			<button class="btn btn-default btn-xs ${val=="Light" ? selected: ''} type_of_license_btn_html"
				type="button" data-type_of_license='Light'>Light</button>
			<button class="btn btn-default btn-xs ${val=="Heavy" ? selected: ''} type_of_license_btn_html"
				type="button" data-type_of_license='Heavy'>Heavy</button>
			<button class="btn btn-default btn-xs ${val=="Motor Bike" ? selected: ''} type_of_license_btn_html"
				type="button" data-type_of_license='Motor Bike'>Motor Bike</button>
			<button class="btn btn-default btn-xs ${val=="Inshaya" ? selected: ''} type_of_license_btn_html"
				type="button" data-type_of_license='Inshaya'>Inshaya</button>
		</div>`;
		$wrapper
			.html(type_of_license_html);
		$wrapper.on('click', '.type_of_license_btn_html', function() {
			if(frm.doc.docstatus == 0){
				var $btn = $(this);
				$wrapper.find('.type_of_license_btn_html').removeClass('btn-primary');
				$btn.addClass('btn-primary');
				frm.set_value('type_of_license', $btn.attr('data-type_of_license'));
			}
		});
	}
	else{
		$wrapper.html("");
	}
};

var set_provide_salary_advance_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.provide_salary_advance, 'provide_salary_advance_html',
		'provide_salary_advance', 'Will this Position Require an Advance Salary?');
};

var set_provide_accommodation_by_company_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.provide_accommodation_by_company, 'provide_accommodation_by_company_html',
		'provide_accommodation_by_company', 'Will Accommodation be Provided?');
};

var set_provide_transportation_by_company_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.provide_transportation_by_company, 'provide_transportation_by_company_html',
		'provide_transportation_by_company', 'Will Transportation be Provided?');
};

var set_provide_vehicle_by_company_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.provide_vehicle_by_company, 'provide_vehicle_by_company_html',
		'provide_vehicle_by_company', 'Will Vehicle be Provided?');
};

var set_provide_laptop_by_company_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.provide_laptop_by_company, 'provide_laptop_by_company_html',
		'provide_laptop_by_company', 'Will Laptop be Provided?');
};

var set_email_access_needed_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.email_access_needed, 'email_access_needed_html',
		'email_access_needed', 'Will Email Access be Needed?');
};

var set_provide_health_insurance_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.provide_health_insurance, 'provide_health_insurance_html',
		'provide_health_insurance', 'Private Self-Health Insurance Provide?');
};

var set_provide_mobile_with_line_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.provide_mobile_with_line, 'provide_mobile_with_line_html',
		'provide_mobile_with_line', 'Provide Private Mobile with Line?');
};

var set_provide_company_insurance_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.provide_company_insurance, 'provide_company_insurance_html',
		'provide_company_insurance', 'Provide Company Insurance?');
};

var set_driving_license_required_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.driving_license_required, 'driving_license_required_html', 'driving_license_required', 'Is Kuwait Driving License a Mandatory Requirement?');
};

var set_is_id_card_needed_for_employee_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.is_id_card_needed_for_employee, 'is_id_card_needed_for_employee_html', 'is_id_card_needed_for_employee', 'Is ID Card Needed For Employee?');
};

var set_is_uniform_needed_for_this_job_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.is_uniform_needed_for_this_job, 'is_uniform_needed_for_this_job_html', 'is_uniform_needed_for_this_job', 'Is Uniform Needed for this Job?');
};

var set_shift_working_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.shift_working, 'shift_working_html', 'shift_working', 'Will The Employee Work In Shifts?');
};

var set_night_shift_btn = function(frm) {
	yes_no_html_buttons(frm, frm.doc.night_shift, 'night_shift_html', 'night_shift', 'Will The Employee Work In Night Shifts?');
};

var yes_no_html_buttons = function(frm, val, html_field, field_name, label) {
	var $wrapper = frm.fields_dict[html_field].$wrapper;
	var selected = 'btn-primary';
	var field_btn_html = field_name+'_btn_html';
	var field_html = `<div><label class="control-label" style="padding-right: 0px;">${label}</label></div><div>
		<button class="btn btn-default btn-xs ${val ? selected: ''} ${field_btn_html}" type="button" data='Yes'>Yes</button>
		<button class="btn btn-default btn-xs ${!val ? selected: ''} ${field_btn_html}" type="button" data='No'>No</button>
	</div>`;
	$wrapper
		.html(field_html);
	$wrapper.on('click', '.'+field_btn_html, function() {
		if(frm.doc.docstatus == 0){
			var $btn = $(this);
			$wrapper.find('.'+field_btn_html).removeClass('btn-primary');
			$btn.addClass('btn-primary');
			if(field_name == 'open_to_different'){
				frm.set_value(field_name, $btn.attr('data'));
			}
			else{
				frm.set_value(field_name, $btn.attr('data')=='Yes'? true:false);
			}
		}
	});
};

var set_is_hieght_mandatory_in_table = function(frm) {
	if(frm.doc.gender_height_requirement){
		frm.doc.gender_height_requirement.forEach((item, i) => {
			frappe.model.set_value(item.doctype, item.name, 'is_height_mandatory', frm.doc.is_height_mandatory);
		});
		frm.refresh_field('gender_height_requirement');
	}
};

var validate_experience_with_min_age = function(frm) {
	if(frm.doc.minimum_experience_required && frm.doc.gender_height_requirement){
		frm.doc.gender_height_requirement.forEach((item, i) => {
			if(item.minimum_age < frm.doc.minimum_experience_required){
				frm.set_value('minimum_experience_required', '');
				frappe.throw(__('Minimum Experience Required cannot be greater than Minimum Age in Row{0} - Candidates Required', [item.idx]));
			}
		});
	}
};

var validate_experience_with_max_age = function(frm) {
	if(frm.doc.maximum_experience_required && frm.doc.gender_height_requirement){
		frm.doc.gender_height_requirement.forEach((item, i) => {
			if(item.maximum_age < frm.doc.maximum_experience_required){
				frm.set_value('maximum_experience_required', '');
				frappe.throw(__('Maximum Experience Required cannot be greater than Maximum Age in Row{0} - Candidates Required', [item.idx]));
			}
		});
	}
};

var validate_experience_range = function(frm) {
	if(frm.doc.minimum_experience_required && frm.doc.maximum_experience_required){
		if(frm.doc.minimum_experience_required > frm.doc.maximum_experience_required){
			frm.set_value('maximum_experience_required', '');
			frappe.throw(__('Minimum Experience Required cannot be greater than Maximum Experience Required'))
		}
	}
};

var validate_date = function(frm) {
	if(frm.doc.expected_date_of_deployment < frm.doc.erf_initiation){
		frm.set_value('expected_date_of_deployment', '');
		frappe.throw(__("Expected Date of Deployment cannot be before ERF Initiation Date"));
	}
	if(frm.doc.expected_date_of_deployment < frappe.datetime.now_date()){
		frm.set_value('expected_date_of_deployment', '');
		frappe.throw(__("Expected Date of Deployment cannot be before Today"));
	}
};

frappe.ui.form.on('ERF Gender Height Requirement', {
	gender_height_requirement_add: function(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, 'is_height_mandatory', frm.doc.is_height_mandatory);
	},
	number: function(frm, cdt, cdn){
    validate_total_required_candidates(frm, cdt, cdn);
  },
	height: function(frm, cdt, cdn) {
		validate_height_range(frm, cdt, cdn);
	},
	is_height_mandatory: function(frm, cdt, cdn) {
		// validate_height_exist(frm, cdt, cdn);
	},
	minimum_age: function(frm, cdt, cdn) {
		validate_age_range(frm, cdt, cdn);
	},
	maximum_age: function(frm, cdt, cdn) {
		validate_age_range(frm, cdt, cdn);
	}

});

var validate_age_range = function(frm, cdt, cdn) {
	var child = locals[cdt][cdn];
	if(child.minimum_age && child.minimum_age <= 15){
		frappe.model.set_value(child.doctype, child.name, 'minimum_age', '');
		frappe.throw(__("Minimum Age Required (In Years) is cannot be Less than or equal to 15 Years"));
	}
	if(child.maximum_age && child.maximum_age >= 70){
		frappe.model.set_value(child.doctype, child.name, 'maximum_age', '');
		frappe.throw(__("Maximum Age Required (In Years) is cannot be Greater than or equal to 70 Years"));
	}
	if(child.minimum_age && child.maximum_age){
		if(child.minimum_age > child.maximum_age){
			frappe.model.set_value(child.doctype, child.name, 'maximum_age', '');
			frappe.throw(__("Maximum Age Required (In Years) is cannot be Greater than Minimum Age Required (In Years)"));
		}
	}
};

var validate_height_exist = function(frm, cdt, cdn) {
	var child = locals[cdt][cdn];
	if(child.is_height_mandatory && !child.height){
		frappe.throw(__('Please put an Height, If Height is Mandatory'));
	}
};

var validate_height_range = function(frm, cdt, cdn) {
	var child = locals[cdt][cdn];
	if(child.height && child.height <= 145){
		frappe.model.set_value(child.doctype, child.name, 'height', '');
		frm.refresh_field('gender_height_requirement');
		frappe.throw(__('Hieght Must be greter than 10cm.'));
	}
};

frappe.ui.form.on('ERF Salary Detail', {
	amount: function(frm, cdt, cdn){
    calculate_salary_per_person(frm);
  }
});

frappe.ui.form.on('ERF Employee Benefit', {
	cost: function(frm, cdt, cdn){
    calculate_benefit_cost_to_company(frm);
  }
});

var set_reason_for_decline_reqd = function(frm) {
	if(frm.doc.status == 'Declined'){
		frm.set_df_property('reason_for_decline', 'reqd', true);
	}
	else{
		frm.set_df_property('reason_for_decline', 'reqd', false);
	}
};

var calculate_benefit_cost_to_company = function(frm) {
	let total = 0;
	if(frm.doc.other_benefits){
    frm.doc.other_benefits.forEach(function(benefit) {
      total += benefit.cost;
    });
  }
  frm.set_value('benefit_cost_to_company', total);
	calculate_total_cost_to_company(frm);
};

var set_other_benefits = function(frm) {
	if(!frm.doc.other_benefits){
		frm.clear_table('other_benefits');
		let options = ['Company Provided Car', 'Mobile with Line', 'Health Insurance'];
		options.forEach((option) => {
			let benefit = frappe.model.add_child(frm.doc, 'ERF Employee Benefit', 'other_benefits');
			frappe.model.set_value(benefit.doctype, benefit.name, 'benefit', option);
		});
		frm.refresh_field('other_benefits');
	}
};

var set_salary_structure = function(frm) {
	if(frm.doc.grade){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Employee Grade',
				filters: {name: frm.doc.grade}
			},
			callback: function(r) {
					if(r.message && r.message.default_salary_structure){
						frm.set_value('salary_structure', r.message.default_salary_structure);
					}
					else{
						frm.set_value('salary_structure', '');
					}
			}
		});
	}
	else{
		frm.set_value('salary_structure', '');
	}
};

var manage_type_of_license = function(frm) {
	set_type_of_license_btn(frm);
	if(frm.doc.driving_license_required){
		frm.set_df_property('type_of_license', 'reqd', true);
	}
	else{
		frm.set_df_property('type_of_license', 'reqd', false);
		frm.set_value('type_of_license', '');
	}
};

var manage_provide_salary_advance = function(frm) {
	// if(frm.doc.provide_salary_advance){
	// 	frm.set_df_property('amount_in_advance', 'reqd', true);
	// }
	// else{
	// 	frm.set_df_property('amount_in_advance', 'reqd', false);
	// 	frm.set_value('amount_in_advance', '');
	// }
};

var manage_type_of_travel = function(frm) {
	if(frm.doc.travel_required){
		frm.set_df_property('type_of_travel', 'reqd', true);
	}
	else{
		frm.set_df_property('type_of_travel', 'reqd', false);
		frm.set_value('type_of_travel', '');
	}
};

var set_off_days = function(frm) {
	if(frm.doc.working_days > 0){
		frm.set_value('off_days', 30-frm.doc.working_days);
	}
};

// var set_required_quantity_grd = function(frm) {
//   if(frm.doc.number_of_candidates_required){
//     frm.set_value('required_quantity', frm.doc.number_of_candidates_required);
//   }
//   else{
//     frm.set_value('required_quantity', 0);
//   }
// }

var validate_total_required_candidates = function (frm, cdt, cdn) {
  let total = 0;
	var child = locals[cdt][cdn];
  if(frm.doc.gender_height_requirement){
    frm.doc.gender_height_requirement.forEach(function(required_candidate) {
      total += required_candidate.number;
    });
  }
	if(total != frm.doc.number_of_candidates_required){
		frappe.show_alert(__('Total Number Candidates Required Should be {0}.', [frm.doc.number_of_candidates_required]));
	}
};

var calculate_salary_per_person = function (frm) {
  let total = 0;
  if(frm.doc.salary_details){
    frm.doc.salary_details.forEach(function(salary_detail) {
      total += salary_detail.amount;
    });
  }
  frm.set_value('salary_per_person', total);
};

var calculate_total_cost_in_salary = function (frm) {
  if(frm.doc.number_of_candidates_required > 0 && frm.doc.salary_per_person > 0){
    frm.set_value('total_cost_in_salary', frm.doc.number_of_candidates_required * frm.doc.salary_per_person);
  }
  else{
    frm.set_value('total_cost_in_salary', 0);
  }
	calculate_total_cost_to_company(frm);
};

var calculate_total_cost_to_company = function(frm) {
	if(frm.doc.total_cost_in_salary && frm.doc.benefit_cost_to_company){
		frm.set_value('total_cost_to_company', frm.doc.total_cost_in_salary+frm.doc.benefit_cost_to_company);
	}
};

var set_default_details_form_designation = function(frm) {
	frm.clear_table("designation_skill");
	frm.clear_table("languages");
	frm.clear_table("tool_request_item");
  if(frm.doc.designation){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: "Designation",
				filters: {"name":frm.doc.designation}
			},
			callback: function(r) {
				if(r.message && r.message.skills){
					set_designation_childs_in_erf(frm, r.message.skills, 'Designation Skill', 'designation_skill', ['skill', 'one_fm_proficiency']);
				}
			},
			freeze: true,
			freeze_message: __('Fetching Data from Designation to Set Default Data')
		});
  }
	frm.refresh_fields();
};

var set_designation_childs_in_erf = function(frm, data, child_doc, child_field, child_doc_fields) {
	data.forEach((item) => {
		let child_item = frappe.model.add_child(frm.doc, child_doc, child_field);
		child_doc_fields.forEach((field) => {
			frappe.model.set_value(child_item.doctype, child_item.name, field, item[field]);
		});
	});
	frm.refresh_field(child_field);
};

var set_salary_structure_to_salary_details = function(frm) {
	frm.clear_table('salary_details');
	let total_amount = 0;
	frm.set_value('salary_per_person', total_amount);
	frm.refresh_field('salary_details');
	if(frm.doc.salary_structure && frm.doc.base){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Salary Structure',
				filters: {'name': frm.doc.salary_structure}
			},
			callback: function(r) {
				if(r && r.message && r.message.earnings){
					r.message.earnings.forEach((item, i) => {
						let amount = item.amount ? item.amount : 0
						if(item.amount_based_on_formula && item.formula){
							const percent = item.formula.split("*")[1];
							amount = parseInt(frm.doc.base)*parseFloat(percent);
						}
						total_amount += amount;
						let salary = frappe.model.add_child(frm.doc, 'ERF Salary Detail', 'salary_details');
						frappe.model.set_value(salary.doctype, salary.name, 'salary_component', item.salary_component);
						frappe.model.set_value(salary.doctype, salary.name, 'amount', amount);
					});
				}
				frm.set_value('salary_per_person', total_amount);
				frm.refresh_field('salary_details');
			}
		});
	}
};
