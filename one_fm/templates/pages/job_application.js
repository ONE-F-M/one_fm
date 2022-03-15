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
      $(".applicant_country").append(`<h5>Hey ${applicant_name}, whats your nationality?</h5>`)
      $(".country_list").removeClass('hide');
    }
  },
  show_applicant_contact_details: function() {
    $(".applicant_contact").empty();
    $(".applicant_contact").append(`<h5>Please provide your email id and mobile number so we could contact you.</h5>`)
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
      // Show CV section
      me.show_cv_section(applicant_name);
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
  show_cv_section: function(applicant_name) {
    $(".applicant_cv").empty();
    $(".applicant_cv").append(`<h5>Dear ${applicant_name}, please attach your CV here so we can get to know you better.</h5>`)
    $(".cv-file").removeClass('hide');
  },
  submit_job_application: function() {
    // Submit Job Application
    $('.btn-submit-application').click(function(){
      var file_data = {};
      // Read file data
      $("[type='file']").each(function(i){
        file_data[$(this).attr("id")] = $('#'+$(this).attr("id")).prop('filedata');
      });
      // POST Job Application if all the conditions are satisfied
      if ($(".applicant_name").val() && $(".country_list").val() && $(".contact_email").val() && $(".contact_number").val() && file_data){
        frappe.freeze();
        frappe.call({
          type: "POST",
          method: "one_fm.templates.pages.job_application.create_job_applicant_from_job_portal",
          args: {
            applicant_name: $(".applicant_name").val(),
            country: $(".country_list").val(),
            applicant_email: $(".contact_email").val(),
            applicant_mobile: $(".contact_number").val(),
            job_opening: $('#job_opening').attr("data"),
            files: file_data
          },
          btn: this,
          callback: function(r){
            frappe.unfreeze();
            frappe.msgprint(frappe._("Successfully submitted your application. Our HR team will be responding to you soon."));
            if(r.message){
              window.location.href = "/jobs";
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
