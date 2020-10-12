if(window.localStorage.getItem("job-application-auth")){
console.log("ready0");
// frappe.ready(function () {
//     // get_dummy();
//     console.log("ready");
// });
// function get_dummy() {

//     frappe.call({
//         method: 'one_fm.templates.pages.job_application.get_dummy',
//         callback: function (r) {
//             console.log("rr2222", r);
//         }
//     });
// }
// frappe.call('one_fm.templates.pages.job_application.get_dummy', {
//     role_profile: 'Test'
// }).then(r => {
//     console.log(r.message);
// });
// $('.star').hover(function () {
//     $(this).prevAll().andSelf().removeClass('fa-star-o').addClass('fa-star');
// });

// $('.star').mouseout(function () {
//     $(this).prevAll().andSelf().removeClass('fa-star').addClass('fa-star-o');
// });

// $('.star').click(function () {
//     alert($(this).prevAll().length + 1);
// });
// OCR Get Text 
(function () {
    console.log("before");
    const firstName = document.getElementById("firstName");
    const secondName = document.getElementById("secondName");
    const thirdName = document.getElementById("thirdName");
    const email = document.getElementById("email");
    const civilIdElement = document.getElementById("civilId");
    const civilValidTill = document.getElementById("civilValidTill");
    const dob = document.getElementById("dob");
    const passport = document.getElementById("PassportNumber");
    console.log("after", civilIdElement);
    var patternForCivilIdNumber = new RegExp("^\\d{12}$");
    var patternForPassportNumber = new RegExp("([A-Z])\w+");
    const placeText = () => {
        if (window.localStorage.getItem("civilId")) {
            const civilId = window.localStorage.getItem("civilId");
            console.log("extracted civil id", civilId);
            let splited = civilId.split(" ");
            var filtered = splited.filter(function (el) {
                return el != null && el != "";
            });
            console.log(filtered);
            filtered.reduce((acc, cur, currentIndex, array) => {
                let loweredCurrent = cur.toLocaleLowerCase();
                if (cur.match(patternForCivilIdNumber)) {
                    civilIdElement.value = cur;
                }
                if (loweredCurrent.includes("name")) {
                    console.log(cur.slice(4).split('\n')[0]);
                    firstName.value = cur.slice(4).split('\n')[0];
                }
                if (loweredCurrent.includes("passport") || loweredCurrent.includes("passportno") || loweredCurrent.includes("pass") || loweredCurrent.includes("tno") || loweredCurrent.includes("assport")) {
                    let passportNumber = array[currentIndex + 1];
                    if (passportNumber.toLocaleLowerCase() == "no")
                        passportNumber = array[currentIndex + 2];
                    passportNumber = passportNumber.replace(/[^A-Za-z0-9]/g, "");
                    console.log(passportNumber);
                    passport.value = passportNumber;
                }
                if (loweredCurrent.includes("birth") || loweredCurrent.includes("bith") || loweredCurrent.includes("brth") || loweredCurrent.includes("hdate") || loweredCurrent.includes("BithDate")) {
                    let dateOfBirth = array[currentIndex + 1];
                    if (dateOfBirth.charAt(0) == "(") {
                        dateOfBirth = dateOfBirth.slice(1);
                        dateOfBirth = `0${dateOfBirth}`;
                    }
                    let newdate = dateOfBirth.split("/").reverse().join("-");
                    dob.defaultValue = newdate;
                }
                if (loweredCurrent.includes("expiryDate") || loweredCurrent.includes("expiry") || loweredCurrent.includes("exp") || loweredCurrent.includes("ydate")) {
                    console.log(array[currentIndex + 1]);
                    let dateOfCivilIdExpiry = array[currentIndex + 1];
                    if (dateOfCivilIdExpiry.charAt(0) == "(") {
                        dateOfCivilIdExpiry = dateOfCivilIdExpiry.slice(1);
                        dateOfCivilIdExpiry = `0${dateOfCivilIdExpiry}`;
                    }
                    let newdate = dateOfCivilIdExpiry.split("/").reverse().join("-");
                    civilValidTill.defaultValue = newdate;
                }
                // console.log("accumulator", acc);
                // console.log("current", cur);
                // console.log("currentIndex", currentIndex);
                // console.log("array", array);
            });
        }
        if (localStorage.getItem("gName") && localStorage.getItem("gEmail")) {
            let name = localStorage.getItem("gName").split(" ");
            console.log("Google Details", name);
            email.value = localStorage.getItem("gEmail");
            firstName.value = name[0] ? name[0] : "";
            secondName.value = name[1] ? name[1] : "";
            thirdName.value = name[2] ? name[2] : "";
            thirdName.value += " " + (name[3] ? name[3] : "");
            thirdName.value += " " + (name[4] ? name[4] : "");
        }
        if (localStorage.getItem("linkedInData")) {
            let data = JSON.parse(localStorage.getItem("linkedInData"));
            console.log("linkedin data",data);
        if(!data.data.error){
            firstName.value = data.data.firstName?.localized.en_US;
            thirdName.value = data.data.lastName?.localized.en_US;
        }
        }
    };
    const star = document.getElementsByClassName("star");
    const addStars = (e) => {
        for (i = 4; i >= 0; i--)
            star[i].innerHTML = "☆";
        console.log("e", e.target.dataset.star);
        console.log("star", star);
        console.log(star[e.target.id]);
        for (i = 4; i >= e.target.id; i--)
            star[i].innerHTML = "★";
        // console.log(star[i].innerHTML);

    };

    Array.from(star).forEach(function (element) {
        element.addEventListener('click', addStars);
    });
    console.log(star);
    placeText();
})();

const addNewLanguage = () => {
    const languageContainer = document.getElementById("language-input");
    languageContainer.innerHTML += `<div>
                                            <div class="col-md-8">
                                                <select class="form-control" name="religion" id="religion">
                                                    <option value="blank"></option>
                                                    <option value="Islam">English</option>
                                                    <option value="Christianity">Arabic</option>
                                                    <option value="Hinduism">Hindi</option>
                                                    <option value="Other">Malayalam</option>
                                                    <option value="Other">Tamil</option>
                                                    <option value="Other">Other</option>
                                                </select>
                                            </div>
                                            <div class="col-md-4">
                                                <div class="rating" id="rating">
                                                    <span id="0" data-star="5" class="star">☆</span><span id="1"
                                                        data-star="4" class="star">☆</span><span id="2" data-star="3"
                                                        class="star">☆</span><span id="3" data-star="2"
                                                        class="star">☆</span><span id="4" data-star="1"
                                                        class="star">☆</span>
                                                </div>
                                            </div>
                                        </div>`;
    console.log("language added");
};
// console.log("user logged in", frappe.is_user_logged_in());
// frappe.call({
//     method: 'one_fm.templates.pages.job_application.get_dummy',
//     callback: function (r) {
//         console.log("r", r);
//         if (r) {
//             console.log("r", r);
//         }
//     }
// });

const addNewSkill = () => {
    const skillInput = document.getElementById("skill-input");
    const skillsList = document.getElementById("skills-list");
    skillsList.innerHTML += ` <p>${skillInput.value}</p>`;
    skillInput.value = "";
};
}
else {
    alert("Please Signup or Login!");
    window.location = "applicant-sign-up";
}