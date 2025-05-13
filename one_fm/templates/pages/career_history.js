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
    var me = this;
    $('.submit-btn').hide();
    $('.next-btn').hide();
    $('.main_section').hide();
    $('.back-btn').hide();

    this.intro_btn(me);
    this.introduction();

    this.submit_career_history();
  },
  introduction:function(){
    var intro_section_html = `
    <h4 id="job_applicant" data="{{ job_applicant.name }}">Hey {{job_applicant.applicant_name}},
    you’re applying for the {{job_applicant.designation}} position.</h4>
    <h4>We would like to know more about you.</h4>
    <h5>Give us some details about your career, and tell us how great you are!</h5>
  `
    $(".intro").append(intro_section_html);
    const pageContentWrapper = document.querySelector('.page-content-wrapper');
    pageContentWrapper.style.position = 'relative';
  },
  on_change_promotion: function(company_no, promotion_no) {
    var me = this;
    $(`.promotion_select_${company_no}${promotion_no}`).on("change", function(){
      var promotion_select = $(`.promotion_select_${company_no}${promotion_no}`).val();
      var promotion_details_html = "";
      var promotion_details_next_job_title_html = `<div class="my-5 col-lg-12 col-md-12">
          <label class="form-label">So, tell us what position you got promoted to first.</label>
          <input type="text" class="form-control position_${company_no}${promotion_no}" placeholder="Enter Your New Job Title"/>
        </div>`;
      var promotion_details_salary_html = `<div class="my-5 col-lg-12 col-md-12">
          <label class="form-label">How much was your incremented salary in KWD?</label>
          <input type="text" class="form-control salary_${company_no}${promotion_no}" placeholder="Enter your increased Salary in KWD"/>
        </div>`;
      var promotion_details_promotion_date_html = `<div class="my-5 col-lg-12 col-md-12">
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
    var next_promotion_details_html = `<div class="mx-auto col-lg-12 col-md-12 mb-12 promotion_section_${company_no}${promotion_no}">
        <label  class="form-label">${promotion_no>1 ?
            'So {{job_applicant.applicant_name}}, after your promotion/salary increase did you get another promotion or salary increase?':
            'Did you get any promotion or salary increase?'}</label>
          <select class="custom-select promotion_select_${company_no}${promotion_no}">
            <option value="0">No, I did not get any promotion or salary increase</option>
            <option value="1">Yes, I got a promotion with a salary increase</option>
            <option value="2">Yes, I only got a promotion</option>
            <option value="3">Yes, I only got a salary increase</option>
          </select>
        <div class="row mx-auto col-lg-12 col-md-12 mb-12 promotion_details_section_${company_no}${promotion_no}" style="width: 100%; display: flex">
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
      $(".factors_in_new_job_"+(company_no.toString())).remove();
      $(".are_you_still_working_"+(company_no.toString())).remove();
      $(".when_did_you_left_"+(company_no.toString())).remove();
      if (still_working == 1){
        var reason_why_leave_job_html = `<div class="mx-auto col-lg-12 col-md-12 mb-3 reason_why_leave_job_${company_no}">
          <label class="form-label">Why do you plan to leave the job?</label>
          <textarea rows="4" cols="50" name="comment" form="usrform" class="form-control reason_why_leave_job_${company_no}_text"></textarea>
        </div>`;
        var factors_in_new_job = `<div class="mx-auto col-lg-12 col-md-12 factors_in_new_job_${company_no}">
          <label class="form-label">What are the factors you are looking for in a new job?</label>
          <textarea rows="4" cols="50" name="comment" form="usrform" class="form-control factors_in_new_job_${company_no}_text"></textarea>
        </div>`;
        $(".company_"+(company_no.toString())).append(reason_why_leave_job_html);
        $(".company_"+(company_no.toString())).append(factors_in_new_job);
        me.show_final_interest_step(company_no.toString());
        $('.submit-btn').fadeIn();
      }
      else if(still_working == 2){
        me.when_did_you_left_the_company(company_no);
        me.are_you_still_working_html(company_no);
        $('.final-interest-section').remove();
        $('.submit-btn').fadeOut();
      }
      else if(still_working == 0){
        $('.final-interest-section').remove();
        $('.submit-btn').fadeOut();
      }
    });
  },
  are_you_still_working_html: function(company_no) {
    var are_you_still_working_html = `<div class="row mx-auto col-lg-12 col-md-12 mb-3 are_you_still_working_${company_no}">
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
    var when_did_you_left_the_company_html = `<div class="row mx-auto col-lg-12 col-md-12 mt-5 mb-12 when_did_you_left_${company_no}">
      <label  class="form-label">When did you leave the company?<span style="color: red">*</span></label>
      <input type="date" class="form-control when_did_you_left_${company_no}_date"/>
    </div>`
    $(".company_"+(company_no.toString())).append(when_did_you_left_the_company_html);
  },
  on_change_are_you_still_working: function(company_no) {
    var me = this;
    $(`.are_you_still_working_${company_no}_select`).on("change", function(){
      var are_you_still_working = $(`.are_you_still_working_${company_no}_select`).val();
      $(".factors_in_new_job_"+(company_no.toString())).remove();
      if(are_you_still_working == 2){
        $('.final-interest-section').remove();
        $('.submit-btn').fadeOut();
        $('.next-btn').fadeIn();
        me.next_career_history(company_no+1);
      }
      else if(are_you_still_working == 0){
        $('.final-interest-section').remove();
        $('.next-btn').fadeOut();
        $('.submit-btn').fadeOut();
      }
      else if(are_you_still_working == 1){
        var factors_in_new_job = `<div class="mx-auto col-lg-12 col-md-12 factors_in_new_job_${company_no}">
          <label class="form-label">What are the factors you are looking for in a new job?</label>
          <textarea rows="4" cols="50" name="comment" form="usrform" class="form-control factors_in_new_job_${company_no}_text"></textarea>
        </div>`;
        $('.next-btn').fadeOut();
        $(".company_"+(company_no.toString())).append(factors_in_new_job);
        $('.submit-btn').fadeIn();
        for (let i = company_no; i < TOTAL_COMPANY_NO; i++) {
          $(".company_"+((i+1).toString())).remove();

        }
        TOTAL_COMPANY_NO = company_no;
        me.show_final_interest_step(TOTAL_COMPANY_NO);
      }
    });
  },
  
  show_final_interest_step: function(TOTAL_COMPANY_NO) {
    $('.final-interest-section').remove();
        var interestSection = $(`
            <div class="row mx-auto col-lg-12 col-md-12 mb-3 final-interest-section">
                <div class="col-lg-12 col-md-12 mb-3">
                    <label class="form-label">What makes you interested in this opportunity?</label>
                    <textarea rows="4" cols="50" 
                        name="interest_reason" 
                        class="form-control what_make_your_interested_in_this_opportunity"
                        required></textarea>
                </div>
            </div>
        `);

        $('.section_' + (TOTAL_COMPANY_NO)).after(interestSection);
  },

  create_company_section_html: function(company_no) {
    $('.main_section').delay(400).fadeIn();
    if(company_no>=2){
      $('.back-btn').fadeIn();
      this.back_career_history(company_no);
    }
    var company_section_html = `
    <div class="section_${company_no}">
    <h3 class="mx-auto">Hello, {{job_applicant.applicant_name}}, tell us about the ${stringifyNumber(company_no)} company you worked for!</h3>
    <div class="row mx-auto col-lg-12 col-md-12 mb-3 company_${company_no} border-top">
        <div class="my-3 col-lg-12 col-md-12">
        <label class="form-label">What was the company's name? </label>
        <input type="text" class="form-control company_${company_no}_name" placeholder="Enter the ${stringifyNumber(company_no)} Company Name"/>
        </div>

        <div class="my-3 col-lg-12 col-md-12">
        <label class="form-label">Which country did you get employed in?</label> <br>
          <select class="form-control country_of_company_${company_no}">
          <option>Select Country</option>
          {% for country in country_list %}
          <option>{{country.name}}</option>
          {% endfor %}
        </select>
        </div>
        <div class="mb-3 col-lg-12 col-md-12">
        <label class="form-label">When did you join the company?</label>
        <input type="date" class="form-control joined_company${company_no}"/>
        </div>

        <div class="mb-3 col-lg-12 col-md-12">
        <label class="form-label">What was your first salary at this company?</label>
        <input type="text" class="form-control salary_company${company_no}" placeholder="Enter your Salary in KWD"/>
        </div>

      <div class="col-lg-12 col-md-12">
        <hr class="my-5"/>
      </div>

      <div class="mb-3 col-lg-12 col-md-12">
        <label  class="form-label">What was your starting job title?</label>
        <input type="text" class="form-control starting_job_title_company_${company_no}" placeholder="Enter the Job Title"/>
      </div>


     <div class="col-lg-12 col-md-12 mb-3">
        <label class="form-label">What was your employment type?</label>
        <select class="custom-select employment_type_company_${company_no}">
        <option value="" disabled selected>Select Employment Type</option>
          {% for type in employment_type_list %}
          <option value="{{ type }}">{{ type }}</option>
          {% endfor %}
        </select>
      </div>



      <div class="mb-3 col-lg-12 col-md-12">
        <label class="form-label">Briefly describe your responsibilities in this role</label>
        <textarea class="form-control responsibilities_company_${company_no}" rows="4" placeholder="E.g. Managed a team of 5, handled client reports, etc."></textarea>
      </div>


      <div class="mt-5 promotion_section_${company_no}" style="width: 100%">

      </div>

      <div class="col-lg-12 col-md-12 mb-3">
        <label>Tell us about contact person details from ${stringifyNumber(company_no)} company you worked!</label>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Full name</label>
        <input type="text" class="form-control first_contact_name_${company_no}" placeholder="Full Name"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Email</label>
        <input type="text" class="form-control first_contact_email_${company_no}" placeholder="Email"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Designation</label>
        <input type="text" class="form-control first_contact_designation_${company_no}" placeholder="Designation"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Phone number with country code</label>
        <input type="text" class="form-control first_contact_phone_${company_no}" placeholder="Phone number with country code"/>
      </div>
      <div class="col-lg-12 col-md-12 mb-3 add_more_contact_${company_no}">
        <button class="btn btn-dark float-left btn_add_more_contact_${company_no}" type="button">{{ _(" + Add more contact person") }}</button>
      </div>
      <div class="col-lg-12 col-md-12 mb-3">
        <label>Tell us some details about your best boss from ${stringifyNumber(company_no)} company you worked</label>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Full name</label>
        <input type="text" class="form-control best_boss_name_${company_no}" placeholder="Full Name"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Email</label>
        <input type="text" class="form-control best_boss_email_${company_no}" placeholder="Email"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Phone number with country code</label>
        <input type="text" class="form-control best_boss_phone_${company_no}" placeholder="Phone number with country code"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Why is He/She the best?</label>
        <input type="text" class="form-control why_best_boss${company_no}" placeholder="Why is he/she the best?"/>
      </div>

       <div class="col-lg-12 col-md-12 mb-3 mt-5" style="width: 100%">
        <label> Tell us some details about your best colleague from ${stringifyNumber(company_no)} company you worked</label>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Full name</label>
        <input type="text" class="form-control best_colleague_name_${company_no}" placeholder="Full Name"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Email</label>
        <input type="text" class="form-control best_colleague_email_${company_no}" placeholder="Email"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Phone number with country code</label>
        <input type="text" class="form-control best_colleague_phone_${company_no}" placeholder="Phone number with country code"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>Why is He/She the best?</label>
        <input type="text" class="form-control why_best_colleague${company_no}" placeholder="Why is he/she the best?"/>
      </div>
      <div class="col-lg-12 col-md-12 mb-3">
        <label>Are you still working for the same company?</label>
        <select class="custom-select still_working_on_same_company_${company_no}">
        <option value="0">Choose</option>
        <option value="1">Yes</option>
        <option value="2">No</option>
        </select>
      </div>
  </div>

  </div>`;
    $(".main_section").append(company_section_html);
    TOTAL_COMPANY_NO += 1;
    this.set_promotion_section_html(company_no, 1);
    this.on_change_still_working_on_same_company(company_no);
    this.on_click_add_more_contact_person(company_no);
  },
  on_click_add_more_contact_person: function(company_no) {
    var company_contact_html = `
      <div class="col-lg-6 col-md-6 mb-3">
        <label>What is name of the second contact person?</label>
        <input type="text" class="form-control second_contact_name_${company_no}" placeholder="Full Name"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>What is the Email of the second contact person?</label>
        <input type="text" class="form-control second_contact_email_${company_no}" placeholder="Email"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>What is designation of the second contact person?</label>
        <input type="text" class="form-control second_contact_designation_${company_no}" placeholder="Designation"/>
      </div>
      <div class="col-lg-6 col-md-6 mb-3">
        <label>What is the phone number of the second contact person?</label>
        <input type="text" class="form-control second_contact_phone_${company_no}" placeholder="Phone number with country code"/>
      </div>
    `
    $(`.btn_add_more_contact_${company_no}`).click(function(){
      $(`.btn_add_more_contact_${company_no}`).fadeOut();
      $(company_contact_html).insertAfter(`.add_more_contact_${company_no}`);
    });
  },
  next_career_history: function(company_no) {
    // Move to Next Career History
    var me = this;
    $('.btn-next-career-history').click(function(){
      $(`.section_${company_no-1}`).fadeOut();
      $('.next-btn').fadeOut();
      if($(`.section_${company_no}`).length){
        $(`.section_${company_no}`).delay(400).fadeIn();
      }
      else{
        me.create_company_section_html(company_no);
      }

    });
  },
  back_career_history: function(company_no) {
    // Move to Next Career History
    var me = this;
    $('.btn-back-career-history').click(function(){
      $(`.section_${company_no}`).fadeOut();
      $(`.section_${company_no-1}`).fadeIn();
      $('.next-btn').fadeIn();
      me.next_career_history(company_no);
    });
  },
  submit_career_history: function() {
    // Submit Career History
    var me = this;
    $('.btn-submit-career-history').click(function(){
      var {career_histories, interest_reason} = me.get_details_from_form();
      var all_best_references = me.get_all_best_references();
      if(!validateBestReferencesAndColleague(all_best_references)){
        return frappe.msgprint(frappe._("Kindly fill the best reference for the most recent job"));
      }

      if(!validateResponsibilities(career_histories)){
        return frappe.msgprint(frappe._("Kindly fill the responsibility for the most recent job"));
      }
      // POST Career History if all the conditions are satisfied
      if ($('#job_applicant').attr("data") && career_histories.length > 0){
        frappe.freeze();
        frappe.call({
          type: "POST",
          method: "one_fm.templates.pages.career_history.create_recruitment_documents",
          args: {
            job_applicant: $('#job_applicant').attr("data"),
            career_history_details: career_histories,
            best_references: all_best_references,
            interest_reason: interest_reason
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
  intro_btn: function(me) {
    // Create Comapany Section
    $('.btn-intro-next').click(function(){
      $('.intro_section').fadeOut();
       me.create_company_section_html(1)
    });
  },
  get_all_best_references: function() {
    var all_best_references = [];
    for (let company_no = 1; company_no <= TOTAL_COMPANY_NO; company_no++) {
      var best_references = {};
      best_references['best_boss_name'] = $(`.best_boss_name_${company_no}`).val();
      best_references['best_boss_email'] = $(`.best_boss_email_${company_no}`).val();
      best_references['best_boss_phone'] = $(`.best_boss_phone_${company_no}`).val();
      best_references['why_best_boss'] = $(`.why_best_boss${company_no}`).val();

      best_references['best_colleague_name'] = $(`.best_colleague_name_${company_no}`).val();
      best_references['best_colleague_email'] = $(`.best_colleague_email_${company_no}`).val();
      best_references['best_colleague_phone'] = $(`.best_colleague_phone_${company_no}`).val();
      best_references['best_colleague_designation'] = $(`.best_colleague_designation_${company_no}`).val();
      best_references['why_best_colleague'] = $(`.why_best_colleague${company_no}`).val();

      all_best_references.push(best_references);
    }
    return all_best_references;
  },
  get_details_from_form: function() {
    var career_histories = [];
    
    for (let company_no = 1; company_no <= TOTAL_COMPANY_NO; company_no++) {
      var career_history = {};
      
      career_history['company_name'] = $(`.company_${company_no}_name`).val();
      career_history['country_of_employment'] = $(`.country_of_company_${company_no}`).val();
      career_history['start_date'] = $(`.joined_company${company_no}`).val();
      career_history['monthly_salary_in_kwd'] = $(`.salary_company${company_no}`).val();
      career_history['responsibility_one'] = $(`.responsibilities_company_${company_no}`).val();
      career_history['job_title'] = $(`.starting_job_title_company_${company_no}`).val();
      career_history['employment_type'] = $(`.employment_type_company_${company_no}`).val();

      career_history['first_contact_name'] = $(`.first_contact_name_${company_no}`).val();
      career_history['first_contact_email'] = $(`.first_contact_email_${company_no}`).val();
      career_history['first_contact_phone'] = $(`.first_contact_phone_${company_no}`).val();
      career_history['first_contact_designation'] = $(`.first_contact_designation_${company_no}`).val();

      career_history['second_contact_name'] = $(`.second_contact_name_${company_no}`).val();
      career_history['second_contact_email'] = $(`.second_contact_email_${company_no}`).val();
      career_history['second_contact_phone'] = $(`.second_contact_phone_${company_no}`).val();
      career_history['second_contact_designation'] = $(`.second_contact_designation_${company_no}`).val(); 
      

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
        if(validateEndDate(career_history['left_the_company'])){
          return frappe.msgprint(frappe._("Kindly fill the when did you left the company field"));
        }
      }
      career_history['factors_in_new_job'] = $(`.factors_in_new_job_${company_no}_text`).val();

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
    let interest_reason = $('[name="interest_reason"]').val();
    return {career_histories, interest_reason};
  }
});

function stringifyNumber(n) {
  var special = ['Zeroth', 'First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth', 'Tenth', 'Eleventh', 'Twelfth', 'Thirteenth', 'Fourteenth', 'Fifteenth', 'Sixteenth', 'Seventeenth', 'Eighteenth', 'Nineteenth'];
  var deca = ['Twent', 'Thirt', 'Fort', 'Fift', 'Sixt', 'Sevent', 'Eight', 'Ninet'];
  if (n < 20) return special[n];
  if (n % 10 === 0) return deca[Math.floor(n / 10) - 2] + 'ieth';
  return deca[Math.floor(n / 10) - 2] + 'y-' + special[n % 10];
}


function validateResponsibilities(data) {
  if (data.length === 0) {
    return true;
  }
  
  const lastObject = data[data.length - 1];
  return lastObject.responsibility_one !== undefined 
    && lastObject.responsibility_one !== null 
    && lastObject.responsibility_one.trim() !== '';
}

function validateEndDate(data){
  return !data;
}

function validateBestReferencesAndColleague(data) {
  if (data.length === 0) {
    return true;
  }
  const lastObject = data[data.length - 1];
  const isBossValid = lastObject.best_boss_name && lastObject.best_boss_name.trim() !== '';
  const isColleagueValid = lastObject.best_colleague_name && lastObject.best_colleague_name.trim() !== '';

  return isBossValid && isColleagueValid;

  }
