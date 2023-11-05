const signup = () => {
    var signup_user_email = document.getElementById('signup-user-email').value;
    var signup_user_pwd = document.getElementById('signup-user-pwd').value;
    if(signup_user_email && signup_user_pwd){
      localStorage.setItem("job-application-auth", `one-fm-authenticated-${Math.floor(Math.random() * 100) + 1}`);
      window.location = "./applicant-docs"
    }
}
