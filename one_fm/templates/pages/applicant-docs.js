window.frappe = {};
frappe.ready_events = [];
frappe.ready = function (fn) {
    frappe.ready_events.push(fn);
}
window.dev_server = {{dev_server}};
window.socketio_port = {{frappe.socketio_port}};

const frontSide = document.getElementById("front_cid");
const backSide = document.getElementById("back_cid");
const uploadFile = document.getElementById("fileUpload");
const imgPreview = document.getElementById("img-preview");
var f1, f2;

function file1(input){
let file = input.files[0];

    let reader = new FileReader();

    reader.readAsDataURL(file);

    reader.onload = function() {
      f1 = reader.result;
      f1 = f1.replace(/^data:image\/\w+;base64,/, "");
    };

    reader.onerror = function() {
      console.log(reader.error);
    };

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
          fill_form(r.message)
          console.log(r.message)
        }
        else{
          console.log("Error");
        }
      }
    });  
  };
  console.log("End");
};


function fill_form(data){
  {/* This Function fills the output form for user to view.
  The value is fetched from the api*/}
  if(data == "Error"){
    alert("Sorry! Some Error Occured!!");
  }
  else {
    document.getElementById("finalForm").style.display = "block";  
    document.getElementById("name").value = data['Name'];
    document.getElementById("ar_name").value = data['Arabic Name'];
    document.getElementById("gender").value = data['Gender']
    document.getElementById("civilid").value = data['Civil ID No.']
    document.getElementById("nationality").value = data['Nationality']
    document.getElementById("dob").value = data['Date Of Birth']
    document.getElementById("expiry_date").value = data['Expiry Date']
    document.getElementById("paci_no").value = data['PACI No.'] 
  }
};