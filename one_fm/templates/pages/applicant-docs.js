const frontSide = document.getElementById("front_cid");
const backSide = document.getElementById("back_cid");
const uploadFile = document.getElementById("fileUpload");
const imgPreview = document.getElementById("img-preview");
var f1, f2;

function upload_file(file, filename){
  let xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/method/upload_file', true);
  xhr.setRequestHeader('Accept', 'application/json');
  xhr.setRequestHeader('X-Frappe-CSRF-Token', frappe.csrf_token);
  let form_data = new FormData();
  form_data.append('file', file, file.name);
  xhr.send(form_data);
};

function file1(input){
let file = input.files[0];
if (file) {
  // Dynamically create a canvas element
  var canvas = document.createElement("canvas");

  // var canvas = document.getElementById("canvas");
  var ctx = canvas.getContext("2d");
  
  // Actual resizing
  ctx.drawImage(file, 0, 0, 300, 300);

  f2 = canvas.toDataURL('image/png', 1);

  f2 = f2.replace(/^data:image\/\w+;base64,/, "");
  console.log(f2)
}
  };
  function file2(input){
    let file = input.files[0];

    let reader = new FileReader();

    reader.readAsDataURL(file);

    reader.onload = function() {
      f2 = reader.result;
      f2 = f2.replace(/^data:image\/\w+;base64,/, "");
    };

    reader.onerror = function() {
      console.log(reader.error);
    };
  };

  {/*
function upload(){
    console.log("Start")
    if(f1 && f2){
      console.log(f1)
      let xhr = new XMLHttpRequest();
      xhr.open('GET', '/api/method/one_fm.templates.pages.applicant-docs.fetch_text', true);
      xhr.setRequestHeader('Accept', 'application/json');
      xhr.setRequestHeader('X-Frappe-CSRF-Token', frappe.csrf_token);
      let form_data = new FormData();
      form_data.append("file1", f1);
      form_data.append("file2", f2);
      console.log(form_data)
      xhr.send(form_data);
      console.log(xhr)
    }
    
  }
*/}
function upload(){
  console.log("Start");
  if (f1 && f2){
    image = {Image1:f1, Image2:f2};
    frappe.call({
      type: "GET",
      method: "one_fm.templates.pages.applicant-docs.fetch_text",
      args: {image :JSON.stringify(image)},
      callback: function(r) {
        if(r && r.message){
          console.log(r);
        }
        else{
          console.log("Error");
        }
      }
    });  
  };
  console.log("End");
};