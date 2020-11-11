function easy_apply() {
  frappe.call({
    method: 'one_fm.templates.pages.job_application.easy_apply',
    args: {
      applicant_name: $('#fullName').val(),
      applicant_email: $('#email').val(),
      applicant_mobile: $('#phone').val(),
      cover_letter: $('#coverLetter').val(),
      // resume: $('#resume').val(),
      job_opening: localStorage.getItem("currentEasyJobOpening")
    },
    callback: function (r) {
      if (r && r.message) {
        Swal.fire(
        'Applied Successfully!',
        'Your message has been sent.',
        'success'
        );
        $('#fullName').val('');
        $('#email').val('');
        $('#phone').val('');
        // $('#resume').val('');
        $('#coverLetter').val('');
      }
      else {
        Swal.fire({
        icon: 'error',
        title: 'Could not send...',
        text: 'Please try again!'
        });
      }
    },
    freeze: true,
    freeze_message: __("Applying ......!")
  });
};
