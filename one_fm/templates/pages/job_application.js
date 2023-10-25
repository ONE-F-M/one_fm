// Copyright (c) 2021, ONEFM and Contributors
// License: GNU General Public License v3. See license.txt

$(document).ready(function() {
  new job_application();
  // File attach Event binding
  $('#cv-file').on('change', ':file', function() {
    var $input = $(this);
    var file_input = $input.get(0);
    if (file_input.files[0].size > 5242880) {
      alert('max upload size is 5 Mega Byte');
    }
    if(file_input.files.length) {
      file_input.filedata = { "files_data" : [] };
    }
    window.file_reading = true;
    // this will handle multi files input
    $.each(file_input.files, function(key, value) {
      setupReader(value, file_input);
    });
    window.file_reading = false;

  });
});
var rotation_shift = $("#work_details").attr("rotation_shift")
var travel_type = $("#work_details").attr("travel_type")
var travel = $("#work_details").attr("travel")
var night_shift = $("#work_details").attr("night_shift")
var license = $("#work_details").attr("license")

// Setup fiel reader
function setupReader(file, input) {
  let name = file.name;
  var reader = new FileReader();
  reader.onload = function(e) {
    input.filedata.files_data.push({
      "__file_attachment": 1,
      "filename": file.name,
      "dataurl": reader.result
    });
  }
  reader.readAsDataURL(file);
}

// Job Application
job_application = Class.extend({
  init: function(){
    // Bind Applicant Name on change
    this.on_change_applicant_name();
    // Bind Email on change
    this.on_change_email();
    // Bind Contact Number on change
    this.on_change_number();
    // Bind Country on change
    this.on_change_country();
    // Bind Work Detail on change
    this.on_change_work_details();
    // Bind submit button event
    this.submit_job_application();
  },
  on_change_applicant_name: function(){
    var me  = this;
    $(".applicant_name").on("change", function(){
      var applicant_name = $(".applicant_name").val();
      if(applicant_name){
        // Show country section
        me.show_country(applicant_name);
      }
    });
  },
  show_country: function(applicant_name) {
    if(applicant_name){
      $(".applicant_country").empty();
      $(".applicant_country").append(`<h5>Hey ${applicant_name}, what's your nationality?</h5>`)
      $(".country_list").removeClass('hide');
    }
  },
  show_applicant_contact_details: function() {
    $(".applicant_contact").empty();
    $(".applicant_contact").append(`<h5>Please provide your mobile number and email address so we could contact you.</h5>`)
    $(".contact_number").removeClass('hide');
    $(".contact_email").removeClass('hide');
  },
  on_change_contact_details: function(applicant_name){
    var me  = this;
    var applicant_name = $(".applicant_name").val();
    var contact_number = $(".contact_number").val();
    var contact_email = $(".contact_email").val();
    if(applicant_name && contact_number && contact_email){
      // Validate email regular expression
      if(!validate_email(contact_email)) {
        frappe.msgprint(frappe._("Please enter valid email address"));
        $('.contact_email').focus();
        return false;
      }
      if(rotation_shift || travel || night_shift){
        // Show Work Detail Section
        me.show_rotation_shift();
      }
      else{
          // Show CV section
          me.show_cv_section();
      }

    }
  },
  on_change_email: function() {
    var me = this;
    $(".contact_email").on("change", function(){
      me.on_change_contact_details();
    });
  },
  on_change_number: function() {
    var me = this;
    $(".contact_number").on("change", function(){
      me.on_change_contact_details();
    });
  },
  on_change_country: function() {
    var me  = this;
    $(".country_list").on("change", function(){
      // Show Contact details
      me.show_applicant_contact_details();
    });
  },
  on_change_work_details: function() {
    var me  = this;
    $(".rotation_shift").on("change", function(){
      // Show CV section
      me.show_night_shift();
    });
    $(".night_shift").on("change", function(){
      // Show CV section
      me.show_travel();
    });
    $(".travel").on("change", function(){
      // Show CV section
      me.show_license();
    });
    $(".license").on("change", function(){
      if($("#license input[type='radio']:checked").val() == 'yes'){
        $(".license_type").removeClass('hide');
      }
      else if($("#license input[type='radio']:checked").val() == 'no'){
        if(!$(".license_type").hasClass('hide')){
          $(".license_type").addClass('hide');
        }
        $(".visa").removeClass('hide');
      }
    });
    $(".license_type").on("change", function(){
      $(".visa").removeClass('hide');
    });
    $(".visa").on("change", function(){
      if($("#visa input[type='radio']:checked").val() == 'yes'){
        $(".visa_type").removeClass('hide');
      }
      else if($("#visa input[type='radio']:checked").val() == 'no'){
        if(!$(".visa_type").hasClass('hide')){
          $(".visa_type").addClass('hide');
        }
        $(".in_kuwait").removeClass('hide');
      }
    });
    $(".visa_type").on("change", function(){
      $(".in_kuwait").removeClass('hide');
    });
    $(".in_kuwait").on("change", function(){
      me.show_cv_section();
    });
  },
  show_rotation_shift: function() {
    var me  = this;
    if(rotation_shift == 1){
      $(".rotation_shift").removeClass('hide');
    }
    else{
      me.show_night_shift();
    }
  },
  show_night_shift: function() {
    var me  = this;
    if(night_shift == 1){
      $(".night_shift").removeClass('hide');
    }
    else{
      me.show_travel();
    }
  },
  show_travel: function() {
    var me  = this;
    if(travel == 1 && travel_type){
      $(".travel").removeClass('hide');
      $(".travel_q").append(`${travel_type}?`)
    }
    else{
      me.show_license();
    }
  },
  show_license: function() {
    var me  = this;

    if(license == 1){
      $(".license").removeClass('hide');
    }
    else{
      $(".visa").removeClass('hide');
    }
  },
  show_cv_section: function() {
    var me  = this;
    me.show_language_section();
    $(".applicant_cv").empty();
    $(".applicant_cv").append(`<h5>Please attach your CV here so we can get to know you better.</h5>`)
    $(".cv-file").removeClass('hide');
  },
  show_language_section: function() {
    $(".languages_heading").removeClass('hide');
    $(".languages_table_div").removeClass('hide');
  },
  submit_job_application: function() {
    // Submit Job Application
    $('.btn-submit-application').click(async function(){
      // var file_data = {};
      // Read file data
      // $("[type='file']").each(function(i){
      //   file_data[$(this).attr("id")] = $('#'+$(this).attr("id")).prop('filedata');
      // });

      var cv = document.getElementById("cv").files[0]
      if (cv && !cv.type.includes(["application/pdf"])){
        return frappe.msgprint(frappe._("CV must be in PDF format !"));
      }

      // POST Job Application if all the conditions are satisfied

      if ($(".applicant_name").val() && $(".country_list").val() && $(".contact_email").val() && $(".contact_number").val() && cv){
        frappe.freeze();
        var response = await upload_image_to_server(cv)
        var url = (response && response.message) ? response.message.file_url : "";
        var name_of_file = (response && response.message) ? response.message.name : "";
        const languages_div = document.getElementById('languages_table_div');
        let erf_languages;
        if(languages_div){
          erf_languages = languages_div.getAttribute('data').split(",");
        }
        var languages = [];
        if(erf_languages){
          for (const language of erf_languages) {
            languages.push({
              language: language,
              speak: $(`.${language}_speak`).val(),
              read: $(`.${language}_read`).val(),
              write: $(`.${language}_write`).val()
            });
          }
        }
        frappe.call({
          type: "POST",
          method: "one_fm.templates.pages.job_application.create_job_applicant_from_job_portal",
          args: {
            applicant_name: $(".applicant_name").val(),
            country: $(".country_list").val(),
            applicant_email: $(".contact_email").val(),
            applicant_mobile: $(".contact_number").val(),
            job_opening: $('#job_opening').attr("data"),
            resume_attachment_url: url,
            rotation_shift: $("#rotation_shift input[type='radio']:checked").val(),
            night_shift: $("#night_shift input[type='radio']:checked").val(),
            travel: $("#travel input[type='radio']:checked").val(),
            travel_type: travel_type,
            driving_license: $("#license input[type='radio']:checked").val(),
            license_type: $(".license_type").val(),
            visa: $("#visa input[type='radio']:checked").val(),
            visa_type: $(".visa_type").val(),
            in_kuwait: $("#in_kuwait input[type='radio']:checked").val(),
            languages: languages,
            name_of_file: name_of_file
          },
          btn: this,
          callback: function(r){
            frappe.unfreeze();
            if(!r.exc && r.message) {
              frappe.msgprint(frappe._("Successfully submitted your application. Our HR team will be responding to you soon."));
              setTimeout(()=>{window.location.href = "/jobs"}, 3000);
            } else {
              frappe.msgprint(__("Application is not submitted. <br /> " + r.exc));
            }
          }
        });
      }
      else{
        frappe.msgprint(frappe._("Please fill all the details to submit the Job Application."));
      }
    });
  }
});


async function upload_image_to_server(file) {
  return new Promise((resolve, reject) => {
    var xhr = new XMLHttpRequest();
    let form_data = new FormData();

    xhr.open('POST', '/api/method/upload_file', true);

    xhr.setRequestHeader("X-Frappe-CSRF-Token", frappe.csrf_token);
    xhr.setRequestHeader("Accept", "application/json");

    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          // File uploaded successfully, and the server responded with status 200
          var response = JSON.parse(xhr.responseText);
          resolve(response);
        } else {
          // File upload failed or server responded with an error status
          reject(new Error("File upload failed. Status: " + xhr.status));
        }
      }
    };

    xhr.onerror = function () {
      // Network error or other issues with the XMLHttpRequest
      reject(new Error("Network error occurred."));
    };

    form_data.append('file', file);
    form_data.append('is_private', true);
    xhr.send(form_data);
  });
}
