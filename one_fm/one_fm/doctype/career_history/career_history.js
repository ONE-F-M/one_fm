// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Career History', {
	refresh: function(frm) {
		set_company_options(frm);
		set_promotions_and_salary_hike_field(frm);
	},
	job_applicant: function(frm) {
    set_job_applicant_details(frm);
	},
  number_of_companies: function(frm) {
    if(frm.doc.number_of_companies <= 0){
      frm.set_value('number_of_companies', 1);
    }
    set_career_history_company_item(frm);
  }
});

frappe.ui.form.on('Career History Company', {
	company_name: function(frm) {
		set_company_options(frm);
	},
	job_start_date: function(frm, cdt, cdn) {
    calculate_years_of_experience(frm, cdt, cdn);
	},
  job_end_date: function(frm, cdt, cdn) {
    calculate_years_of_experience(frm, cdt, cdn);
  },
  years_of_experience: function(frm) {
    calculate_total_years_of_experience(frm);
  },
  career_history_company_remove: function(frm, cdt, cdn) {
    if(frm.doc.career_history_company.length < frm.doc.number_of_companies){
      frappe.msgprint(__('Not Permitted, Please Update the Number of Companies to Remove Row.'));
      frappe.model.add_child(frm.doc, 'Career History Company', 'career_history_company');
    }
  },
	did_you_get_any_promotion: function(frm, cdt, cdn) {
		validate_promotion_item_exists(frm, cdt, cdn);
		set_promotions_and_salary_hike_field(frm);
	},
	did_you_get_any_salary_increase: function(frm) {
		validate_salary_hikes_item_exists(frm, cdt, cdn);
		set_promotions_and_salary_hike_field(frm);
	}
});

var validate_promotion_item_exists = function(frm, cdt, cdn) {
	var child = locals[cdt][cdn];
	if(child.did_you_get_any_promotion == 'No' && frm.doc.promotions){
		frm.doc.promotions.forEach((item) => {
	    if(item.company_name == child.company_name){
				frappe.model.set_value(child.doctype, child.name, 'did_you_get_any_promotion', 'Yes');
				frm.refresh_field('promotions');
				frappe.throw(__("Please Clear the Promotion Details for the Company"))
			}
	  });
	}
};

var validate_salary_hikes_item_exists = function(frm, cdt, cdn) {
	var child = locals[cdt][cdn];
	if(child.did_you_get_any_salary_increase == 'No' && frm.doc.salary_hikes){
		frm.doc.salary_hikes.forEach((item) => {
	    if(item.company_name == child.company_name){
				frappe.model.set_value(child.doctype, child.name, 'did_you_get_any_salary_increase', 'Yes');
				frm.refresh_field('salary_hikes');
				frappe.throw(__("Please Clear the Salary Hike Details for the Company"))
			}
	  });
	}
};

var set_promotions_and_salary_hike_field = function(frm) {
	let promotions = false;
	let salary_hikes = false;
	if(frm.doc.career_history_company){
		frm.doc.career_history_company.forEach((item) => {
	    if(item.did_you_get_any_promotion == 'Yes'){
				promotions = true;
			}
			if(item.did_you_get_any_salary_increase == 'Yes'){
				salary_hikes = true;
			}
	  });
	}
	frm.set_df_property('promotions_section', 'hidden', !promotions);
	frm.set_df_property('salary_hikes_section', 'hidden', !salary_hikes);
	frm.set_df_property('promotions', 'reqd', promotions);
	frm.set_df_property('salary_hikes', 'reqd', salary_hikes);
	if(!promotions){
		frm.clear_table('promotions');
	}
	if(!salary_hikes){
		frm.clear_table('salary_hikes');
	}
};

var set_company_options = function(frm) {
  var options = [''];
  frm.doc.career_history_company.forEach((item, i) => {
    options[i+1] = item.company_name;
  });
  frappe.meta.get_docfield("Career History Promotion", "company_name", frm.doc.name).options = options;
	frappe.meta.get_docfield("Career History Salary Hike", "company_name", frm.doc.name).options = options;
  frm.refresh_field('promotions');
	frm.refresh_field('salary_hikes');
};

frappe.ui.form.on('Career History Promotion', {
  recruiter_validation_score: function(frm) {
    calculate_number_promotions_and_salary_changes(frm);
  }
});

frappe.ui.form.on('Career History Salary Hike', {
  recruiter_validation_score: function(frm) {
    calculate_number_promotions_and_salary_changes(frm);
  }
});

var set_career_history_company_item = function(frm) {
  if(frm.doc.number_of_companies > 0){
    if(frm.doc.career_history_company){
        if(frm.doc.career_history_company.length < frm.doc.number_of_companies){
          create_career_history_company_item(frm);
        }
    }
    else{
      create_career_history_company_item(frm);
    }
  }
};

var create_career_history_company_item = function(frm) {
  var the_factor = frm.doc.number_of_companies - frm.doc.career_history_company.length
  for (var i = 0; i < the_factor; i++) {
    frappe.model.add_child(frm.doc, 'Career History Company', 'career_history_company');
  }
  frm.refresh_field('career_history_company');
};

var calculate_career_history_score = function(frm) {
  var career_history_score = 0;
  if(frm.doc.number_promotions_and_salary_changes && frm.doc.total_years_of_experience){
    var the_factor = frm.doc.number_promotions_and_salary_changes/frm.doc.total_years_of_experience;
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

var calculate_number_promotions_and_salary_changes = function(frm) {
  let total = 0;
	let total_promotion = 0;
	let total_salary_hike = 0;
  if(frm.doc.promotions){
    frm.doc.promotions.forEach((item) => {
      total += item.recruiter_validation_score?item.recruiter_validation_score:0;
			total_promotion += item.recruiter_validation_score?item.recruiter_validation_score:0;
    });
  }
	if(frm.doc.salary_hikes){
    frm.doc.salary_hikes.forEach((item) => {
      total += item.recruiter_validation_score?item.recruiter_validation_score:0;
			total_salary_hike += item.recruiter_validation_score?item.recruiter_validation_score:0;
    });
  }
	frm.set_value('promotion_total_score', total_promotion);
	frm.set_value('salary_hike_total_score', total_salary_hike);
  frm.set_value('number_promotions_and_salary_changes', total);
  calculate_career_history_score(frm);
};

var calculate_years_of_experience = function(frm, cdt, cdn) {
  var child = locals[cdt][cdn];
  if(child.job_start_date && child.job_end_date){
    let	date_diff_ms = Date.parse(child.job_end_date) - Date.parse(child.job_start_date);
  	let	date_obj = new Date();
  	date_obj.setTime(date_diff_ms);
  	let	years =  date_obj.getFullYear() - 1970;
    let month_factor = parseFloat(date_obj.getMonth())/12;
		let years_of_experience_str = '';
		if(years > 0){
			years_of_experience_str = years + " Year(s) ";
		}
		if(date_obj.getMonth() && date_obj.getMonth() > 0){
			years_of_experience_str += date_obj.getMonth() + " Month(s) ";
		}
		child.years_of_experience_str = years_of_experience_str;
    child.years_of_experience = years+month_factor;
  }
  frm.refresh_field('career_history_company');
  calculate_total_years_of_experience(frm);
};

var calculate_total_years_of_experience = function(frm) {
  let total_years_of_experience = 0;
  if(frm.doc.career_history_company){
    frm.doc.career_history_company.forEach((item) => {
      total_years_of_experience += item.years_of_experience?item.years_of_experience:0;
    });
  }
  frm.set_value('total_years_of_experience', total_years_of_experience);
	let years = total_years_of_experience - (total_years_of_experience%1);
	let months = Math.round((total_years_of_experience%1)*12);
	let total_years_of_experience_str = '';
	if(years > 0){
		total_years_of_experience_str = years + " Year(s) ";
	}
	if(months > 0){
		total_years_of_experience_str += months + " Month(s) ";
	}
	frm.set_value('total_years_of_experience_str', total_years_of_experience_str);
	calculate_career_history_score(frm);
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
    frm.set_value('number_of_companies', 1);
    let current_job = frappe.model.add_child(frm.doc, 'Career History Company', 'career_history_company');
    frappe.model.set_value(current_job.doctype, current_job.name, 'current_job', true);
    frappe.model.set_value(current_job.doctype, current_job.name, 'company_name', job_applicant.one_fm_current_employer);
    frappe.model.set_value(current_job.doctype, current_job.name, 'job_title', job_applicant.one_fm_current_job_title);
    frappe.model.set_value(current_job.doctype, current_job.name, 'job_start_date', job_applicant.one_fm_employment_start_date);
    frappe.model.set_value(current_job.doctype, current_job.name, 'job_end_date', job_applicant.one_fm_employment_end_date);
    frappe.model.set_value(current_job.doctype, current_job.name, 'monthly_salary_in_dolor', job_applicant.one_fm_current_salary);
  }
};
