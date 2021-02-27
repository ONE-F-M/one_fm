const baseUrl = (frappe.base_url || window.location.origin);
$(document).ready(function () {
  console.log("Ready .....!!");
  get_jobs_info();
});
if(baseUrl.substr(baseUrl.length-1, 1)=='/') baseUrl = baseUrl.substr(0, baseUrl.length-1);
const signUp = (job) => {
  localStorage.setItem("currentJobOpening", job)
  location.href = "./applicant-sign-up"
}
const easySignUp = (job) => {
  localStorage.setItem("currentEasyJobOpening", job)
  location.href = "./easy_apply"
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
          const job_container = document.getElementById("job_listing");
          var job_list_html = `<li class="job-preview" id=${job.name}>
            <div class="content float-left">
                <h4 class="job-title">
                    ${job.designation}
                </h4>
                <p>
                    ${job.description}
                </p>
            </div>`
            if(job.allow_easy_apply){
              job_list_html += `<a id='${job.name}' class="btn btn-apply mr-2 float-sm-right float-xs-left proceed-to-easy-signup" onclick="easySignUp('${job.name}')">
                  Easy Apply
              </a>`
            }
            job_list_html += `<a id=${job.name} class="btn btn-apply float-sm-right float-xs-left proceed-to-signup" onclick="signUp('${job.name}')">
              Apply
            </a>
            </li>`;
          job_container.innerHTML += job_list_html;
        });
      }
    }
  });

};
