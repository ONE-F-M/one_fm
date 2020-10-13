const signup = () => {
    localStorage.setItem("job-application-auth", `one-fm-authenticated-${Math.floor(Math.random() * 100) + 1}`);
    window.location = "./applicant-docs"
}