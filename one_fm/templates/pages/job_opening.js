const signUp = (erf_code) => {
    localStorage.setItem("currentJobOpening", erf_code.target.id)
    location.href = "./applicant-sign-up"
}
// proceedToSignUp.addEventListener("click", signUp);

const renderJobs = (designation, erf_code, creation) => {
    const job_container = document.getElementById("job_listing");    
    job_container.innerHTML +=  `<li class="job-preview" id=${erf_code}>
<div class="content float-left">
    <h4 class="job-title">
        ${designation}
    </h4>
    <h5 class="company">
    Posted On
        ${creation}
    </h5>
</div>
<a id=${erf_code} class="btn btn-apply float-sm-right float-xs-left proceed-to-signup">
    Apply
</a>
</li>`;
}
// frappe.call('get_gender')
//     .then(r => {
//         console.log("heyyyyy",r)
//         // {message: "pong"}
//     })

// frappe.call({
//     method: 'frappe.core.doctype.user.user.get_role_profile',
//     args: {
//         role_profile: 'Test'
//     },
//     callback: (r) => {
//         // on success
//     },
//     error: (r) => {
//         // on error
//     }
// })
// frappe.db.count('ERF')
//     .then(count => {
//         console.log(count)
//     })
// frappe.db.get_doc('ERF')
//     .then(doc => {
//         console.log("ada",doc)
//     })
// fetch("http://192.168.0.129/api/resource/Gender", {}).then(a=> console.log("hello", a.body.getReader()))
fetch('http://192.168.0.129/api/resource/ERF?fields=["designation", "erf_code", "creation"]', {
    headers: {
        'Authorization': 'token 57f152ebd8b9af5:50fe35e6c122253'
    }
})
.then(r => r.json())
.then(r => {
    const job_container = document.getElementById("job_listing");
    job_container.innerHTML = "";
    console.log("parakkum rasaliyay",r);
    const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    r.data.map(a=> {
        console.log(a)
        const {designation, erf_code, creation} = a;
        const date = new Date(creation);
        console.log(date.getDate())
        const finalDate = `${date.getDate()} ${months[date.getMonth()]}`
        renderJobs(designation, erf_code, finalDate)
    })
})
.then(r=>{
    const proceedToSignUp = document.getElementsByClassName("proceed-to-signup");
for(let i=0; i<proceedToSignUp.length; i++){
    proceedToSignUp[i].addEventListener("click", signUp);
}
})