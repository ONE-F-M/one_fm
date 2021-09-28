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

var special = ['zeroth', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth', 'thirteenth', 'fourteenth', 'fifteenth', 'sixteenth', 'seventeenth', 'eighteenth', 'nineteenth'];
var deca = ['twent', 'thirt', 'fort', 'fift', 'sixt', 'sevent', 'eight', 'ninet'];

function stringifyNumber(n) {
    if (n < 20) return special[n];
    if (n % 10 === 0) return deca[Math.floor(n / 10) - 2] + 'ieth';
    return deca[Math.floor(n / 10) - 2] + 'y-' + special[n % 10];
}

const returnCompanyDom = (companyNumber) => {
    return `<div class="col-lg-12 col-md-12 mb-3">
    <h3>${companyNumber == 1 ? 'So' : 'And'}, Hassan Which is your <span id="companyNumberInString">${stringifyNumber(companyNumber)}</span> Company you worked on?</h3>
</div>
<div class="mb-3 col-lg-6 col-md-6">
    <label for="companyName" class="form-label">First Company Name </label>
    <input type="text" class="form-control" id="companyName${companyNumber}"
        placeholder="Enter the First Company Name">

</div>
<div class="mb-3 col-lg-6 col-md-6">
    <label for="companyName" class="form-label">Where is it Located? </label> <br>
    <select class="custom-select" id="location${companyNumber}">
        <option selected>Choose</option>
        <option value="1">India</option>
        <option value="2">kuwait</option>
    </select>
</div>
<div class="mb-3 col-lg-6 col-md-6">
    <label for="companyName" class="form-label">When Do you Joined that company</label>
    <input type="date" class="form-control" id="companyName${companyNumber}"
        placeholder="Country Dropdown">

</div>
<div class="mb-3 col-lg-6 col-md-6">
    <label for="howMuchDidYouGotPaid${companyNumber}" class="form-label">How much did you got paid?</label>
    <input type="text" class="form-control" id="howMuchDidYouGotPaid${companyNumber}"
        placeholder="Enter the Salary">

</div>
<div class=" col-lg-12 col-md-12">
    <label for="Responisbilities" class="form-label">What are your top 3
        Responisbilities?</label>
    <input type="text" class="form-control mb-3" id="Responisbilities${companyNumber}"
        placeholder="1">
    <!-- This is a Input element -->
    <input type="text" class="form-control mb-3" id="Responisbilities${companyNumber}"
        placeholder="2">
    <input type="text" class="form-control" id="Responisbilities${companyNumber}" placeholder="3">
</div>
<div class="col-lg-12 col-md-12">
    <hr class="my-5">
</div>
<div class="mb-3 col-lg-6 col-md-6">
    <h4 for="companyName" class="form-label">What was your Starting Job Title?</h4>
    <input type="text" class="form-control" id="companyName${companyNumber}"
        placeholder="Enter the Job Title">
</div>
<div class="col-lg-12 col-md-12 mb-3">
    <h4>Your Promotions/Salary Increase</h4>
</div>
<div style="width: 100%" id="promotionOrSalaryContainer${companyNumber}">
    <div class=" col-lg-12 col-md-12">
        <!-- <label for="companyName" class="form-label">Did You Only Got a Salary Increase?</label> <br> -->
        <select class="custom-select anyPromotionOrSalaryClick" id="salaryIncrease${companyNumber}">
            <option value="1" selected>Did You Got a Promotion with a Salary Increase?</option>
            <option value="2">Did You Only Got a Promotion?</option>
            <option value="3">Did You Only Got a Salary Increase?</option>
        </select>
    </div>
    <div class="row" style="width: 100%; display: flex" id="promotionWithSalary${companyNumber}">
        <div class="my-5 col-lg-6 col-md-6">
            <label for="promotionInput${companyNumber}" class="form-label">Reason for Promotion</label>
            <input type="text" class="form-control" id="promotionInput${companyNumber}"
                placeholder="Enter the Reason for Your Promotion">

        </div>
        <div class="my-5 col-lg-6 col-md-6">
            <label for="increasedSalary${companyNumber}" class="form-label">What is Your Increased Salary in KWD?</label>
            <input type="text" class="form-control" id="increasedSalary${companyNumber}"
                placeholder="Enter your increased Salary in KWD">

        </div>
        <div class="mb-5 col-lg-6 col-md-6">
            <label for="whenDoYouGotPromoted${companyNumber}" class="form-label">When Do you got Promoted?</label>
            <input type="date" class="form-control" id="whenDoYouGotPromoted${companyNumber}">

        </div>
    </div>
    <div class="row" style="width: 100%; display: none" id="promotion${companyNumber}">
        <div class="my-5 col-lg-6 col-md-6">
            <label for="promotionOnlyInput${companyNumber}" class="form-label">Reason for Promotion</label>
            <input type="text" class="form-control" id="promotionOnlyInput${companyNumber}"
                placeholder="Enter the Reason for Your Salary Increase">

        </div>
        <div class="my-5 col-lg-6 col-md-6">
            <label for="whenDoYouGotPromotedOnly${companyNumber}" class="form-label">When Do you got Promoted?</label>
            <input type="date" class="form-control" id="whenDoYouGotPromotedOnly${companyNumber}">

        </div>
    </div>
    <div class="row" style="width: 100%; display: none" id="salary${companyNumber}">
        <div class="my-5 col-lg-6 col-md-6">
            <label for="reasonFOrSalaryIncrease${companyNumber}" class="form-label">Reason for Salary Increase</label>
            <input type="text" class="form-control" id="reasonFOrSalaryIncrease${companyNumber}"
                placeholder="Enter the Reason for Your Salary Increase">

        </div>
        <div class="my-5 col-lg-6 col-md-6">
            <label for="increasedSalaryOnly${companyNumber}" class="form-label">What is Your Increased Salary in KWD?</label>
            <input type="text" class="form-control" id="increasedSalaryOnly${companyNumber}"
                placeholder="Enter your increased Salary in KWD">

        </div>
        <div class="mb-5 col-lg-6 col-md-6">
            <label for="whenDoYouGotSalaryIncrease${companyNumber}" class="form-label">When Do you got your Salary Increase?</label>
            <input type="date" class="form-control" id="whenDoYouGotSalaryIncrease${companyNumber}">

        </div>
    </div>
</div>

<div class="col-lg-12 col-md-12 text-center">
    <button class="btn btn-primary anyPromotionSelect" data-numberOfElements="1" id="addPromotionsAndSalary${companyNumber}">Add +</button>
</div>

<div class="col-lg-12 col-md-12">
    <hr class="my-5">
</div>
<div class="col-lg-12 col-md-12 mb-3">
    <h3>Are You still working for the Company?</h3>
    <select class="custom-select anyDidYouLeaveTheJob" id="didYouLeaveTheJob${companyNumber}">
        <option selected>Choose</option>
        <option value="1">Yes</option>
        <option value="2">No</option>
    </select>
</div>
<div class="col-lg-12 col-md-12" id="didYouLeaveTheJobDescription${companyNumber}" style="display: none">
    <label for="leaveJobContent" class="form-label">Why do you plan to leave the job?</label>

    <textarea rows="4" cols="50" name="comment" form="usrform" class="form-control jobContent"
        id="leaveJobContent${companyNumber}"></textarea>
    <!-- This is a Input element -->
</div>
<div class="col-lg-12 col-md-12">
    <hr class="my-5">
</div>`;
};
const promotionsDomRenderer = (companyNumber) => {
    return `<div class=" col-lg-12 col-md-12">
    <!-- <label for="companyName" class="form-label">Did You Only Got a Salary Increase?</label> <br> -->
    <select class="custom-select anyPromotionOrSalaryClick" id="salaryIncrease${companyNumber}">
        <option value="1" selected>Did You Got a Promotion with a Salary Increase?</option>
        <option value="2">Did You Only Got a Promotion?</option>
        <option value="3">Did You Only Got a Salary Increase?</option>
    </select>
</div>
<div class="row" style="width: 100%; display: flex" id="promotionWithSalary${companyNumber}">
    <div class="my-5 col-lg-6 col-md-6">
        <label for="promotionInput${companyNumber}" class="form-label">Reason for Promotion</label>
        <input type="text" class="form-control" id="promotionInput${companyNumber}"
            placeholder="Enter the Reason for Your Promotion">

    </div>
    <div class="my-5 col-lg-6 col-md-6">
        <label for="increasedSalary${companyNumber}" class="form-label">What is Your Increased Salary in KWD?</label>
        <input type="text" class="form-control" id="increasedSalary${companyNumber}"
            placeholder="Enter your increased Salary in KWD">

    </div>
    <div class="mb-5 col-lg-6 col-md-6">
        <label for="whenDoYouGotPromoted${companyNumber}" class="form-label">When Do you got Promoted?</label>
        <input type="date" class="form-control" id="whenDoYouGotPromoted${companyNumber}">

    </div>
</div>
<div class="row" style="width: 100%; display: none" id="promotion${companyNumber}">
    <div class="my-5 col-lg-6 col-md-6">
        <label for="promotionOnlyInput${companyNumber}" class="form-label">Reason for Promotion</label>
        <input type="text" class="form-control" id="promotionOnlyInput${companyNumber}"
            placeholder="Enter the Reason for Your Salary Increase">

    </div>
    <div class="my-5 col-lg-6 col-md-6">
        <label for="whenDoYouGotPromotedOnly${companyNumber}" class="form-label">When Do you got Promoted?</label>
        <input type="date" class="form-control" id="whenDoYouGotPromotedOnly${companyNumber}">

    </div>
</div>
<div class="row" style="width: 100%; display: none" id="salary${companyNumber}">
    <div class="my-5 col-lg-6 col-md-6">
        <label for="reasonFOrSalaryIncrease${companyNumber}" class="form-label">Reason for Salary Increase</label>
        <input type="text" class="form-control" id="reasonFOrSalaryIncrease${companyNumber}"
            placeholder="Enter the Reason for Your Salary Increase">

    </div>
    <div class="my-5 col-lg-6 col-md-6">
        <label for="increasedSalaryOnly${companyNumber}" class="form-label">What is Your Increased Salary in KWD?</label>
        <input type="text" class="form-control" id="increasedSalaryOnly${companyNumber}"
            placeholder="Enter your increased Salary in KWD">

    </div>
    <div class="mb-5 col-lg-6 col-md-6">
        <label for="whenDoYouGotSalaryIncrease${companyNumber}" class="form-label">When Do you got your Salary Increase?</label>
        <input type="date" class="form-control" id="whenDoYouGotSalaryIncrease${companyNumber}">

    </div>
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

const addCompany = () => {
    console.log("add Company");
    const oldNumberOfCompanies = JSON.parse(window.localStorage.getItem('numberOfCompanies'));
    const newNumberOfCompanies = oldNumberOfCompanies + 1;
    window.localStorage.setItem('numberOfCompanies', JSON.stringify(newNumberOfCompanies));
    let div = document.createElement("div");
    div.id = `CompanyList${newNumberOfCompanies}`;

    div.className = 'row';
    div.innerHTML = returnCompanyDom(newNumberOfCompanies);
    domGetter('companyList').append(div);
    // domGetter('companyList').innerHTML += returnCompanyDom(newNumberOfCompanies);

    const anyPromotionSelect = document.getElementsByClassName('anyPromotionSelect');
    const anyDidYouLeaveTheJob = document.getElementsByClassName('anyDidYouLeaveTheJob');
    const anyPromotionOrSalaryClick = document.getElementsByClassName('anyPromotionOrSalaryClick');
    for (let i = 0; i < anyPromotionSelect.length; i += 1) {
        anyPromotionSelect[i].addEventListener("click", onPromotionClick);
    }
    for (let i = 0; i < anyDidYouLeaveTheJob.length; i += 1) {
        anyDidYouLeaveTheJob[i].addEventListener("click", onDidYouLeaveJobClick);
    }
    for (let i = 0; i < anyPromotionOrSalaryClick.length; i += 1) {
        anyPromotionOrSalaryClick[i].addEventListener("click", onPromotionOrSalaryClick);
    }
};

const onPromotionClick = (e) => {
    console.log("came inside");
    const id = e.target.id.slice(-1);
    let count = Number(e.target.dataset.numberofelements) + 1;
    alert(id);
    let div = document.createElement("div");
    div.id = `promotionField${id}`;
    div.className = 'row';
    div.innerHTML = promotionsDomRenderer(count);
    domGetter(`promotionOrSalaryContainer${id}`).append(div);

    const anyPromotionOrSalaryClick = document.getElementsByClassName('anyPromotionOrSalaryClick');
    console.log(anyPromotionOrSalaryClick);
    for (let i = 0; i < anyPromotionOrSalaryClick.length; i += 1) {
        anyPromotionOrSalaryClick[i].addEventListener("click", onPromotionOrSalaryClick);
    }
    e.target.dataset.numberofelements = count;
};
const onDidYouLeaveJobClick = (e) => {
    const id = e.target.id.slice(-1);
    const selectedValue = e.target[e.target.selectedIndex].value;
    if (selectedValue == 1) {
        domGetter(`didYouLeaveTheJobDescription${id}`).style.display = 'inline';
    }
    if (selectedValue == 2) {
        domGetter(`didYouLeaveTheJobDescription${id}`).style.display = 'none';
    }
};
const onPromotionOrSalaryClick = (e) => {
    const id = e.target.id.slice(-1);
    const selectedValue = e.target[e.target.selectedIndex].value;
    if (selectedValue == 1) {
        domGetter(`promotion${id}`).style.display = 'none';
        domGetter(`salary${id}`).style.display = 'none';
        domGetter(`promotionWithSalary${id}`).style.display = 'flex';
    }
    if (selectedValue == 2) {
        domGetter(`promotionWithSalary${id}`).style.display = 'none';
        domGetter(`salary${id}`).style.display = 'none';
        domGetter(`promotion${id}`).style.display = 'flex';
    }
    if (selectedValue == 3) {
        domGetter(`promotion${id}`).style.display = 'none';
        domGetter(`promotionWithSalary${id}`).style.display = 'none';
        domGetter(`salary${id}`).style.display = 'flex';
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
document.getElementById("submit").addEventListener("click", submit);
