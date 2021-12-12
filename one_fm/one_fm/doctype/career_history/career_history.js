// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Career History', {
	refresh: function(frm) {
		frm.set_query('job_applicant', function () {
			return {
				filters: {
					'status': ['not in', ['Rejected']]
				}
			};
		});
		if(frm.doc.total_years_of_experience){
			set_total_years_of_experience_str(frm, frm.doc.total_years_of_experience);;
		}
	},
	job_applicant: function(frm) {
    set_job_applicant_details(frm);
	},
	pass_to_next_interview: function(frm) {
		confirm_score_action(frm);
	},
	total_years_of_experience: function(frm) {
		set_total_years_of_experience_str(frm, frm.doc.total_years_of_experience);
	}
});

var confirm_score_action = function(frm) {
	if(frm.doc.pass_to_next_interview){
		let msg = __('Do You Need to Set the Value to {0}', [frm.doc.pass_to_next_interview])
		frappe.confirm(
			msg,
			function(){
				// Yes
				if(frm.doc.pass_to_next_interview == 'Reject'){
					frappe.msgprint(__('Applicant Will be Rejected on this Career History Save.'));
				}
				if(frm.doc.pass_to_next_interview == 'Pass'){
					frm.save();
				}
			},
			function(){
				// No
				frm.set_value('pass_to_next_interview', '');
			}
		);
	}
};

frappe.ui.form.on('Career History Company', {
	start_date: function(frm, cdt, cdn) {
		calculate_promotions_and_experience(frm);
	},
	end_date: function(frm, cdt, cdn) {
		calculate_promotions_and_experience(frm);
	},
	job_title: function(frm, cdt, cdn) {
		calculate_promotions_and_experience(frm);
	},
	monthly_salary_in_kwd: function(frm, cdt, cdn) {
		calculate_promotions_and_experience(frm);
	}
});

var calculate_promotions_and_experience = function(frm) {
	let total_years_of_experience = 0;
	let total_number_of_promotions = 0;
	let total_number_of_salary_changes = 0;
	if(frm.doc.career_history_company){
		var start_date_in_company = {};
		var promotions = {};
		var salary_hikes = {};
		var end_date_in_company = {};

		frm.doc.career_history_company.forEach((item) => {
			if(!start_date_in_company[item.company_name]){
				start_date_in_company[item.company_name] = item.start_date;
			}
			if(!end_date_in_company[item.company_name] && item.end_date){
				end_date_in_company[item.company_name] = item.end_date;
			}
			if(!promotions[item.company_name]){
				promotions[item.company_name] = [item.job_title];
			}
			else if(promotions[item.company_name] != item.job_title){
				promotions[item.company_name].push(item.job_title);
			}
			if(!salary_hikes[item.company_name]){
				salary_hikes[item.company_name] = [item.monthly_salary_in_kwd];
			}
			else if(salary_hikes[item.company_name] != item.monthly_salary_in_kwd){
				salary_hikes[item.company_name].push(item.monthly_salary_in_kwd);
			}
		});

		for (var company in start_date_in_company) {
			if (start_date_in_company.hasOwnProperty(company)) {
				var start_date = start_date_in_company[company];
				if(end_date_in_company[company]){
					total_years_of_experience += calculate_total_years_of_experience(start_date, end_date_in_company[company]);
				}
			}
			if(promotions[company]){
				total_number_of_promotions += promotions[company].length-1;
			}
			if(salary_hikes[company]){
				total_number_of_salary_changes += salary_hikes[company].length-1;
			}
		}
	}
	frm.set_value('total_number_of_promotions_and_salary_changes', total_number_of_promotions+total_number_of_salary_changes);
	frm.set_value('total_years_of_experience', total_years_of_experience);
	calculate_career_history_score(frm);
};

var calculate_total_years_of_experience = function(start_date, end_date) {
	let	date_diff_ms = Date.parse(end_date) - Date.parse(start_date);
	let	date_obj = new Date();
	date_obj.setTime(date_diff_ms);
	let	years =  date_obj.getFullYear() - 1970;
	let month_factor = parseFloat(date_obj.getMonth())/12;
	return years+month_factor;
};

var calculate_career_history_score = function(frm) {
  var career_history_score = 0;
  if(frm.doc.total_number_of_promotions_and_salary_changes && frm.doc.total_years_of_experience){
    var the_factor = frm.doc.total_number_of_promotions_and_salary_changes/frm.doc.total_years_of_experience;
    if(the_factor >= 0 && the_factor < 0.25){
      career_history_score = 1
    }
    else if(the_factor >= 0.25 && the_factor < 0.33){
      career_history_score = 2
    }
    else if(the_factor >= 0.33 && the_factor < 0.5){
      career_history_score = 3
    }
    else if(the_factor >= 0.5 && the_factor < 1){
      career_history_score = 4
    }
    else if(the_factor >= 1){
      career_history_score = 5
    }
  }
  frm.set_value('career_history_score', career_history_score);
};

var set_total_years_of_experience_str = function(frm, total_years_of_experience) {
	let years = total_years_of_experience - (total_years_of_experience%1);
	let months = Math.round((total_years_of_experience%1)*12);
	let total_years_of_experience_str = '';
	if(years > 0){
		total_years_of_experience_str = years + " Year(s) ";
	}
	if(months > 0){
		total_years_of_experience_str += months + " Month(s) ";
	}
	frm.set_df_property('total_years_of_experience', 'description', total_years_of_experience_str);
};

var set_job_applicant_details = function(frm) {
  if(frm.doc.job_applicant){
    frappe.call({
      method: 'frappe.client.get',
      args:{
        doctype: 'Job Applicant',
        filters: {name: frm.doc.job_applicant}
      },
      callback: function(r) {
        frm.clear_table('career_history_company');
        if(r && r.message){
          var job_applicant = r.message;
          set_current_job_details(frm, job_applicant);
        }
        frm.refresh_field('career_history_company');
      }
    })
  }
  else{
    frm.clear_table('career_history_company');
  }
};

var set_current_job_details = function(frm, job_applicant) {
  if(job_applicant.one_fm_i_am_currently_working){
    let current_job = frappe.model.add_child(frm.doc, 'Career History Company', 'career_history_company');
    frappe.model.set_value(current_job.doctype, current_job.name, 'current_job', true);
    frappe.model.set_value(current_job.doctype, current_job.name, 'company_name', job_applicant.one_fm_current_employer);
    frappe.model.set_value(current_job.doctype, current_job.name, 'job_title', job_applicant.one_fm_current_job_title);
		frappe.model.set_value(current_job.doctype, current_job.name, 'country_of_employment', job_applicant.one_fm_country_of_employment);
    frappe.model.set_value(current_job.doctype, current_job.name, 'start_date', job_applicant.one_fm_employment_start_date);
    frappe.model.set_value(current_job.doctype, current_job.name, 'end_date', job_applicant.one_fm_employment_end_date);
    frappe.model.set_value(current_job.doctype, current_job.name, 'monthly_salary_in_dolor', job_applicant.one_fm_current_salary);
  }
};
