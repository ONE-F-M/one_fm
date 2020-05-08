// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Career History', {
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
	job_start_date: function(frm, cdt, cdn) {
    calculate_years_of_experience(frm, cdt, cdn);
	},
  job_end_date: function(frm, cdt, cdn) {
    calculate_years_of_experience(frm, cdt, cdn);
  },
  years_of_experience: function(frm) {
    calculate_total_years_of_experience(frm);
  },
  recruiter_validation_score_promotion: function(frm) {
    calculate_number_promotions_and_salary_changes(frm);
  },
  recruiter_validation_score_salary_change: function(frm) {
    calculate_number_promotions_and_salary_changes(frm);
  },
  career_history_company_remove: function(frm, cdt, cdn) {
    if(frm.doc.career_history_company.length < frm.doc.number_of_companies){
      frappe.msgprint(__('Not Permitted, Please Update the Number of Companies to Remove Row.'));
      frappe.model.add_child(frm.doc, 'Career History Company', 'career_history_company');
    }
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
  if(frm.doc.career_history_company){
    frm.doc.career_history_company.forEach((item) => {
      total += item.recruiter_validation_score_promotion?item.recruiter_validation_score_promotion:0;
      total += item.recruiter_validation_score_salary_change?item.recruiter_validation_score_salary_change:0;
    });
  }
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
