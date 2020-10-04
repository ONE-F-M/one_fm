// File Upload
function readURL(input) {
    const loaderElement = document.getElementById("loader");
    if (input.files && input.files[0]) {
        var reader = new FileReader();

        reader.onload = function (e) {
            $(".image-upload-wrap").hide();

            $(".file-upload-image").attr("src", e.target.result);
            console.log(e.target.result);
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

