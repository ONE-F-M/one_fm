// Copyright (c) 2021, ONEFM and Contributors
// License: GNU General Public License v3. See license.txt

$(document).ready(function() {
  new career_history();
});

// Career History
career_history = Class.extend({
  init: function(){
  	// Bind Promotion Select on change
		this.on_change_promotion();
    // Bind submit button event
    this.submit_career_history();
		this.on_change_still_working_company();
  },
	on_change_promotion: function() {
		var me = this;
		$(".promotion_select_11").on("change", function(){
			var promotion_select = $(".promotion_select_11").val()
			var promotion_details_html = "";
			var promotion_details_next_job_title_html = `<div class="my-5 col-lg-6 col-md-6">
					<label class="form-label">So, Tell me to which position you got promoted first</label>
					<input type="text" class="form-control" placeholder="Enter Your New Job Title"/>
			</div>`
			var promotion_details_salary_html = `<div class="my-5 col-lg-6 col-md-6">
					<label class="form-label">What is Your Increased Salary in KWD?</label>
					<input type="text" class="form-control" id="increasedSalary1" placeholder="Enter your increased Salary in KWD"/>
			</div>`
			var promotion_details_promotion_date_html = `<div class="my-5 col-lg-6 col-md-6">
					<label class="form-label">When Do you got Promoted?</label>
					<input type="date" class="form-control" id="whenDoYouGotPromoted1"/>
			</div>`;

			if(promotion_select == 1){
				promotion_details_html = promotion_details_next_job_title_html+promotion_details_salary_html+promotion_details_promotion_date_html;
			}
			else if(promotion_select == 2){
				promotion_details_html = promotion_details_next_job_title_html+promotion_details_promotion_date_html;
			}
			else if(promotion_select == 3){
				promotion_details_html = promotion_details_salary_html+promotion_details_promotion_date_html;
			}
			$(".promotion_details_section_11").empty();
			// $(".promotion_section_1").empty();
	    $(".promotion_details_section_11").append(promotion_details_html);
			if(promotion_select > 0){
				var next_promotion_details_html = `<div class="col-lg-12 col-md-12 promotion_section_12">
						<label  class="form-label">Did You Got any Promotion or Salary Increase?</label>
						<select class="custom-select promotion_select_12">
							<option value="0">No, I did not get any promotion or salary increase</option>
							<option value="1">Yes, I Got a Promotion with a Salary Increase</option>
							<option value="2">Yes, Only Got a Promotion</option>
							<option value="3">Yes, Only Got a Salary Increase</option>
						</select>
				</div>`
				$(".promotion_section_12").empty();
				$(".promotion_section_1").append(next_promotion_details_html);
			}
			else{
				$(".promotion_section_12").empty();
				// $(".promotion_details_section_12").empty();
			}
		});
	},
	on_change_still_working_company: function() {
		var me = this;
		$(".still_working_on_company1").on("change", function(){
			var still_working = $(".still_working_on_company1").val();
			$(".reason_why_leave_job_1").empty();
			$(".are_you_still_working_1").empty();
			if (still_working == 1){
				var reason_why_leave_job_html = `<div class="col-lg-12 col-md-12 reason_why_leave_job_1">
					<label class="form-label">Why do you plan to leave the job?</label>
					<textarea rows="4" cols="50" name="comment" form="usrform" class="form-control"></textarea>
				</div>`;
				$(".main_section").append(reason_why_leave_job_html);
			}
			else if(still_working == 2){
				var are_you_still_working_html = `<div class="col-lg-12 col-md-12 promotion_section_12">
						<label  class="form-label">Are you still working?</label>
						<select class="custom-select are_you_still_working_1">
							<option value="0">Choose</option>
							<option value="1">No</option>
							<option value="2">Yes</option>
						</select>
				</div>`
				$(".main_section").append(are_you_still_working_html);
				me.on_change_are_you_still_working(1)
			}
		});
	},
	on_change_are_you_still_working: function(companyNumber) {
		var me = this;
		$(`.are_you_still_working_${companyNumber}`).on("change", function(){
			var are_you_still_working = $(`.are_you_still_working_${companyNumber}`).val();
			if(are_you_still_working == 2){
				me.create_company_section(companyNumber+1);
			}
		});
	},
	create_company_section: function(companyNumber) {
		var company_section_html = `<h3>Great {{job_applicant.applicant_name}}, Tell me about your ${stringifyNumber(companyNumber)} Company you worked on?</h3>
		<div class="my-5 col-lg-6 col-md-6">
			<label class="form-label">${stringifyNumber(companyNumber)} Company Name </label>
			<input type="text" class="form-control company_${companyNumber}" placeholder="Enter the ${stringifyNumber(companyNumber)} Company Name"/>
		</div>
		<div class="my-5 col-lg-6 col-md-6">
			<label class="form-label">Where is it Located? </label> <br>
			<select class="form-control country_list">
				<option>Select Country</option>
				{% for country in country_list %}
					<option>{{country.name}}</option>
				{% endfor %}
			</select>
		</div>
		<div class="mb-3 col-lg-6 col-md-6">
			<label class="form-label">When Do you Joined that company</label>
			<input type="date" class="form-control"/>
		</div>
		<div class="col-lg-12 col-md-12">
			<label for="Responisbilities" class="form-label">What are your top 3 Responisbilities?</label>
			<input type="text" class="form-control mb-3" placeholder="1"/>
			<input type="text" class="form-control mb-3" placeholder="2"/>
			<input type="text" class="form-control mb-3" placeholder="3"/>
		</div>
		<div class="col-lg-12 col-md-12">
			<hr class="my-5"/>
		</div>
		<div class="mb-3 col-lg-6 col-md-6">
			<label  class="form-label">What was your Starting Job Title?</label>
			<input type="text" class="form-control" placeholder="Enter the Job Title"/>
		</div>
		<div class="promotion_section_1" style="width: 100%">
			<div class="col-lg-12 col-md-12 promotion_section_11">
				<label  class="form-label">Did You Got any Promotion or Salary Increase?</label>
				<select class="custom-select promotion_select_11">
					<option value="0">No, I did not get any Promotion or Salary Increase</option>
					<option value="1">Yes, I Got a Promotion with a Salary Increase</option>
					<option value="2">Yes, Only Got a Promotion</option>
					<option value="3">Yes, Only Got a Salary Increase</option>
				</select>
			</div>
			<div class="row col-lg-12 col-md-12 my-5 promotion_details_section_11" style="width: 100%; display: flex" id="promotion_details_section_11">

			</div>
		</div>


		<div class="col-lg-12 col-md-12 mb-3">
			<label>Are You still working for the Company?</label>
			<select class="custom-select still_working_on_company1">
				<option value="0">Choose</option>
				<option value="1">Yes</option>
				<option value="2">No</option>
			</select>
		</div>`;
		$(".main_section").append(company_section_html);
	},
  submit_career_history: function() {
    // Submit Career History
    $('.btn-submit-career-history').click(function(){
      // POST Career History if all the conditions are satisfied
      if ($(".job_applicant").val()){
        frappe.freeze();
        frappe.call({
          type: "POST",
          method: "one_fm.templates.pages.career_history.create_career_history_from_portal",
          args: {
						job_applicant: $('#job_applicant').attr("data")
          },
          btn: this,
          callback: function(r){
            frappe.unfreeze();
            frappe.msgprint(frappe._("Succesfully Submitted your Career History and our HR team will be responding to you soon."));
            if(r.message){
              window.location.href = "/career_history";
            }
          }
        });
      }
      else{
        frappe.msgprint(frappe._("Please fill All the details to submit the Career History."));
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
