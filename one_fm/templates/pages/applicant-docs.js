window.frappe = {};
frappe.ready_events = [];
frappe.ready = function (fn) {
    frappe.ready_events.push(fn);
}
window.dev_server = {{dev_server}};
window.socketio_port = {{frappe.socketio_port}};

//Name and Nationality should be fetched from link.
const nationality = "Kuwaiti"; //or Non-Kuwaiti

var front , back;

function front_civil_extract(input){
    let file = input.files[0];

    let reader = new FileReader();

    reader.readAsDataURL(file);

    reader.onload = function() {
      front = reader.result;
      front = front.replace(/^data:image\/\w+;base64,/, "");
    };

    reader.onerror = function() {
      console.log(reader.error);
    };

};

function back_civil_extract(input){
    let file = input.files[0];
    let reader = new FileReader();

    reader.readAsDataURL(file);

    reader.onload = function() {
      back = reader.result;
      back = back.replace(/^data:image\/\w+;base64,/, "");
    };

    reader.onerror = function() {
      console.log(reader.error);
    };
};
function test(input){
  var date = input.value;
  console.log(date)
}

function upload(){
<<<<<<< HEAD
  civilid_check = document.getElementById("noCivilID").checked;
  console.log(civilid_check)

  if(!civilid_check){
    if (front && back){
      image = {front_side:front, back_side:back};
      frappe.call({
        type: "GET",
        method: "one_fm.templates.pages.applicant-docs.get_civil_id_text",
        args: {image :JSON.stringify(image)},
        callback: function(r) {
          console.log(r)
          if(r && r.message){
            document.getElementById("finalForm").style.display = "block"; 
            document.getElementById("output_message").innerHTML = "Have a look at the following form and correct if any mistakes!";
            fill_form(r.message)
            console.log(r.message)
          }
          else{
            console.log("Error");
          }
=======
  var f1 = fetch_base(document.getElementById("front_cid").files[0]);
  var f2 = fetch_base(document.getElementById("back_cid").files[0]);

  console.log(f1);
  if (f1 && f2){
    image = {Image1:f1, Image2:f2};
    frappe.call({
      type: "GET",
      method: "one_fm.templates.pages.applicant_docs.fetch_text_for_kuwaiti_civilid",
      args: {image :JSON.stringify(image)},
      callback: function(r) {
        if(r && r.message){
          fill_form(r.message)
          console.log(r.message)
        }
        else{
          console.log("Error");
>>>>>>> Update method name
        }
      });  
    };
  }
  else{
    document.getElementById("finalForm").style.display = "block";   
    document.getElementById("output_message").innerHTML = "Kindly fill in the following form and correct if any mistakes!";
  }
  
  console.log("End");
};


function fill_form(data){
  {/* This Function fills the output form for user to view.
  The value is fetched from the api*/}
  if(data == "Error"){
    alert("Sorry! Some Error Occured!!");
  }
  else {
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