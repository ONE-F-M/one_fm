const baseUrl = (frappe.base_url || window.location.origin);
$(document).ready(function () {
  get_jobs_info();
});
if(baseUrl.substr(baseUrl.length-1, 1)=='/') baseUrl = baseUrl.substr(0, baseUrl.length-1);
const signUp = (erf_code) => {
    localStorage.setItem("currentJobOpening", erf_code.target.id)
    if(window.localStorage.getItem("job-application-auth"))
        location.href = "./job_application"
    else
        location.href = "./applicant-sign-up"
}
const easySignUp = (job) => {
  localStorage.setItem("currentEasyJobOpening", job)
  // if(window.localStorage.getItem("job-application-auth"))
  location.href = "./easy_apply"
  // else
  //     location.href = "./applicant-sign-up"
}

function get_jobs_info() {
  $("#job_listing").empty();
  frappe.call({
    method: "one_fm.templates.pages.job_opening.get_job_openings",
    callback: function (r) {
      var content = "";
      var content_modal = "";
      if (r.message) {
        var jobs = r.message;
        jobs.forEach((job, i) => {
          const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
          const date = new Date(job.one_fm_job_opening_created);
          const finalDate = `${date.getDate()} ${months[date.getMonth()]}`
          const job_container = document.getElementById("job_listing");
          job_container.innerHTML +=  `<li class="job-preview" id=${job.name}>
            <div class="content float-left">
                <h4 class="job-title">
                    ${job.designation}
                </h4>
                <h5 class="company">
                Posted On
                    ${finalDate}
                </h5>
                <p>
                    ${job.description}
                </p>
            </div>
            <a id='${job.name}' class="btn btn-apply mr-2 float-sm-right float-xs-left proceed-to-easy-signup" onclick="easySignUp('${job.name}')">
                Easy Apply
            </a>
            </li>`;
            // <a id=${job.name} class="btn btn-apply float-sm-right float-xs-left proceed-to-signup">
            // Apply
            // </a>
        });
      }
    }
  });

};
