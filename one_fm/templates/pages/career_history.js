// Copyright (c) 2021, ONEFM and Contributors
// License: GNU General Public License v3. See license.txt

var TOTAL_COMPANY_NO = 0;
var PROMOTIONS_IN_COMPANY = {};
$(document).ready(function() {
  new career_history();
});

// Career History

var DEFAULT_RANKED_FACTORS = [
    "Projects & Technology",
    "Manager & Teams",
    "Compensation",
    "Continuing Growth Rate",
    "Job Stretch & Learning",
    "Work/Life Balance",
    "Company Mission & Values (optional addition)"
];

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
        $(".company_details_"+(company_no.toString())).append(reason_why_leave_job_html);
        $(".company_details_"+(company_no.toString())).append(factors_in_new_job);
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
    $(".company_details_"+(company_no.toString())).append(are_you_still_working_html);
    this.on_change_are_you_still_working(company_no)
  },
  when_did_you_left_the_company: function(company_no) {
    var when_did_you_left_the_company_html = `<div class="row mx-auto col-lg-12 col-md-12 mt-5 mb-12 when_did_you_left_${company_no}">
      <label  class="form-label">When did you leave the company?<span style="color: red">*</span></label>
      <input type="date" class="form-control when_did_you_left_${company_no}_date"/>
    </div>`
    $(".company_details_"+(company_no.toString())).append(when_did_you_left_the_company_html);
  },
  on_change_are_you_still_working: function(company_no) {
    var me = this;
    $(`.are_you_still_working_${company_no}_select`).on("change", function(){
      var are_you_still_working = $(`.are_you_still_working_${company_no}_select`).val();
      $(".factors_in_new_job_"+(company_no.toString())).remove();
      $(".shoves-tugs-block").remove();
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
        $(".company_details_"+(company_no.toString())).append(factors_in_new_job);
        $(".company_details_"+(company_no.toString())).append(get_shoves_tugs_html(company_no));
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
      // Remove existing sections to prevent duplicates if this function is called multiple times.
      // Be cautious with this selector if 'final-interest-section' elements are meant to persist.
      // If the table is part of what should be removed and re-added, this is fine.
      $('.final-interest-section').remove();

      var interestSection = $(`
          <div class="row mx-auto col-lg-12 col-md-12 mb-3 final-interest-section">
              <div class="col-lg-12 col-md-12 mb-3">
                  <label class="form-label">Which career factors are most important to you?<span style="color: red">*</span></label>
                  <h6>Instructions for Candidate:</h6>
                  <ul style="font-size: smaller; font-weight: bold;">
                      <li>Think about what really drives your career decisions.</li>
                      <li>Please drag and drop the rows in the table below to rank the career factors from 1 (most important) to 7 (least important) based on what matters most to you.</li>
                      <li>There are no right or wrong answers — your response helps us understand how to align the role with your career goals.</li>
                  </ul>
                  <table class="min-w-full bg-white border border-gray-200 rounded-lg overflow-hidden sortable-table" name="rank_and_factors">
                      <thead class="bg-gray-50">
                          <tr>
                              <th class="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rank</th>
                              <th class="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Factor</th>
                              <th class="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                          </tr>
                      </thead>
                      <tbody id="sortableRows" class="divide-y divide-gray-200">
                          <!-- Corrected: Each row needs its own <tr> tag -->
                          <tr class="hover:bg-gray-50 transition-colors duration-150 ease-in-out">
                              <td class="py-4 px-6 whitespace-nowrap text-sm font-medium text-gray-900 rank-cell">1</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Projects & Technology</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">A mix of more satisfying and engaging work</td>
                          </tr>
                          <tr class="hover:bg-gray-50 transition-colors duration-150 ease-in-out">
                              <td class="py-4 px-6 whitespace-nowrap text-sm font-medium text-gray-900 rank-cell">2</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Manager & Teams</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Working with the right types of people and leaders</td>
                          </tr>
                          <tr class="hover:bg-gray-50 transition-colors duration-150 ease-in-out">
                              <td class="py-4 px-6 whitespace-nowrap text-sm font-medium text-gray-900 rank-cell">3</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Compensation</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Total rewards including salary, benefits, and bonuses</td>
                          </tr>
                          <tr class="hover:bg-gray-50 transition-colors duration-150 ease-in-out">
                              <td class="py-4 px-6 whitespace-nowrap text-sm font-medium text-gray-900 rank-cell">4</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Continuing Growth Rate</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Long-term career advancement and opportunity</td>
                          </tr>
                          <tr class="hover:bg-gray-50 transition-colors duration-150 ease-in-out">
                              <td class="py-4 px-6 whitespace-nowrap text-sm font-medium text-gray-900 rank-cell">5</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Job Stretch & Learning</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Bigger challenges, scope, and learning potential</td>
                          </tr>
                          <tr class="hover:bg-gray-50 transition-colors duration-150 ease-in-out">
                              <td class="py-4 px-6 whitespace-nowrap text-sm font-medium text-gray-900 rank-cell">6</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Work/Life Balance</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Time and flexibility for personal life and well-being</td>
                          </tr>
                          <tr class="hover:bg-gray-50 transition-colors duration-150 ease-in-out">
                              <td class="py-4 px-6 whitespace-nowrap text-sm font-medium text-gray-900 rank-cell">7</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Company Mission & Values (optional addition)</td>
                              <td class="py-4 px-6 whitespace-nowrap text-sm text-gray-700">Alignment with your personal purpose and values</td>
                          </tr>
                      </tbody>
                  </table>
              </div>
          </div>
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

      // Append the new HTML content to the DOM
      $('.section_' + (TOTAL_COMPANY_NO)).after(interestSection);

      // --- SortableJS Initialization (Corrected) ---
      // Get the tbody element where the rows are located
      const sortableList = document.getElementById('sortableRows');

      // Check if the element exists before initializing SortableJS
      if (sortableList) {
          new Sortable(sortableList, {
              animation: 150, // ms, animation speed moving items when sorting, `0` — no animation
              ghostClass: 'sortable-ghost', // Class name for the drop placeholder
              chosenClass: 'sortable-chosen', // Class name for the chosen item
              dragClass: 'sortable-drag', // Class name for the dragging item
              // handle: '.rank-cell', // Uncomment this if you only want to drag by the rank number cell

              // Callback when an item is dropped
              onEnd: function (evt) {
                  console.log('Item moved:', evt.oldIndex, 'to', evt.newIndex);
                  updateRanks(); // Call function to re-assign ranks after sorting
              }
          });

          // Function to update the rank numbers in the first column
          function updateRanks() {
              // Select all direct <tr> children of the sortable tbody
              Array.from(sortableList.children).forEach(function(row, index) {
                  // Find the cell with the 'rank-cell' class and update its text content
                  const rankCell = row.querySelector('.rank-cell');
                  if (rankCell) {
                      rankCell.textContent = index + 1;
                  }
              });
          }
          updateRanks();

      } else {
          console.error("Element with ID 'sortableRows' not found after appending. SortableJS not initialized.");
      }
      // --- END SortableJS Initialization ---
  },
  create_company_section_html: function(company_no) {
    $('.main_section').delay(400).fadeIn();
    if(company_no>=2){
      $('.back-btn').fadeIn();
      this.back_career_history(company_no);
    }
    var company_section_html = `
    <div class="section_${company_no}">
      <h3 class="mx-auto">Hello, {{job_applicant.applicant_name}}, alone</h3>

      <div
        class="row border-top"
      >
        <div class="my-3 col-lg-12 col-md-12">
          <label class="form-label">Are you a Fresher or Experienced?</label>
          <select class="form-control fresher_experienced_select_${company_no}">
            <option value="" disabled selected>Select</option>
            <option value="Fresher">Fresher</option>
            <option value="Experienced">Experienced</option>
          </select>
        </div>
      </div>

      <div class="row company_details_${company_no}"></div>
    </div>
    `;
    $(".main_section").append(company_section_html);
    TOTAL_COMPANY_NO += 1;
    this.on_change_experience_type(company_no);
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
  // Function to get the current order of factors from the sortable table
  getRankedFactorsData:function() {
      const rankedFactors = [];
      const sortableList = document.getElementById('sortableRows'); // Get the tbody by its ID

      if (sortableList) {
          // Iterate over each table row (<tr>) directly within the sortable tbody
          Array.from(sortableList.children).forEach(function(row, index) {
              // Find the cells containing the factor and description.
              // Based on your HTML: <td>Rank</td> <td>Factor</td> <td>Description</td>
              const factorCell = row.children[1]; // Second td for Factor
              const descriptionCell = row.children[2]; // Third td for Description

              if (factorCell && descriptionCell) {
                  rankedFactors.push({
                      // The rank is simply its current index + 1 in the reordered list
                      rank: index + 1,
                      factor: factorCell.textContent.trim(),
                      description: descriptionCell.textContent.trim()
                  });
              }
          });
      }
      return rankedFactors;
  },
  submit_career_history: function() {
    // Submit Career History
    var me = this;
    $('.btn-submit-career-history').click(function(){
      var formData = me.get_details_from_form();

      var fresher_args = null;
      var exper_args = null;
      var should_submit = false;
      if (formData.fresher_details) {
        // Fresher: build args
        var fresherData = formData.fresher_details;
        var rank_and_factors = fresherData.ranked_factors || [];
        var interest_reason = fresherData.interest_reason;
        var job_applicant = $('#job_applicant').attr("data");
        fresher_args = {
          job_applicant: job_applicant,
          career_history_details: JSON.stringify([fresherData]),
          best_references: JSON.stringify([]),
          interest_reason: interest_reason,
          rank_and_factors: JSON.stringify(rank_and_factors)
        };
        should_submit = !!job_applicant;
      } else {
        var {career_histories, interest_reason} =  formData;
        var rank_and_factors = me.getRankedFactorsData();
        var isDefaultOrder = rank_and_factors.every(function(row, idx) {
              return row.factor === DEFAULT_RANKED_FACTORS[idx];
          });
        if (isDefaultOrder) {
              return frappe.msgprint(frappe._("Please drag and rank the factors according to your preference before submitting."));
          }
        var all_best_references = me.get_all_best_references();
        if(!validateResponsibilities(career_histories)){
          return frappe.msgprint(frappe._("Kindly fill the responsibility for the most recent job"));
        }
        exper_args = {
          job_applicant: $('#job_applicant').attr("data"),
          career_history_details: JSON.stringify(career_histories),
          best_references: JSON.stringify(all_best_references),
          interest_reason: interest_reason,
          rank_and_factors: JSON.stringify(rank_and_factors)
        };
        should_submit = $('#job_applicant').attr("data") && career_histories.length > 0;
      }

      // POST Career History if all the conditions are satisfied
      var args_to_send = fresher_args || exper_args;
      if (should_submit && args_to_send) {
        frappe.freeze();
        frappe.call({
          type: "POST",
          method: "one_fm.templates.pages.career_history.create_recruitment_documents",
          args: args_to_send,
          btn: this,
          callback: function(r){
            frappe.unfreeze();
            frappe.msgprint(frappe._("Successfully submitted your career history. Our HR team will be responding to you soon."));
            if(r.message){
              window.location.href = "/career_history";
            }
          }
        });
      } else {
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
    let fresher_details = null;
    let isFresher = false;
    // Check experience type for each company
    let expType = null;
    for (let company_no = 1; company_no <= TOTAL_COMPANY_NO; company_no++) {
      expType = $(`.fresher_experienced_select_${company_no}`).val();
      if (expType === 'Fresher') {
        isFresher = true;
        // For fresher, check at least one activity type is selected (robust)
        let learning_journey = [];
        // Fix: check for any select with class containing 'activity_type_select_' and a value, regardless of company_no
        let hasActivity = $(".learning-journey-items select").filter(function(){
          return $(this).val() && $(this).attr('class') && $(this).attr('class').indexOf('activity_type_select_') !== -1;
        }).length > 0;
        $(`.learning-journey-items .learning-journey-item`).each(function() {
          // Find the select and input for activity type and title inside this item
          let activityType = $(this).find("select").filter(function(){
            return $(this).attr('class') && $(this).attr('class').indexOf('activity_type_select_') !== -1;
          }).val();
          let activity_title = $(this).find("input").filter(function(){
            return $(this).attr('class') && $(this).attr('class').indexOf('activity_title_') !== -1;
          }).val();
          let questions = [];
          $(this).find("textarea").filter(function(){
            return $(this).attr('class') && $(this).attr('class').indexOf('assessment_question_') !== -1;
          }).each(function() {
            let label = $(this).prev("label").text().trim();
            let answer = $(this).val();
            questions.push({ label: label, answer: answer });
          });
          if (activityType) {
            learning_journey.push({
              activity_type: activityType,
              activity_title: activity_title,
              questions: questions
            });
          }
        });
        if (!hasActivity) {
          frappe.msgprint(frappe._("Please add at least one Learning and Development Activity Type."));
          return {};
        }
        // Collect shoves and tugs
        let shoves = $(`.shoves_input_${company_no}`).val();
        let tugs = $(`.tugs_input_${company_no}`).val();
        // Collect ranked factors
        let ranked_factors = this.getRankedFactorsData ? this.getRankedFactorsData() : [];
        // Collect interest reason
        let interest_reason = $('[name="interest_reason"]').val();
        fresher_details = {
          expType: expType,
          learning_journey: learning_journey,
          shoves: shoves,
          tugs: tugs,
          ranked_factors: ranked_factors,
          interest_reason: interest_reason
        };
        break; // Only one fresher section expected
      }
      // Experienced: run all validations as before
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
      if(!career_history['start_date']){
        frappe.msgprint(frappe._("Kindly fill the date of joining field."));
        return {};
      }
      if($(`.still_working_on_same_company_${company_no}`).val() == 1){
        career_history['reason_for_leaving_job'] = $(`.reason_why_leave_job_${company_no}_text`).val();
      }
      else{
        career_history['left_the_company'] = $(`.when_did_you_left_${company_no}_date`).val();
        if(validateEndDate(career_history['left_the_company'])){
          frappe.msgprint(frappe._("Kindly fill the when did you leave the company field."));
          return false;
        }
      }
      career_history['factors_in_new_job'] = $(`.factors_in_new_job_${company_no}_text`).val();
      var max_promotion = PROMOTIONS_IN_COMPANY[company_no];
      var promotions = [];
      for (let promotion_no = 1; promotion_no <= max_promotion; promotion_no++) {
        var promotion = {};
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
    let project_and_technology = $('[name="project_and_technology"]').val();
    let manager_and_team = $('[name="manager_and_team"]').val();
    let compensation = $('[name="compensation"]').val();
    let continuing_growth_rate = $('[name="continuing_growth_rate"]').val();
    let jobstretch_and_learning = $('[name="jobstretch_and_learning"]').val();
    let work_life_balance = $('[name="work_life_balance"]').val();
    if (isFresher && fresher_details) {
      return { fresher_details, expType };
    }
    return {career_histories, interest_reason, expType, project_and_technology, manager_and_team,compensation,continuing_growth_rate,jobstretch_and_learning,work_life_balance};
  },
  on_change_experience_type: function (company_no) {
    const me = this;
    $(`.fresher_experienced_select_${company_no}`).on('change', function() {
      const selectedExperienceType = $(this).val();
      const companyDetailsElement = $(`.company_details_${company_no}`);
      if (selectedExperienceType === 'Fresher') {
        heading_html = '<h3 class="mx-auto">Hello, {{job_applicant.applicant_name}}, tell us about your learning and development journey!</h3>';
        $(`.section_${company_no} h3.mx-auto`).replaceWith($(heading_html));
         $('.next-btn').remove();
        const fresherDetailsHTML = `
        <div class="learning-journey-block my-3 col-lg-12 col-md-12">
          <h6 class="learning-journey-heading">
            Learning and Development Journey
          </h6>
          <div class="learning-journey-items mb-5"></div>
          <button class="btn btn-primary mb-3 add-learning-and-development-journey">Add Learning and Development Journey</button>
          ${get_shoves_tugs_html(company_no)}
        </div>
        `;
        companyDetailsElement.html(fresherDetailsHTML);
        me.on_click_add_learning_and_development_journey(company_no);
        me.show_final_interest_step(company_no); // Reuse for Freshers
          // Show submit button by default for Fresher
          $('.submit-btn').fadeIn();
      } else if (selectedExperienceType === 'Experienced') {
         heading_html = '<h3 class="mx-auto">Hello, {{job_applicant.applicant_name}}, tell us about the ' + stringifyNumber(company_no) + ' company you worked for!</h3>';
      $(`.section_${company_no} h3.mx-auto`).replaceWith($(heading_html));
        $('.final-interest-section').remove();
        $('.submit-btn').fadeOut();
        const experienceDetailsHTML = `
        <div class="my-3 col-lg-12 col-md-12">
          <label class="form-label">What was the company's name? </label>
          <input
            type="text"
            class="form-control company_${company_no}_name"
            placeholder="Enter the ${stringifyNumber(company_no)} Company Name"
          />
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
          <input type="date" class="form-control joined_company${company_no}" />
        </div>
        <div class="mb-3 col-lg-12 col-md-12">
          <label class="form-label">What was your first salary at this company?</label>
          <input
            type="text"
            class="form-control salary_company${company_no}"
            placeholder="Enter your Salary in KWD"
          />
        </div>
        <div class="col-lg-12 col-md-12">
          <hr class="my-5" />
        </div>
        <div class="mb-3 col-lg-12 col-md-12">
          <label class="form-label">What was your starting job title?</label>
          <input
            type="text"
            class="form-control starting_job_title_company_${company_no}"
            placeholder="Enter the Job Title"
          />
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
          <label class="form-label"
            >Briefly describe your responsibilities in this role</label>
          <textarea
            class="form-control responsibilities_company_${company_no}"
            rows="4"
            placeholder="E.g. Managed a team of 5, handled client reports, etc."
          ></textarea>
        </div>
        <div class="mt-5 promotion_section_${company_no}" style="width: 100%"></div>
        <div class="col-lg-12 col-md-12 mb-3">
          <label>Tell us about contact person details from ${stringifyNumber(company_no)} company you worked!</label>
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Full name</label>
          <input type="text" class="form-control first_contact_name_${company_no}" placeholder="Full Name" />
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Email</label>
          <input type="text" class="form-control first_contact_email_${company_no}" placeholder="Email" />
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Designation</label>
          <input type="text" class="form-control first_contact_designation_${company_no}" placeholder="Designation" />
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Phone number with country code</label>
          <input type="text" class="form-control first_contact_phone_${company_no}" placeholder="Phone number with country code" />
        </div>
        <div class="col-lg-12 col-md-12 mb-3 add_more_contact_${company_no}">
          <button class="btn btn-dark float-left btn_add_more_contact_${company_no}" type="button">+ Add more contact person</button>
        </div>
        <div class="col-lg-12 col-md-12 mb-3">
          <label>Tell us some details about your best boss from ${stringifyNumber(company_no)} company you worked</label>
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Full name</label>
          <input type="text" class="form-control best_boss_name_${company_no}" placeholder="Full Name" />
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Email</label>
          <input type="text" class="form-control best_boss_email_${company_no}" placeholder="Email" />
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Phone number with country code</label>
          <input type="text" class="form-control best_boss_phone_${company_no}" placeholder="Phone number with country code" />
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Why is He/She the best?</label>
          <input type="text" class="form-control why_best_boss${company_no}" placeholder="Why is he/she the best?" />
        </div>
        <div class="col-lg-12 col-md-12 mb-3 mt-5" style="width: 100%">
          <label>Tell us some details about your best colleague from ${stringifyNumber(company_no)} company you worked</label>
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Full name</label>
          <input type="text" class="form-control best_colleague_name_${company_no}" placeholder="Full Name" />
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Email</label>
          <input type="text" class="form-control best_colleague_email_${company_no}" placeholder="Email" />
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Phone number with country code</label>
          <input type="text" class="form-control best_colleague_phone_${company_no}" placeholder="Phone number with country code" />
        </div>
        <div class="col-lg-6 col-md-6 mb-3">
          <label>Why is He/She the best?</label>
          <input type="text" class="form-control why_best_colleague${company_no}" placeholder="Why is he/she the best?" />
        </div>
        <div class="col-lg-12 col-md-12 mb-3">
          <label>Are you still working for the same company?</label>
          <select class="custom-select still_working_on_same_company_${company_no}">
            <option value="0">Choose</option>
            <option value="1">Yes</option>
            <option value="2">No</option>
          </select>
        </div>
        `;
        companyDetailsElement.html(experienceDetailsHTML);
        me.set_promotion_section_html(company_no, 1);
        me.on_change_still_working_on_same_company(company_no);
        me.on_click_add_more_contact_person(company_no);
      }
    })
  },
  on_click_add_learning_and_development_journey: function(company_no) {
    const me = this;
    let activityTypes = [];

    // Fetch activity types from the server
    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "Experience Type",
        limit_page_length: 100,
      },
      callback: function (r) {
        activityTypes = r.message;
      },
    });

    $(`.add-learning-and-development-journey`).click(function(e) {
      e.preventDefault();

      const learningJourneyItemsContainer = $(`.learning-journey-items`);
      const currentItemCount = learningJourneyItemsContainer.children().length;


      const learningJourneyItem = `
        <div class="learning-journey-item mb-3" data-item-index="${currentItemCount + 1}">
          <div class="mb-3">
            <label class="form-label">Activity type</label>
            <select class="form-control activity_type_select_${company_no}_${currentItemCount + 1}">
              <option value="" selected disabled>None</option>
              ${activityTypes.map(type => `<option value="${type.name}">${type.name}</option>`).join('')}
            </select>
          </div>
          <div class="assessment-questions"></div>
        </div>
      `;

      learningJourneyItemsContainer.append(learningJourneyItem);

      me.on_change_learning_and_development_journey_activity_type(company_no, currentItemCount + 1);
    })
  },
  on_change_learning_and_development_journey_activity_type: function(company_no, item_no) {
    $(`.activity_type_select_${company_no}_${item_no}`).on('change', function() {
      const selectedActivityType = $(this).val();
      if (selectedActivityType) {
        frappe.call({
          method: "frappe.client.get",
          args: {
            doctype: "Experience Type",
            name: selectedActivityType
          },
          callback: function(r) {
            const assessmentQuestions = r.message.assessment_questions || [];
            const questionsContainer = $(`.activity_type_select_${company_no}_${item_no}`).closest('.learning-journey-item').find('.assessment-questions');
            let questionsHTML = `
              <div class="mb-3">
                <label class="form-label">Title</label>
                <input type="text" class="form-control activity_title_${company_no}_${item_no}" placeholder="Enter title..." />
              </div>
            `;
            assessmentQuestions.forEach((question, index) => {
              questionsHTML += `
                <div class="mb-3">
                  <label class="form-label">${question.experience_type_question}</label>
                  <textarea class="form-control assessment_question_${company_no}_${item_no}_${index + 1}" rows="2" placeholder="Your answer..."></textarea>
                </div>
              `;
            });
            questionsContainer.html(questionsHTML);
          }
        });
      }
    });
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

// Helper to generate Shoves and Tugs block HTML
function get_shoves_tugs_html(company_no) {
  return `<div class="shoves-tugs-block my-3 col-lg-12 col-md-12">
    <div class="mb-3">
      <label class="form-label">Shoves</label>
      <textarea
        class="form-control shoves_input_${company_no}"
        rows="2"
        placeholder="Describe your shoves..."
      ></textarea>
    </div>
    <div class="mb-3">
      <label class="form-label">Tugs</label>
      <textarea
        class="form-control tugs_input_${company_no}"
        rows="2"
        placeholder="Describe your tugs..."
      ></textarea>
    </div>
  </div>`;
}