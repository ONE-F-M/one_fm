function onSignIn(googleUser) {
    var profile = googleUser.getBasicProfile();
    // console.log('ID: ' + profile.getId()); // Do not send to your backend! Use an ID token instead.
    console.log('Name: ' + profile.getName());
    console.log('Image URL: ' + profile.getImageUrl());
    console.log('Email: ' + profile.getEmail()); // This is null if the 'email' scope is not present.
    localStorage.setItem("job-application-auth", `one-fm-authenticated-${profile.getId()}`);
    localStorage.setItem("gName", profile.getName());
    localStorage.setItem("gEmail", profile.getEmail());
    window.location = "./applicant-docs"
}
// Linked in Redirect Link


function linkedInSigin() {
    window.localStorage.setItem("linkedIn", true);
    localStorage.setItem("job-application-auth", `one-fm-authenticated-${Math.floor(Math.random() * 100) + 1}`);
    window.location = "https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=77qh8odc5i852h&redirect_uri=https%3A%2F%2Fdev.one-fm.com%2Fapplicant-docs&scope=r_liteprofile%20r_emailaddress";
}