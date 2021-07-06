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
window.localStorage.setItem('numberOfCompanies', JSON.stringify(0));
// Values has to be set from the Backend
// valueSetter('erfNumber', '987654321');
// valueSetter('applicantId', '12345');
// valueSetter('historyScore', '75');
// valueSetter('Promotions', '2');


// Commenting for Errors, will resolve in future
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
    <div class="col-md-12">
    <h4>Company <span>${companyNumber}</span> </h4>
</div>
<div class="mb-3 col-lg-4">
    <label for="companyName" class="form-label">Current Company Name </label>
    <input type="text" class="form-control" id="companyName${companyNumber}"
        placeholder="Enter the Company Name">
    <!-- This is a Input element -->
</div>
<div class="mb-3 col-lg-4 ">
    <label for="monthlySalary" class="form-label">Monthly Salary in $ </label>
    <input type="number" class="form-control" id="monthlySalary${companyNumber}"
        placeholder="Enter the Salary"> <!-- This is a Input element -->
</div>

<div class="mb-3 col-lg-4 ">
    <label for="jobTitle" class="form-label">Current Job Title</label>
    <input type="text" class="form-control" id="jobTitle${companyNumber}"
        placeholder="Enter the Job Title">
    <!-- This is a Input element -->
</div>
<div class="mb-3 col-lg-4 ">
    <label for="startDate" class="form-label">Job Start Date</label>
    <input type="date" class="form-control" id="startDate${companyNumber}">
    <!-- This is a Input element -->
</div>
<div class="mb-3 col-lg-4">
    <label for="endDate" class="form-label">End Date</label>
    <input type="date" class="form-control" id="endDate${companyNumber}">
    <!-- This is a Input element -->
</div>
<div class="mb-3 col-lg-4 ">
    <label for="totalExperiance" class="form-label">Years Of Experience</label>
    <input type="text" class="form-control" id="totalExperiance${companyNumber}"
        placeholder="Number" disabled>
    <!-- This is a Input element -->
</div>
<div class="mb-3 col-lg-6">
    <label for="opportunityjobContent" class="form-label">Could you please tell us what is it
        that makes
        you interested in this opportunity?</label>
    <textarea rows="4" cols="50" name="comment" form="usrform" class="form-control jobContent"
        id="opportunityjobContent${companyNumber}"></textarea>
    <!-- This is a Input element -->
</div>
<div class=" col-lg-6">
    <label for="Responisbilities" class="form-label">What are your top 3
        Responisbilities?</label>
    <input type="text" class="form-control mb-3" id="Responisbilities${companyNumber}"
        placeholder="1">
    <!-- This is a Input element -->
    <input type="text" class="form-control mb-3" id="Responisbilities${companyNumber}"
        placeholder="2">
    <input type="text" class="form-control" id="Responisbilities${companyNumber}"
        placeholder="3">
</div>

<div class="col-lg-12">
    <hr class="my-5">
</div>
<div class="col-lg-6">
    <h4>Did you get any Promotion?</h4>
    <select class="custom-select anyPromotionSelect" id="anyPromotion${companyNumber}">
        <option selected>Choose</option>
        <option value="1">Yes</option>
        <option value="2">No</option>
    </select>
</div>

<div class="mb-3 col-lg-6" id="totalPromotionsContainer${companyNumber}" style="opacity: 0">
    <label for="totalPromotions" class="form-label">Total Promotions of Applicant</label> <br>
    <div class="row">
        <div class="col-6"><input type="number" class="form-control total" id="totalPromotions${companyNumber}" placeholder="Choose"></div>
        <div class="col-6"> <button class="btn btn-primary" id="totalPromotionsSubmit${companyNumber}">submit</button></div>
    </div>
</div>
<div class="col-lg-12" id="promotionsData${companyNumber}">
    <!-- All the Promotions based fields will be rendered here -->
</div>
<div class="col-lg-12">
    <hr class="my-5">
</div>
<div class="col-lg-6">
    <h4>Did you get any Salary Increase? (Change in
        Salary)</h4> 
    <select class="custom-select anySalaryIncrease" id="salaryIncrease${companyNumber}">
        <option selected>Choose</option>
        <option value="1">Yes</option>
        <option value="2">No</option>
    </select>
</div>
<div class="mb-3 col-lg-6" id="totalSalaryChangesContainer${companyNumber}" style="opacity: 0">
    <label for="tatalSalarychanges" class="form-label">Total Salary Changes of Applicant</label> <br>
    <div class="row">
        <div class="col-6"><input type="number" class="form-control total" id="totalSalaryChanges${companyNumber}" placeholder="Choose"></div>
        <div class="col-6"> <button class="btn btn-primary" id="totalSalaryChangesSubmit${companyNumber}">submit</button></div>
    </div>
</div>
<div class="col-lg-12" id="salaryChangesData${companyNumber}">
    <!-- All the Salary changes based fields will be rendered here -->
</div>
<div class="col-lg-12">
    <hr class="my-5">
</div>


<div class="col-lg-6">

    <h4>Did you leave the job?</h4>
    <select class="custom-select anyDidYouLeaveTheJob" id="leaveJob${companyNumber}">
        <option selected>Choose</option>
        <option value="1">Yes</option>
        <option value="2">No</option>
    </select>
</div>

<div class="mb-3 mt-3 col-lg-12" id="didYouLeaveTheJobDescription${companyNumber}" style="display: none">
    <label for="leaveJobContent" class="form-label">Why do you plan to leave the job?</label>

    <textarea rows="4" cols="50" name="comment" form="usrform" class="form-control jobContent"
        id="leaveJobContent${companyNumber}"></textarea>
    <!-- This is a Input element -->
</div>
<div class="col-lg-12 mt-3">
    <div class="row">
    <div class="mb-3  col-lg-6">
        <label for="recruiterPromottionsFinalNotes" class="form-label">Shoves</label>
        <input type="text" class="form-control" id="recruiterPromottionsFinalNotes${companyNumber}"
            placeholder="Shoves" disabled>
        <!-- This is a Input element -->
    </div>
    <div class="mb-3  col-lg-6">
        <!-- This is a Input element -->
        <label for="recruiterPromottionsFinalNotes" class="form-label">Tugs</label>
        <input type="text" class="form-control" id="recruiterPromottionsFinalNotes${companyNumber}"
            placeholder="Tugs" disabled>
    </div>
    </div>
</div>
<div class="col-lg-12">
    <hr class="my-5">
</div>
</div>`;
};
const promotionsDomRenderer = (companyNumber) => {
    return `<div class="mb-3 col-lg-6">
        <label for="reasonPromottion" class="form-label">Reason for Promotion</label>
        <input type="text" class="form-control" id="reasonPromottion${companyNumber}"
            placeholder="Reason for Promotion"> <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-3">
        <label for="recruiterPromottions" class="form-label">Recruiter Notes Promitions</label>
        <input type="text" class="form-control" id="recruiterPromottions${companyNumber}"
            placeholder="Recruiter Notes Promitions" disabled>
        <!-- This is a Input element -->
    </div>
    <div class="mb-3 col-lg-3">
        <label for="recruiterPromotionValidation" class="form-label">Recruiter Validation
            Score</label>
        <input type="text" class="form-control" id="recruiterPromotionValidation${companyNumber}"
            placeholder="Recruiter Validation Score" disabled>
        <!-- This is a Input element -->
    </div>
`;
};
const salaryChangesDomRenderer = (companyNumber) => {
    return `<div class="mb-3 col-lg-6">
    <label for="reasonSalaryIncrease" class="form-label">Reason for Salary Increase</label>
    <input type="text" class="form-control" id="reasonSalaryIncrease${companyNumber}"
        placeholder="Reason for Salary Increase"> <!-- This is a Input element -->
</div>

<div class="mb-3 col-lg-3">
    <label for="recruiterPromottionsNotes" class="form-label">Recruiter Notes Promitions</label>
    <input type="text" class="form-control" id="recruiterPromottionsNotes${companyNumber}"
        placeholder="Recruiter Notes Promitions" disabled>
    <!-- This is a Input element -->
</div>
<div class="mb-3 col-lg-3">
    <label for="recruiterSalaryValidation" class="form-label">Recruiter Validation Score</label>
    <input type="text" class="form-control" id="recruiterSalaryValidation${companyNumber}"
        placeholder="Recruiter Validation Score" disabled>
    <!-- This is a Input element -->
</div>
`;
};
const addCompany = (isNumberEntered) => {
    console.log("add Company");
    if (isNumberEntered === 'yes') {
        if (domGetter('CompanyList1') != null) {
            alert('Already Entered Data will be lost!');
        }
        domGetter('companyList').innerHTML = '';
        window.localStorage.setItem('numberOfCompanies', JSON.stringify(0));
        const numberEntered = JSON.parse(valueGetter('numberOfCompaniesNumber'));
        domGetter('numberOfCompaniesNumber').disabled = true;
        domGetter('numberOfCompaniesSubmit').disabled = true;
        window.localStorage.setItem('numberOfCompanies', JSON.stringify(numberEntered));
        for (let i = 1; i <= numberEntered; i += 1) {
            domGetter('companyList').innerHTML += returnCompanyDom(i);
        }
    }
    else {
        const oldNumberOfCompanies = JSON.parse(window.localStorage.getItem('numberOfCompanies'));
        const newNumberOfCompanies = oldNumberOfCompanies + 1;
        window.localStorage.setItem('numberOfCompanies', JSON.stringify(newNumberOfCompanies));
        let div = document.createElement("div");
        div.id = `CompanyList${newNumberOfCompanies}`;
        div.className = 'row';
        div.innerHTML = returnCompanyDom(newNumberOfCompanies);
        domGetter('companyList').append(div);
        // domGetter('companyList').innerHTML += returnCompanyDom(newNumberOfCompanies);
    }
    const anyPromotionSelect = document.getElementsByClassName('anyPromotionSelect');
    const anySalaryIncrease = document.getElementsByClassName('anySalaryIncrease');
    const anyDidYouLeaveTheJob = document.getElementsByClassName('anyDidYouLeaveTheJob');
    for (let i = 0; i < anyPromotionSelect.length; i += 1) {
        anyPromotionSelect[i].addEventListener("click", onPromotionClick);
    }
    for (let i = 0; i < anySalaryIncrease.length; i += 1) {
        anySalaryIncrease[i].addEventListener("click", onSalaryIncreaseClick);
    }
    for (let i = 0; i < anyDidYouLeaveTheJob.length; i += 1) {
        anyDidYouLeaveTheJob[i].addEventListener("click", onDidYouLeaveJobClick);
    }
};

const onPromotionClick = (e) => {
    const id = e.target.id.slice(-1);
    const selectedValue = e.target[e.target.selectedIndex].value;
    if (selectedValue == 1) {
        domGetter(`totalPromotionsContainer${id}`).style.opacity = 1;
        domGetter(`totalPromotionsSubmit${id}`).addEventListener("click", function () {
            renderPromotionFields(id);
        });
    }
};
const onSalaryIncreaseClick = (e) => {
    const id = e.target.id.slice(-1);
    const selectedValue = e.target[e.target.selectedIndex].value;
    if (selectedValue == 1) {
        domGetter(`totalSalaryChangesContainer${id}`).style.opacity = 1;
        domGetter(`totalSalaryChangesSubmit${id}`).addEventListener("click", function () {
            renderSalaryChangesFields(id);
        });
    }
};
const onDidYouLeaveJobClick = (e) => {
    const id = e.target.id.slice(-1);
    const selectedValue = e.target[e.target.selectedIndex].value;
    if (selectedValue == 1) {
        domGetter(`didYouLeaveTheJobDescription${id}`).style.display = 'inline';
    }
};

const renderPromotionFields = (id) => {
    const value = valueGetter(`totalPromotions${id}`);
    if (value) {
        console.log("yes value", value, id);
        domGetter(`promotionsData${id}`).innerHTML = '';
        for (let i = 1; i <= value; i += 1) {
            let div = document.createElement("div");
            div.id = `promotionField${id}`;
            div.className = 'row';
            div.innerHTML = promotionsDomRenderer(id);
            // <div class="row" id="promotionField${companyNumber}"> promotionsDomRenderer
            domGetter(`promotionsData${id}`).append(div);
        }
    }
    else {
        alert('Please enter some value to Fill details about your Promotion');
    }
};
const renderSalaryChangesFields = (id) => {
    const value = valueGetter(`totalSalaryChanges${id}`);
    if (value) {
        console.log("yes value", value, id);
        domGetter(`salaryChangesData${id}`).innerHTML = '';
        for (let i = 1; i <= value; i += 1) {
            let div = document.createElement("div");
            div.id = `totalSalaryField${id}`;
            div.className = 'row';
            div.innerHTML = salaryChangesDomRenderer(id);
            // <div class="row" id="promotionField${companyNumber}"> promotionsDomRenderer
            domGetter(`salaryChangesData${id}`).append(div);
        }
    }
    else {
        alert('Please enter some value to Fill details about your Promotion');
    }
};

const submit = () => {
    console.log("Submit clicked");
    let totalExp = 0;
    const numberOfCompanies = JSON.parse(window.localStorage.getItem('numberOfCompanies'));
    for (let i = 1; i <= numberOfCompanies; i += 1) {
        const endDate = moment(valueGetter(`endDate${i}`));
        const startDate = moment(valueGetter(`startDate${i}`));
        totalExp += JSON.parse(endDate.diff(startDate, 'years', true).toFixed(2));
        valueSetter(`totalExperiance${i}`, endDate.diff(startDate, 'years', true).toFixed(2));
        console.log('val', endDate.diff(startDate, 'years', true).toFixed(2));
    }
    valueSetter('Experience', totalExp);
};

// Event Listners anyPromotion1

domGetter('addCompany').addEventListener("click", function () {
    addCompany();
});
domGetter('numberOfCompaniesSubmit').addEventListener("click", function () {
    addCompany('yes');
});
document.getElementById("submit").addEventListener("click", submit);