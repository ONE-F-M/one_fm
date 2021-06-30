// career-history JS here

const domGetter = (id) => {
    return document.getElementById(id);
};
const valueGetter = (id) => {
    return document.getElementById(id).value;
};
const valueSetter = (id, value) => {
    document.getElementById(id).value = value;
};

// Values has to be set from the Backend
valueSetter('erfNumber', '987654321');
valueSetter('applicantId', '12345');
valueSetter('historyScore', '75');
valueSetter('Promotions', '2');
valueSetter('Experience', '1 Year');

// let numberofCompany = document.getElementById('numberofCompany');
// function show() {
//     var FormValue = numberofCompany.options[numberofCompany.selectedIndex].value;
//     console.log(FormValue);
// }
// numberofCompany.onchange = show();

// var df= document.getElementById("startDate").value;
// var dt = .value;  


// const totalValue = () => {
//     var df = Number(document.getElementById("startDate"));
//     var dt = Number(document.getElementById('endDate'));
//     var allMonths = dt.getMonth() - df.getMonth() + (12 * (dt.getFullYear() - df.getFullYear()));
//     var allYears = dt.getFullYear() - df.getFullYear();
//     var partialMonths = dt.getMonth() - df.getMonth();
//     if (partialMonths < 0) {
//         allYears--;
//         partialMonths = partialMonths + 12;
//     }
//     var total = allYears + " years " + partialMonths + " months";
//     console.log(total);
//     console.log({ jaren: allYears, maanden: partialMonths });
// };
// console.log(totalValue());
const returnCompanyDom = (companyNumber) => {
    return `<div class="row" id="${companyNumber}">
    <div class="mb-3 col-lg-4"></div>
    <div class="col-md-12">
        <h3>Company <span>${companyNumber}</span> </h3>        
    </div>
    <div class="mb-3 col-lg-4">
        <label for="companyName" class="form-label">Current Company Name </label>
        <input type="text" class="form-control" id="companyName" placeholder="Current Company Name">
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-3 ">
        <label for="monthlySalary" class="form-label">Monthly Salary in $ </label>
        <input type="text" class="form-control" id="monthlySalary"
            placeholder="Current Company Name"> <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-5 "></div>
    <div class="mb-3 col-lg-3 ">
        <label for="jobTitle" class="form-label">Current Job Title</label>
        <input type="text" class="form-control" id="jobTitle" placeholder="Current Company Name">
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-3 ">
        <label for="startDate" class="form-label">Job Start Date</label>
        <input type="date" class="form-control" id="startDate" placeholder="Current Company Name">
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-3 ">
        <label for="endDate" class="form-label">End Date</label>
        <input type="date" class="form-control" id="endDate" placeholder="Current Company Name">
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-3 ">
        <label for="totalExperiance" class="form-label">Years Of Experience</label>
        <input type="text" class="form-control" id="totalExperiance" placeholder="number" disabled>
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-8">
        <label for="opportunityjobContent" class="form-label">Could you please tell us what is it
            that makes
            you interested in this opportunity?</label>
        <textarea rows="4" cols="50" name="comment" form="usrform" class="form-control jobContent"
            id="opportunityjobContent"></textarea>
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-8">
        <label for="Responisbilities" class="form-label">What are your top 3
            Responisbilities?</label>
        <input type="text" class="form-control mb-3" id="Responisbilities" placeholder="1">
        <!-- This is a Input element -->
        <input type="text" class="form-control mb-3" id="Responisbilities" placeholder="2">
        <input type="text" class="form-control mb-3" id="Responisbilities" placeholder="3">
    </div>
    <div class="mb-3 col-lg-8">
        <label for="opportunityjobContent" class="form-label">Could you please tell us what is it
            that makes
            you interested in this opportunity?</label>

        <textarea rows="4" cols="50" name="comment" form="usrform" class="form-control jobContent"
            id="opportunityjobContent"></textarea>
        <!-- This is a Input element -->
    </div>
    <div class="col-md-6">

        <label for="anyPromotion" class="form-label">Did you get any Promotion? (Change in Job
            title)</label>

        <div class="col-md-4">
            <select class="custom-select" id="anyPromotion">
                <option selected>Choose</option>
                <option value="1">Yes</option>
                <option value="2">No</option>
            </select>
        </div>
    </div>
    <div class="mb-3 col-lg-2"></div>
    <div class="mb-3 col-lg-4">
        <label for="totalPrmottions" class="form-label">Total Promottions of Applicant</label>
        <input type="text" class="form-control" id="totalPrmottions"
            placeholder="Total Salary Changes of Applicant" disabled>
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-5">
        <label for="reasonPromottion" class="form-label">Reason for Promotion</label>
        <input type="text" class="form-control" id="reasonPromottion"
            placeholder="Reason for Promotion"> <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-3"></div>
    <div class="mb-3 col-lg-4">
        <label for="recruiterPromotionValidation" class="form-label">Recruiter Validation
            Score</label>
        <input type="text" class="form-control" id="recruiterPromotionValidation"
            placeholder="Recruiter Validation Score" disabled>
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-8">
        <label for="recruiterPromottions" class="form-label">Recruiter Notes Promitions</label>
        <input type="text" class="form-control" id="recruiterPromottions"
            placeholder="Recruiter Notes Promitions" disabled>
        <!-- This is a Input element -->
    </div>
    <div class="col-md-6">

        <label for="salaryIncrease" class="form-label">Did you get any Salary Increase? (Change in
            Salary)</label>

        <div class="col-md-4">
            <select class="custom-select" id="salaryIncrease">
                <option selected>Choose</option>
                <option value="1">Yes</option>
                <option value="2">No</option>
            </select>
        </div>
    </div>
    <div class="mb-3 col-lg-2"></div>
    <div class="mb-3 col-lg-4">
        <label for="tatalSalarychanges" class="form-label">Total Salary Changes of Applicant</label>
        <input type="text" class="form-control" id="tatalSalarychanges"
            placeholder="Total Salary Changes of Applicant" disabled>
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-5">
        <label for="reasonSalaryIncrease" class="form-label">Reason for Salary Increase</label>
        <input type="text" class="form-control" id="reasonSalaryIncrease"
            placeholder="Reason for Salary Increase"> <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-3"></div>
    <div class="mb-3 col-lg-4">
        <label for="recruiterSalaryValidation" class="form-label">Recruiter Validation Score</label>
        <input type="text" class="form-control" id="recruiterSalaryValidation"
            placeholder="Recruiter Validation Score" disabled>
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-8">
        <label for="recruiterPromottionsNotes" class="form-label">Recruiter Notes Promitions</label>
        <input type="text" class="form-control" id="recruiterPromottionsNotes"
            placeholder="Recruiter Notes Promitions" disabled>
        <!-- This is a Input element -->
    </div>
    <div class="col-md-6">

        <label for="leaveJob" class="form-label">Did you leave the job?</label>

        <div class="col-md-4">
            <select class="custom-select" id="leaveJob">
                <option selected>Choose</option>
                <option value="1">Yes</option>
                <option value="2">No</option>
            </select>
        </div>
    </div>
    <div class="mb-3 col-lg-8">
        <label for="leaveJobContent" class="form-label">Why do you plan to leave the job?</label>

        <textarea rows="4" cols="50" name="comment" form="usrform" class="form-control jobContent"
            id="leaveJobContent"></textarea>
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-8">
        <label for="recruiterPromottionsFinalNotes" class="form-label">Recruiter Notes
            Promitions</label>
        <input type="text" class="form-control" id="recruiterPromottionsFinalNotes"
            placeholder="Recruiter Notes Promitions" disabled>
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-8">
        <label for="recruiterPromottionsFinalNotes" class="form-label">Recruiter Notes
            Promitions</label>
        <input type="text" class="form-control" id="recruiterPromottionsFinalNotes"
            placeholder="Recruiter Notes Promitions" disabled>
        <!-- This is a Input element -->
    </div>

    <div class="mb-3 col-lg-4"></div>


</div>`;
};
const addCompany = (isNumberEntered) => {
    console.log("add Company");
    if (isNumberEntered === 'yes') {
        const numberEntered = JSON.parse(valueGetter('numberOfCompaniesNumber'));
        domGetter('numberOfCompaniesNumber').disabled = true;
        domGetter('numberOfCompaniesSubmit').disabled = true;
        window.localStorage.setItem('numberOfCompanies', JSON.stringify(numberEntered));
        for (let i = 1; i <= numberEntered; i += 1)
            domGetter('companyList').innerHTML += returnCompanyDom(i);
    }
    else {
        const oldNumberOfCompanies = JSON.parse(window.localStorage.getItem('numberOfCompanies'));
        const newNumberOfCompanies = oldNumberOfCompanies + 1;
        window.localStorage.setItem('numberOfCompanies', JSON.stringify(newNumberOfCompanies));
        domGetter('companyList').innerHTML += returnCompanyDom(newNumberOfCompanies);
    }
};

const submit = () => {
    console.log("Submit clicked");
};

// Event Listners
domGetter('addCompany').addEventListener("click", function () {
    addCompany();
});
domGetter('numberOfCompaniesSubmit').addEventListener("click", function () {
    addCompany('yes');
});
document.getElementById("submit").addEventListener("click", submit);