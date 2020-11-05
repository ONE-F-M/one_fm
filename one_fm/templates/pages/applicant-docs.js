if(window.localStorage.getItem("job-application-auth")){
    // File Upload
    function readURL(input) {
        const loaderElement = document.getElementById("loader");
        if (input.files && input.files[0]) {
            var reader = new FileReader();
            reader.fileName = input.files[0].name
            reader.onload = function (e) {
                console.log(e.target.fileName);
                let fileType = e.target.fileName.split('.').pop(), allowdtypes = 'jpeg,jpg,png';
                if (allowdtypes.indexOf(fileType) < 0) {
                    alert('Invalid file type, Upload only jpeg,jpg,png formats. aborted');
                    return false;
                }
                $(".image-upload-wrap").hide();
    
                $(".file-upload-image").attr("src", e.target.result);
                console.log(e);
                $(".file-upload-content").show();
    
                $(".image-title").html(input.files[0].name);
                Tesseract.recognize(e.target.result, "eng", {
                    logger: (m) => {
                        console.log(m);
                        loaderElement.style = "";
                    },
                })
                    .then(({ data: { text } }) => {
                        console.log(text);
                        window.localStorage.setItem("civilId", text);
                    })
                    .then((a) => {
                        window.location = "./job_application";
                    });
            };
    
            reader.readAsDataURL(input.files[0]);
        } else {
            removeUpload();
        }
    }
    
    function removeUpload() {
        $(".file-upload-input").replaceWith($(".file-upload-input").clone());
        $(".file-upload-content").hide();
        $(".image-upload-wrap").show();
    }
    $(".image-upload-wrap").bind("dragover", function () {
        $(".image-upload-wrap").addClass("image-dropping");
    });
    $(".image-upload-wrap").bind("dragleave", function () {
        $(".image-upload-wrap").removeClass("image-dropping");
    });
    
    const getLinkedInData = async () => {
        window.localStorage.setItem("linkedIn", false);
        const code = window.location.search.slice(6);
        console.log("code", code);
        axios
            .post("https://linked-be.vercel.app/api/accessCode", { code })
            .then((result) => {
                console.log(result);
                localStorage.setItem("linkedInData", JSON.stringify(result));
            })
            .catch((err) => {
                console.log(err);
                // Do somthing
            });
    };
    
    if (window.localStorage.getItem("linkedIn")) {
        getLinkedInData();
    }
    
    }
    else {
        alert("Please Signup or Login!");
        window.location = "applicant-sign-up";
    }
    const skipSignup = () => {
        if(localStorage.getItem("currentEasyJobOpening"))
            window.location = "easy_apply";        
        else
            window.location = "job_application";

    }