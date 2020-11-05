const baseUrl = "http://dev.one-fm.com"
if(window.localStorage.getItem("job-application-auth")){
    const ERF = localStorage.getItem("currentJobOpening");
    const basicSkills = "basic-skills";
    const language = "rating";
    if(!ERF){
        alert("Please Select a Job Posting before continuing");
        window.location = "job_opening";
    }
    console.log(ERF)
    fetch(`${baseUrl}/api/resource/ERF/${ERF}`, {
        // headers: {
        //     'Authorization': 'token 57f152ebd8b9af5:50fe35e6c122253'
        // }
        body: JSON.stringify({
            usr: 'h.marzooq@armor-services.com',
            pwd: 'hassarah420024703307786'
        })
    })
    .then(r => r.json())
    .then(erf => {
    console.log("ERF",erf);
    console.log("ERF",erf.data.designation_skill);
    erf.data.designation_skill.map(a=>{
        placeSkills(basicSkills, a.skill)
    })
    starEffects()
    
})
// Place Skills
const placeSkills = (location, skill="none") => {
    
    document.getElementById(location).innerHTML += ` <div class="form-group col-md-6">
    ${skill != "none" ? `<p>${skill}</p>` : `<select class="form-control" name="religion" id="religion">
    <option value="blank"></option>
    <option value="Islam">English</option>
    <option value="Christianity">Arabic</option>
    <option value="Hinduism">Hindi</option>
    <option value="Other">Malayalam</option>
    <option value="Other">Tamil</option>
    <option value="Other">Other</option>
</select>`}
</div>
<div class="form-group col-md-6">
    <div class='rating-stars'>
        <ul id='stars'>
            <li class='star' title='Poor' data-value='1'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' title='Fair' data-value='2'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' title='Good' data-value='3'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' title='Excellent' data-value='4'>
                <i class='fa fa-star fa-fw'></i>
            </li>
            <li class='star' title='WOW!!!' data-value='5'>
                <i class='fa fa-star fa-fw'></i>
            </li>
        </ul>
    </div>
</div>`
}
placeSkills(language)
// Auto complete scripts
    $( function() {
        let availableTags = [
          "Married"
        ];
        $( "#tags" ).autocomplete({
          source: availableTags
        });
      } );
console.log("ready0");

// Star Component
const starEffects = () =>{
  
    /* 1. Visualizing things on Hover - See next part for action on click */
    $('#stars li').on('mouseover', function(){
      var onStar = parseInt($(this).data('value'), 10); // The star currently mouse on
     
      // Now highlight all the stars that's not after the current hovered star
      $(this).parent().children('li.star').each(function(e){
        if (e < onStar) {
          $(this).addClass('hover');
        }
        else {
          $(this).removeClass('hover');
        }
      });
      
    }).on('mouseout', function(){
      $(this).parent().children('li.star').each(function(e){
        $(this).removeClass('hover');
      });
    });
    
    
    /* 2. Action to perform on click */
    $('#stars li').on('click', function(){
      var onStar = parseInt($(this).data('value'), 10); // The star currently selected
      var stars = $(this).parent().children('li.star');
      
      for (i = 0; i < stars.length; i++) {
        $(stars[i]).removeClass('selected');
      }
      
      for (i = 0; i < onStar; i++) {
        $(stars[i]).addClass('selected');
      }
      
      // JUST RESPONSE (Not needed)
      var ratingValue = parseInt($('#stars li.selected').last().data('value'), 10);
      var msg = "";
      if (ratingValue > 1) {
          msg = "Thanks! You rated this " + ratingValue + " stars.";
      }
      else {
          msg = "We will improve ourselves. You rated this " + ratingValue + " stars.";
      }
      console.log("star", onStar)
    });
    
}

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
    

    placeText();
})();
// Submit
async function postData(url = '', data = {}) {
    // Default options are marked with *
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        "Accept": "application/json",
        'Content-Type': 'application/json',
        'Authorization': 'token 57f152ebd8b9af5:50fe35e6c122253'      
      },     
      body: JSON.stringify(data) 
    });
    return response.json(); // parses JSON response into native JavaScript objects
  }
const submitForm = () => {
    console.log("submited");
    postData(`${baseUrl}/api/resource/Job Applicant`, { "ERF": "ERF-2020-00004", "First Name": "Hassan"})
  .then(data => {
    console.log("post data",data); 
  });
    fetch(`${baseUrl}/api/resource/Job Applicant`, {
        // headers: {
        //     'Authorization': 'token 57f152ebd8b9af5:50fe35e6c122253'
        // }
        body: JSON.stringify({
            usr: 'h.marzooq@armor-services.com',
            pwd: 'hassarah420024703307786'
        })
    })
    .then(r => r.json())
    .then(erf => {
    console.log("ERFFInel",erf);    
    
})
}
document.getElementById("submitBtn").addEventListener("click", submitForm);

}
else {
    alert("Please Signup or Login!");
    window.location = "applicant-sign-up";
}