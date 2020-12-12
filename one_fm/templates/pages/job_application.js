const baseUrl = (frappe.base_url || window.location.origin);
if(baseUrl.substr(baseUrl.length-1, 1)=='/') baseUrl = baseUrl.substr(0, baseUrl.length-1);
const listOfLanguages = [];
const listOfSkills = [];
const basicSkills = "basic-skills";
const language = "rating";

$(document).ready(function () {
  if(window.localStorage.getItem("job-application-auth")){
    set_jobs_info_to_application();
  }
  else {
      alert("Please Signup or Login!");
      window.location = "applicant-sign-up";
  }
});

function set_jobs_info_to_application() {
  const job = localStorage.getItem("currentJobOpening");
  if(!job){
      alert("Please Select a Job Posting before continuing");
      window.location = "job_opening";
  }
  frappe.call({
    method: "one_fm.templates.pages.job_application.get_job_details",
    args: {'job': job},
    callback: function (r) {
      if(r.message){
        var erf = r.message;
        window.localStorage.setItem("erf", erf.name);
        erf.designation_skill.map(a=>{
            listOfSkills.push({
              skill: a.skill,
              proficiency: ""
            })
            placeSkills(basicSkills, a.skill)
        })
        erf.languages.map(a=>{
          listOfLanguages.push({
            language: a.language,
            language_name: a.language_name,
            speak: 0,
            read: 0,
            write: 0
          });
          placeSkills(language, "none", a.language_name)
        })
        starEffects();
      }
    }
  });
};

// Place Skills
const placeSkills = (location, skill="none", language="none") => {
    document.getElementById(location).innerHTML +=
    skill != "none" ? `
    <div class="form-group col-md-6">
    <p>${skill}</p>
    </div>
    <div class="form-group col-md-6">
    <div class='rating-stars'>
        <ul class='stars'>
            <li class='star' data-skill=${skill} title='skill' data-value='1'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-skill=${skill} title='skill' data-value='2'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-skill=${skill} title='skill' data-value='3'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-skill=${skill} title='skill' data-value='4'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-skill=${skill} title='skill' data-value='5'>
                <i class='fa fa-star fa-fw'></i>
            </li>
        </ul>
    </div>
</div>
    ` : `
<div class="form-group col-md-4">
    <p>${language}</p>
</div>
<div class="form-group col-md-2">
<div class=''>
Speak
</div>
<div class='mt-3'>
Read
</div>
<div class='mt-3'>
Write
</div>
</div>
<div class="form-group col-md-6">
    <div class='rating-stars'>
        <ul class='stars'>
            <li class='star' data-language=${language} title='speak' data-value='1'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='speak' data-value='2'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='speak' data-value='3'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='speak' data-value='4'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='speak' data-value='5'>
                <i class='fa fa-star fa-fw'></i>
            </li>
        </ul>
    </div>
    <div class='rating-stars'>
        <ul class='stars'>
            <li class='star' data-language=${language} title='read' data-value='1'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='read' data-value='2'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='read' data-value='3'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='read' data-value='4'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='read' data-value='5'>
                <i class='fa fa-star fa-fw'></i>
            </li>
        </ul>
    </div>
    <div class='rating-stars'>
        <ul class='stars'>
            <li class='star' data-language=${language} title='write' data-value='1'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='write' data-value='2'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='write' data-value='3'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='write' data-value='4'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' data-language=${language} title='write' data-value='5'>
                <i class='fa fa-star fa-fw'></i>
            </li>
        </ul>
    </div>
</div>
`
}

// Auto complete scripts
$(function() {
    let availableTags = [
      "Married"
    ];
    $( "#tags" ).autocomplete({
      source: availableTags
    });
});

// Star Component
const starEffects = () =>{

    /* 1. Visualizing things on Hover - See next part for action on click */
    $('.stars li').on('mouseover', function(){
      var onStar = parseInt($(this).data('value'), 10); // The star currently mouse on

      // Now highlight all the stars that's not after the current hovered star
      $(this).parent().children('li.star').each(function(e){
        if (e < onStar) {
          $(this).addClass('hover');
        }
        else {
          $(this).removeClass('hover');
        }
      });

    }).on('mouseout', function(){
      $(this).parent().children('li.star').each(function(e){
        $(this).removeClass('hover');
      });
    });


    /* 2. Action to perform on click */
    $('.stars li').on('click', function(){
      var onStar = parseInt($(this).data('value'), 10); // The star currently selected
      var stars = $(this).parent().children('li.star');

      for (i = 0; i < stars.length; i++) {
        $(stars[i]).removeClass('selected');
      }

      for (i = 0; i < onStar; i++) {
        $(stars[i]).addClass('selected');
      }

      // RESPONSE
      var ratingValue = parseInt($('.stars li.selected').last().data('value'), 10);
      if(this.title != "skill"){
        listOfLanguages.map(a=> {
          if(a.language_name == this.getAttribute('data-language')){
            a[this.title] = ratingValue;
          }
        })
      }
      else {
        listOfSkills.map(a=> {
          if(a.skill == this.getAttribute('data-skill'))
            a.proficiency = ratingValue;
        })
      }
      var msg = "";
      if (ratingValue > 1) {
          msg = "Thanks! You rated this " + ratingValue + " stars.";
      }
      else {
          msg = "We will improve ourselves. You rated this " + ratingValue + " stars.";
      }
    });
}

// OCR Get Text
(function () {
    console.log("before");
    const firstName = document.getElementById("firstName");
    const secondName = document.getElementById("secondName");
    const thirdName = document.getElementById("thirdName");
    const email = document.getElementById("email");
    const civilIdElement = document.getElementById("civilId");
    const civilValidTill = document.getElementById("civilValidTill");
    const dob = document.getElementById("dob");
    const passport = document.getElementById("PassportNumber");
    console.log("after", civilIdElement);
    var patternForCivilIdNumber = new RegExp("^\\d{12}$");
    var patternForPassportNumber = new RegExp("([A-Z])\w+");
    const placeText = () => {
        if (window.localStorage.getItem("civilId")) {
            const civilId = window.localStorage.getItem("civilId");
            console.log("extracted civil id", civilId);
            let splited = civilId.split(" ");
            var filtered = splited.filter(function (el) {
                return el != null && el != "";
            });
            console.log(filtered);
            filtered.reduce((acc, cur, currentIndex, array) => {
                let loweredCurrent = cur.toLocaleLowerCase();
                if (cur.match(patternForCivilIdNumber)) {
                    civilIdElement.value = cur;
                }
                if (loweredCurrent.includes("name")) {
                    console.log(cur.slice(4).split('\n')[0]);
                    firstName.value = cur.slice(4).split('\n')[0];
                }
                if (loweredCurrent.includes("passport") || loweredCurrent.includes("passportno") || loweredCurrent.includes("pass") || loweredCurrent.includes("tno") || loweredCurrent.includes("assport")) {
                    let passportNumber = array[currentIndex + 1];
                    if (passportNumber.toLocaleLowerCase() == "no")
                        passportNumber = array[currentIndex + 2];
                    passportNumber = passportNumber.replace(/[^A-Za-z0-9]/g, "");
                    console.log(passportNumber);
                    passport.value = passportNumber;
                }
                if (loweredCurrent.includes("birth") || loweredCurrent.includes("bith") || loweredCurrent.includes("brth") || loweredCurrent.includes("hdate") || loweredCurrent.includes("BithDate")) {
                    let dateOfBirth = array[currentIndex + 1];
                    if (dateOfBirth.charAt(0) == "(") {
                        dateOfBirth = dateOfBirth.slice(1);
                        dateOfBirth = `0${dateOfBirth}`;
                    }
                    let newdate = dateOfBirth.split("/").reverse().join("-");
                    dob.defaultValue = newdate;
                }
                if (loweredCurrent.includes("expiryDate") || loweredCurrent.includes("expiry") || loweredCurrent.includes("exp") || loweredCurrent.includes("ydate")) {
                    console.log(array[currentIndex + 1]);
                    let dateOfCivilIdExpiry = array[currentIndex + 1];
                    if (dateOfCivilIdExpiry.charAt(0) == "(") {
                        dateOfCivilIdExpiry = dateOfCivilIdExpiry.slice(1);
                        dateOfCivilIdExpiry = `0${dateOfCivilIdExpiry}`;
                    }
                    let newdate = dateOfCivilIdExpiry.split("/").reverse().join("-");
                    civilValidTill.defaultValue = newdate;
                }
                // console.log("accumulator", acc);
                // console.log("current", cur);
                // console.log("currentIndex", currentIndex);
                // console.log("array", array);
            });
        }
        if (localStorage.getItem("gName") && localStorage.getItem("gEmail")) {
            let name = localStorage.getItem("gName").split(" ");
            console.log("Google Details", name);
            email.value = localStorage.getItem("gEmail");
            firstName.value = name[0] ? name[0] : "";
            secondName.value = name[1] ? name[1] : "";
            thirdName.value = name[2] ? name[2] : "";
            thirdName.value += " " + (name[3] ? name[3] : "");
            thirdName.value += " " + (name[4] ? name[4] : "");
        }
        if (localStorage.getItem("linkedInData")) {
            let data = JSON.parse(localStorage.getItem("linkedInData"));
            console.log("linkedin data",data);
        if(!data.data.error){
            firstName.value = data.data.firstName?.localized.en_US;
            thirdName.value = data.data.lastName?.localized.en_US;
        }
        }
    };


    placeText();
})();

// Submit
const submitForm = () => {
    frappe.call({
      method: 'one_fm.templates.pages.job_application.create_job_applicant',
      args: {
        job_opening: localStorage.getItem("currentJobOpening"),
        email_id: $('#email').val(),
        job_applicant_fields: {
          one_fm_first_name: $('#firstName').val(),
          one_fm_erf: window.localStorage.getItem("erf"),
          // one_fm_second_name: $('#secondName').val(),
          // one_fm_third_name: $('#thirdName').val(),
          one_fm_last_name: $('#lastName').val(),
          one_fm_gender: $("#gender option:selected").text(),
          one_fm_religion: $("#religion option:selected").text(),
          one_fm_date_of_birth: $('#dob').val(),
          one_fm_place_of_birth: $('#placeOfBirth').val(),
          one_fm_marital_status: $('#MaritalStatus option:selected').text(),
          one_fm_email_id: $('#email').val(),
          one_fm_contact_number: $('#phone').val(),
          one_fm_secondary_number: $('#phone1').val(),
          one_fm_passport_number: $('#PassportNumber').val(),
          one_fm_passport_holder_of: $('#passportHolderOf').val(),
          one_fm_passport_issued: $('#passportIssued').val(),
          one_fm_passport_expire: $('#passportExpiry').val(),
          one_fm_passport_type: $('#PassportType option:selected').text(),
          one_fm_have_a_valid_visa_in_kuwait: $('#ValidVisa').val(),
          one_fm_visa_type: $('#visaType').val(),
          one_fm_visa_issued: $('#visaIssuedOn').val(),
          one_fm_cid_number: $('#civilId').val(),
          one_fm_cid_expire: $('#civilValidTill').val(),
          one_fm_educational_qualification: $('#educationalQualification option:selected').text(),
          one_fm_university: $('#University').val(),
          one_fm_specialization: $('#Specialization').val(),
          one_fm_rotation_shift: $('#rotationalShift option:selected').text(),
          one_fm_night_shift: $('#nightShift option:selected').text(),
          one_fm_type_of_driving_license: $('#typeOfDrivingLicense option:selected').text(),
        },
        languages: listOfLanguages,
        skills: listOfSkills,
        // files: $('#resume').val(),
      },
      callback: function (r) {
        if (r) {
          if (r.message == 1) {
            Swal.fire(
              'Successfully Sent!',
              'Your message has been sent.',
              'success'
            );

            $('#fullName').val('');
            $('#email').val('');
            $('#phone').val('');
            $('#resume').val('');
          } else {
            Swal.fire({
              icon: 'error',
              title: 'Could not send...',
              text: 'Please try again!'
            });
          }
        }
      }
    });
}
document.getElementById("submitBtn").addEventListener("click", submitForm);
