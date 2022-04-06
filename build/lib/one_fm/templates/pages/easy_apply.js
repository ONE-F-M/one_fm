$(document).ready(function () {
  get_nationality();
});

function get_nationality() {
  $("#nationality").empty();
  const job_container = document.getElementById("nationality");
  job_container.innerHTML +=  `<option></option>`;
  frappe.call({
    method: "one_fm.templates.pages.easy_apply.get_nationality_list",
    callback: function (r) {
      if (r.message) {
        var jobs = r.message;
        jobs.forEach((job, i) => {
          job_container.innerHTML +=  `
            <option>${job.name}</option>
          `;
        });
      }
    }
  });

};

function easy_apply() {
  frappe.call({
    method: 'one_fm.templates.pages.job_application.easy_apply',
    args: {
      first_name: $('#firstName').val(),
      second_name: $('#secondName').val() || '',
      third_name: $('#thirdName').val() || '',
      last_name: $('#lastName').val(),
      nationality: $('#nationality').val(),
      civil_id: $('#civilID').val() || '',
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
        $('#firstName').val('');
        $('#secondName').val('');
        $('#thirdName').val('');
        $('#lastName').val('');
        $('#nationality').val('');
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
