frappe.ui.form.on('Job Offer', {
  refresh(frm) {
    if(frm.is_new()){
      frm.set_value('offer_date', frappe.datetime.now_date());
    }
    check_and_info_offer_terms(frm, false);
    frm.remove_custom_button("Create Employee");
    if ((!frm.doc.__islocal) && (frm.doc.status == 'Accepted')
			&& (frm.doc.docstatus === 1) && (!frm.doc.__onload || !frm.doc.__onload.employee)) {
      frm.add_custom_button(__('Create New Transfer Paper'),
				function () {
          frappe.model.open_mapped_doc({
            method: "one_fm.hiring.utils.make_transfer_paper_from_job_offer",
            frm: frm
          });
				}
			);
		}
    if (frm.doc.workflow_state == 'Accepted' && frm.doc.docstatus === 1){
      if (!frm.doc.__onload || !frm.doc.__onload.onboard_employee){
        frm.add_custom_button(__('Start Onboard Employee'),
  				function () {
            frappe.call({
              method: 'one_fm.hiring.utils.btn_create_onboarding_from_job_offer',
              args: {'job_offer': frm.doc.name},
              callback: function functionName(r) {
                frm.reload_doc();
              },
              freeze: true,
              freeze_message: __("Creating Onboard Employee ...!")
            });
  				}
  			);
  		}
      else if (frm.doc.__onload && frm.doc.__onload.onboard_employee) {
        frm.add_custom_button(__('Go to Onboard Employee'),
  				function () {
            frappe.set_route("Form", "Onboard Employee", frm.doc.__onload.onboard_employee);
  				}
  			);
      }
    }
    set_filters(frm);
  },
  validate: function(frm) {
    // check_and_info_offer_terms(frm);
  },
  one_fm_provide_accommodation_by_company: function(frm) {
    // check_and_info_offer_terms(frm, 'one_fm_provide_accommodation_by_company');
  },
  one_fm_provide_transportation_by_company: function(frm) {
    // check_and_info_offer_terms(frm, 'one_fm_provide_transportation_by_company');
  },
  job_applicant: function(frm) {
    set_job_applicant_details(frm);
  },
	one_fm_notify_finance_department: function(frm) {
		if(!frm.is_new() && frm.doc.one_fm_provide_salary_advance && frm.doc.one_fm_salary_advance_amount > 0 && !frm.doc.one_fm_notified_finance_department){
			frappe.call({
				method: 'one_fm.hiring.utils.notify_finance_job_offer_salary_advance',
				args: {'job_offer_id': frm.doc.name},
				callback: function(r) {
					if(!r.exc) {
						frappe.msgprint("Notified Finance Department!");
						frm.reload_doc();
					}
				},
				freeze: true,
				freeze_message: __("Notifying Finance Department."),
			});
		}
	},
  one_fm_salary_structure: function(frm) {
    set_salary_structure_to_salary_details(frm);
  },
  base: function(frm) {
    set_salary_structure_to_salary_details(frm);
  },
  employee_grade: function(frm) {
    set_filters(frm);
  }
});

var set_filters = function(frm) {
  var filters = {};
  if(frm.doc.employee_grade){
    filters['employee_grade'] = frm.doc.employee_grade;
  }
	frm.set_query("one_fm_salary_structure", function() {
		return {
			query: "one_fm.one_fm.utils.get_salary_structure_list",
			filters: filters
		}
	});
};

var check_and_info_offer_terms = function(frm, field_name) {
  if(frm.doc.one_fm_provide_accommodation_by_company || frm.doc.one_fm_provide_transportation_by_company){
    if (frm.doc.one_fm_salary_details){
      var exists = false;
      frm.doc.one_fm_salary_details.forEach((item, i) => {
        if(item.salary_component.includes('Accommodation') || item.salary_component.includes('Transportation')){
          exists = true;
        }
      });
      if(exists){
        let msg = __("Accommodation / Transportation is listed in the Salary Structure, Please confirm if it is provide by company.!!");
        frm.set_intro(msg, 'yellow');
        if(field_name){
          confirm_input(frm, msg, field_name)
        }
      }
    }
  }
};

var confirm_input = function(frm, msg, field_name) {
  frappe.confirm(
    msg+" Would you like to continue ?",
    function(){
      validated = true;
    }, // Yes
    function(){
      // No
      frm.set_value(field_name, '');
      validated = false;
    }
  );
}

var set_job_applicant_details = function(frm) {
  if(frm.doc.job_applicant){
    frappe.db.get_value('Job Applicant', frm.doc.job_applicant, 'one_fm_erf', function(r) {
      if(r && r.one_fm_erf){
        frappe.call({
          method: 'frappe.client.get',
          args: {
            doctype: 'ERF',
            filters: {'name': r.one_fm_erf}
          },
          callback: function(ret) {
            if(ret && ret.message){
              var erf = ret.message;
              set_erf_details(frm, erf);
            }
          }
        });
      }
    });
  }
};

var set_erf_details = function(frm, erf) {
  frm.set_value('designation', erf.designation);
  set_salary_details(frm, erf);
  // set_other_benefits_to_terms(frm, erf);
};

var set_salary_details = function(frm, erf) {
  frm.set_value('one_fm_salary_structure', erf.salary_structure);
  if(erf.salary_details && !erf.salary_structure){
    frm.clear_table('one_fm_salary_details');
    let total_amount = 0;
    erf.salary_details.forEach((item, i) => {
      total_amount += item.amount;
      let salary = frappe.model.add_child(frm.doc, 'ERF Salary Detail', 'one_fm_salary_details');
      frappe.model.set_value(salary.doctype, salary.name, 'salary_component', item.salary_component);
      frappe.model.set_value(salary.doctype, salary.name, 'amount', item.amount);
    });
    frm.set_value('one_fm_job_offer_total_salary', total_amount);
    frm.refresh_field('one_fm_salary_details');
  }
};

var set_salary_structure_to_salary_details = function(frm) {
  frm.clear_table('one_fm_salary_details');
  let total_amount = 0;
  let base = frm.doc.base
  console.log(base)
  if(frm.doc.one_fm_salary_structure && base){
    frappe.call({
      method: 'frappe.client.get',
      args: {
        doctype: 'Salary Structure',
        filters: {'name': frm.doc.one_fm_salary_structure}
      },
      callback: function(r) {
        if(r && r.message){
          if(r.message.earnings){
            r.message.earnings.forEach((item, i) => {
              console.log(item.amount_based_on_formula)
              if(item.amount_based_on_formula && item.formula){
                let formula = item.formula;
                const percent = formula.split("*")[1];
                let amount = parseInt(base)*parseFloat(percent);
                total_amount += amount;
                if(amount!=0){
                  let salary = frappe.model.add_child(frm.doc, 'ERF Salary Detail', 'one_fm_salary_details');
                  frappe.model.set_value(salary.doctype, salary.name, 'salary_component', item.salary_component);
                  frappe.model.set_value(salary.doctype, salary.name, 'amount', amount);
                }
              } else {
                total_amount += item.amount;
                if(item.amount!=0){
                  let salary = frappe.model.add_child(frm.doc, 'ERF Salary Detail', 'one_fm_salary_details');
                  frappe.model.set_value(salary.doctype, salary.name, 'salary_component', item.salary_component);
                  frappe.model.set_value(salary.doctype, salary.name, 'amount', item.amount);
                } 
              }
            });
          }
        }
        frm.set_value('one_fm_job_offer_total_salary', total_amount);
        frm.refresh_field('one_fm_salary_details');
      }
    });
  }
  frm.set_value('one_fm_job_offer_total_salary', total_amount);
  frm.refresh_field('one_fm_salary_details');
};

frappe.ui.form.on('ERF Salary Detail', {
  one_fm_salary_details_remove: function(frm, cdt, cdn) {
    calculate_total_salary(frm);
  },
  amount: function(frm, cdt, cdn) {
    calculate_total_salary(frm);
  }
});

var calculate_total_salary = function(frm) {
  let total_amount = 0;
  if(frm.doc.one_fm_salary_details){
    frm.doc.one_fm_salary_details.forEach((item, i) => {
      total_amount += item.amount;
    });
  }
  frm.set_value('one_fm_job_offer_total_salary', total_amount);
  frm.refresh_field('one_fm_salary_details');
};

var set_other_benefits_to_terms = function(frm, erf) {
  var terms_list = [];
  if(erf.other_benefits){
    erf.other_benefits.forEach((item) => {
      terms_list.push({'offer_term': item.benefit, 'value': 'Company Provided'});
    });
  }
  var terms = ['Kuwait Visa processing Fees', 'Kuwait Residency Fees', 'Kuwait insurance Fees']
  terms.forEach((item) => {
    terms_list.push({'offer_term': item, 'value': 'Borne By The Company'});
  });
  var hours = erf.shift_hours?erf.shift_hours:9;
  let vacation_days = erf.vacation_days?erf.vacation_days:30;
  terms_list.push({'offer_term': 'Working Hours', 'value': hours+' hours a day, (Subject to Operational Requirements) from Sunday to Thursday'});
  terms_list.push({'offer_term': 'Annual Leave', 'value': '('+vacation_days+') days paid leave, as per Kuwait Labor Law (Private Sector)'});
  terms_list.push({'offer_term': 'Probation Period', 'value': '(100) working days'});
  set_offer_terms(frm, terms_list);
};

var set_offer_terms = function(frm, terms_list) {
  frm.clear_table('offer_terms');
  terms_list.forEach((item) => {
    let offer_term = frappe.model.add_child(frm.doc, 'Job Offer Term', 'offer_terms');
    frappe.model.set_value(offer_term.doctype, offer_term.name, 'offer_term', item['offer_term']);
    frappe.model.set_value(offer_term.doctype, offer_term.name, 'value', item['value']);
  });
  frm.refresh_field('offer_terms');
}
