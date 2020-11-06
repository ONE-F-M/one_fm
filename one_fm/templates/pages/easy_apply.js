function easy_apply() {
    frappe.call({
      method: 'one_fm.templates.pages.job_application.easy_apply',
      args: {
        applicant_name: $('#fullName').val(),
        applicant_email: $('#email').val(),
        applicant_mobile: $('#phone').val(),
        cover_letter: $('#resume').val(),
        designation: localStorage.getItem("currentEasyJobOpening")
      },
      callback: function (r) {
        if (r) {
  
          console.log(r);
  
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