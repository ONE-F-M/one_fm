// Copyright (c) 2021, ONEFM and Contributors
// License: GNU General Public License v3. See license.txt

var TOTAL_COMPANY_NO = 0;
var PROMOTIONS_IN_COMPANY = {};
$(document).ready(function() {
  new career_history();
});

// Career History
career_history = Class.extend({
  init: function(){
    this.create_company_section_html(1)
    this.submit_career_history();
  },
  on_change_promotion: function(company_no, promotion_no) {
    var me = this;
    $(`.promotion_select_${company_no}${promotion_no}`).on("change", function(){
      var promotion_select = $(`.promotion_select_${company_no}${promotion_no}`).val()
      var promotion_details_html = "";
      var promotion_details_next_job_title_html = `<div class="my-5 col-lg-6 col-md-6">
          <label class="form-label">So, tell us what position you got promoted to first.</label>
          <input type="text" class="form-control position_${company_no}${promotion_no}" placeholder="Enter Your New Job Title"/>
        </div>`;
      var promotion_details_salary_html = `<div class="my-5 col-lg-6 col-md-6">
          <label class="form-label">How much was your incremented salary in KWD?</label>
          <input type="text" class="form-control salary_${company_no}${promotion_no}" placeholder="Enter your increased Salary in KWD"/>
        </div>`;
      var promotion_details_promotion_date_html = `<div class="my-5 col-lg-6 col-md-6">
          <label class="form-label">When did you get promoted?</label>
          <input type="date" class="form-control date_of_promotion_${company_no}${promotion_no}"/>
        </div>`;

      /*
        Got any Promotion or Salary Increase
        value="0" if selected 'No, I did not get any promotion or salary increase'
        value="1" if selected 'Yes, I Got a Promotion with a Salary Increase'
        value="2" if selected 'Yes, I only got a promotion'
        value="3" if selected 'Yes, Only Got a Salary Increase'
      */
      if(promotion_select == 1){
        promotion_details_html = promotion_details_next_job_title_html+promotion_details_salary_html+promotion_details_promotion_date_html;
      }
      else if(promotion_select == 2){
        promotion_details_html = promotion_details_next_job_title_html+promotion_details_promotion_date_html;
      }
      else if(promotion_select == 3){
        promotion_details_html = promotion_details_salary_html+promotion_details_promotion_date_html;
      }
      $(`.promotion_details_section_${company_no}${promotion_no}`).empty();
      $(`.promotion_details_section_${company_no}${promotion_no}`).append(promotion_details_html);
      if(promotion_select > 0){
        me.set_promotion_section_html(company_no, promotion_no+1)
        PROMOTIONS_IN_COMPANY[company_no] = promotion_no+1;
      }
      else{
        var max_promotion = PROMOTIONS_IN_COMPANY[company_no];
        for (let i = promotion_no; i <= max_promotion; i++) {
          $(`.promotion_section_${company_no}${(i+1).toString()}`).remove();
          $(`.promotion_details_section_${company_no}${(i+1).toString()}`).remove();
        }
        PROMOTIONS_IN_COMPANY[company_no] = promotion_no;
      }
    });
  },
  set_promotion_section_html: function(company_no, promotion_no) {
    var next_promotion_details_html = `<div class="col-lg-12 col-md-12 promotion_section_${company_no}${promotion_no}">
        <label  class="form-label">Did you get any promotion or salary increase?</label>
          <select class="custom-select promotion_select_${company_no}${promotion_no}">
            <option value="0">No, I did not get any promotion or salary increase</option>
            <option value="1">Yes, I got a promotion with a salary increase</option>
            <option value="2">Yes, I only got a promotion</option>
            <option value="3">Yes, I only got a salary increase</option>
          </select>
        <div class="row col-lg-12 col-md-12 my-5 promotion_details_section_${company_no}${promotion_no}" style="width: 100%; display: flex">
        </div>
      </div>`;
    $(`.promotion_section_${company_no}${promotion_no}`).remove();
    $(`.promotion_details_section_${company_no}${promotion_no}`).remove();
    $(`.promotion_section_${company_no}`).append(next_promotion_details_html);
    this.on_change_promotion(company_no, promotion_no);
  },
  on_change_still_working_on_same_company: function(company_no) {
    var me = this;
    $(".still_working_on_same_company_"+(company_no.toString())).on("change", function(){
      var still_working = $(".still_working_on_same_company_"+(company_no.toString())).val();
      $(".reason_why_leave_job_"+(company_no.toString())).remove();
      $(".are_you_still_working_"+(company_no.toString())).remove();
      $(".when_did_you_left_"+(company_no.toString())).remove();
      if (still_working == 1){
        var reason_why_leave_job_html = `<div class="col-lg-12 col-md-12 reason_why_leave_job_${company_no}">
          <label class="form-label">Why do you plan to leave the job?</label>
          <textarea rows="4" cols="50" name="comment" form="usrform" class="form-control reason_why_leave_job_${company_no}_text">
          </textarea>
        </div>`;
        $(".company_"+(company_no.toString())).append(reason_why_leave_job_html);
      }
      else if(still_working == 2){
        me.when_did_you_left_the_company(company_no);
        me.are_you_still_working_html(company_no);
      }
    });
  },
  are_you_still_working_html: function(company_no) {
    var are_you_still_working_html = `<div class="col-lg-12 col-md-12 are_you_still_working_${company_no}">
      <label  class="form-label">Are you still working?</label>
      <select class="custom-select are_you_still_working_${company_no}_select">
        <option value="0">Choose</option>
        <option value="1">No</option>
        <option value="2">Yes</option>
      </select>
    </div>`
    $(".company_"+(company_no.toString())).append(are_you_still_working_html);
    this.on_change_are_you_still_working(company_no)
  },
  when_did_you_left_the_company: function(company_no) {
    var when_did_you_left_the_company_html = `<div class="col-lg-12 col-md-12 when_did_you_left_${company_no}">
      <label  class="form-label">When did you leave the company?</label>
      <input type="date" class="form-control when_did_you_left_${company_no}_date"/>
    </div>`
    $(".company_"+(company_no.toString())).append(when_did_you_left_the_company_html);
  },
  on_change_are_you_still_working: function(company_no) {
    var me = this;
    $(`.are_you_still_working_${company_no}_select`).on("change", function(){
      var are_you_still_working = $(`.are_you_still_working_${company_no}_select`).val();
      if(are_you_still_working == 2){
        me.create_company_section_html(company_no+1);
      }
      else if(are_you_still_working <= 1){
        for (let i = company_no; i < TOTAL_COMPANY_NO; i++) {
          $(".company_"+((i+1).toString())).remove();
        }
        TOTAL_COMPANY_NO = company_no;
      }
    });
  },
  create_company_section_html: function(company_no) {
    var company_section_html = `<div class="row col-lg-12 col-md-12 mb-12 company_${company_no}">
      <h3>So {{job_applicant.applicant_name}}, tell us about the ${stringifyNumber(company_no)} company you worked for!</h3>
      <div class="my-5 col-lg-6 col-md-6">
        <label class="form-label">${stringifyNumber(company_no)} Company Name </label>
        <input type="text" class="form-control company_${company_no}_name" placeholder="Enter the ${stringifyNumber(company_no)} Company Name"/>
      </div>
      <div class="my-5 col-lg-6 col-md-6">
        <label class="form-label">Select country of employment</label> <br>
        <select class="form-control country_of_company_${company_no}">
          <option>Select Country</option>
          {% for country in country_list %}
          <option>{{country.name}}</option>
          {% endfor %}
        </select>
      </div>
      <div class="mb-3 col-lg-6 col-md-6">
        <label class="form-label">When did you join the company?</label>
        <input type="date" class="form-control joined_company${company_no}"/>
      </div>
      <div class="mb-3 col-lg-6 col-md-6">
        <label class="form-label">What was your first salary at this company?</label>
        <input type="text" class="form-control salary_company${company_no}" placeholder="Enter your Salary in KWD"/>
      </div>

      <div class="col-lg-12 col-md-12">
        <label for="Responisbilities" class="form-label">What were your top three responsibilities?</label>
        <input type="text" class="form-control mb-3 responisbility_1_company${company_no}" placeholder="1"/>
        <input type="text" class="form-control mb-3 responisbility_2_company${company_no}" placeholder="2"/>
        <input type="text" class="form-control mb-3 responisbility_3_company${company_no}" placeholder="3"/>
      </div>

      <div class="col-lg-12 col-md-12">
        <hr class="my-5"/>
      </div>

      <div class="mb-3 col-lg-6 col-md-6">
        <label  class="form-label">What was your starting job title?</label>
        <input type="text" class="form-control starting_job_title_company_${company_no}" placeholder="Enter the Job Title"/>
      </div>

      <div class="promotion_section_${company_no}" style="width: 100%">

      </div>

      <div class="col-lg-12 col-md-12 mb-3">
        <label>Are You still working for the same company?</label>
        <select class="custom-select still_working_on_same_company_${company_no}">
          <option value="0">Choose</option>
          <option value="1">Yes</option>
          <option value="2">No</option>
        </select>
      </div>
      </div>`;
    $(".main_section").append(company_section_html);
    TOTAL_COMPANY_NO += 1;
    this.set_promotion_section_html(company_no, 1);
    this.on_change_still_working_on_same_company(company_no);
  },
  submit_career_history: function() {
    // Submit Career History
    var me = this;
    $('.btn-submit-career-history').click(function(){
      var data = me.get_details_from_form();
      // POST Career History if all the conditions are satisfied
      if ($('#job_applicant').attr("data") && data.length > 0){
        frappe.freeze();
        frappe.call({
          type: "POST",
          method: "one_fm.templates.pages.career_history.create_career_history_from_portal",
          args: {
            job_applicant: $('#job_applicant').attr("data"),
            career_history_details: data
          },
          btn: this,
          callback: function(r){
            frappe.unfreeze();
            frappe.msgprint(frappe._("Successfully submitted your career history. Our HR team will be responding to you soon."));
            if(r.message){
              window.location.href = "/career_history";
            }
          }
        });
      }
      else{
        frappe.msgprint(frappe._("Please fill all the details to submit the career history."));
      }
    });
  },
  get_details_from_form: function() {
    var career_histories = [];
    for (let company_no = 1; company_no <= TOTAL_COMPANY_NO; company_no++) {
      var career_history = {};
      career_history['company_name'] = $(`.company_${company_no}_name`).val();
      career_history['country_of_employment'] = $(`.country_of_company_${company_no}`).val();
      career_history['start_date'] = $(`.joined_company${company_no}`).val();
      career_history['monthly_salary_in_kwd'] = $(`.salary_company${company_no}`).val();
      career_history['responsibility_one'] = $(`.responisbility_1_company${company_no}`).val();
      career_history['responsibility_two'] = $(`.responisbility_2_company${company_no}`).val();
      career_history['responsibility_three'] = $(`.responisbility_3_company${company_no}`).val();
      career_history['job_title'] = $(`.starting_job_title_company_${company_no}`).val();

      /*
        Still working in same company
        value="1" if selected 'Yes'
        value="2" if selected 'No'
      */
      if($(`.still_working_on_same_company_${company_no}`).val() == 1){
        career_history['reason_for_leaving_job'] = $(`.reason_why_leave_job_${company_no}_text`).val();
      }
      else{
        career_history['left_the_company'] = $(`.when_did_you_left_${company_no}_date`).val();
      }

      // Set Promotion Details
      var max_promotion = PROMOTIONS_IN_COMPANY[company_no];
      var promotions = [];
      for (let promotion_no = 1; promotion_no <= max_promotion; promotion_no++) {
        var promotion = {};
        /*
        Got any Promotion or Salary Increase
        value="0" if selected 'No, I did not get any promotion or salary increase'
        value="1" if selected 'Yes, I Got a Promotion with a Salary Increase'
        value="2" if selected 'Yes, Only Got a Promotion'
        value="3" if selected 'Yes, Only Got a Salary Increase'
        */
        var got_promoted = $(`.promotion_select_${company_no}${promotion_no}`).val();
        if(got_promoted > 0){
          promotion['start_date'] = $(`.date_of_promotion_${company_no}${promotion_no}`).val();
        }
        if(got_promoted == 1){
          promotion['job_title'] = $(`.position_${company_no}${promotion_no}`).val();
          promotion['monthly_salary_in_kwd'] = $(`.salary_${company_no}${promotion_no}`).val();
        }
        else if(got_promoted == 2){
          promotion['job_title'] = $(`.position_${company_no}${promotion_no}`).val();
        }
        else if(got_promoted == 3){
          promotion['monthly_salary_in_kwd'] = $(`.salary_${company_no}${promotion_no}`).val();
        }
        promotions.push(promotion);
      }
      career_history['promotions'] = promotions;

      career_histories.push(career_history);
    }
    return career_histories;
  }
});

function stringifyNumber(n) {
	var special = ['Zeroth', 'First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth', 'Tenth', 'Eleventh', 'Twelfth', 'Thirteenth', 'Fourteenth', 'Fifteenth', 'Sixteenth', 'Seventeenth', 'Eighteenth', 'Nineteenth'];
	var deca = ['Twent', 'Thirt', 'Fort', 'Fift', 'Sixt', 'Sevent', 'Eight', 'Ninet'];
  if (n < 20) return special[n];
  if (n % 10 === 0) return deca[Math.floor(n / 10) - 2] + 'ieth';
  return deca[Math.floor(n / 10) - 2] + 'y-' + special[n % 10];
}
