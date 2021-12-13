window.frappe = {};
frappe.ready_events = [];
frappe.ready = function (fn) {
    frappe.ready_events.push(fn);
}
window.dev_server = {{dev_server}};
window.socketio_port = {{frappe.socketio_port}};

var is_kuwaiti = 0;
let civil_id_image = new FormData();
let passport_image = new FormData();

function extract_image(){
  extract(document.getElementById("front_cid").files[0],"Civil_ID","front_civil")
  extract(document.getElementById("back_cid").files[0],"Civil_ID","back_civil")
  extract(document.getElementById("front_passport").files[0],"Passport","front_passport")
  extract(document.getElementById("back_passport").files[0],"Passport","back_passport")

}
function extract(file, type, key){

  if(file){
    let reader = new FileReader();

    reader.readAsDataURL(file);

    reader.onload = function() {
      result = reader.result;
      result = result.replace(/^data:image\/\w+;base64,/, "");
      if(type =="Civil_ID"){
        civil_id_image.append(key, result);
        return civil_id_image
      }
      else{
        passport_image.append(key, result);
        return passport_image
      }           
    };
  }
  else{
    console.log("File missing")
  }
}

function populate_nationality(){
  frappe.call({
    type: "GET",
    method: "one_fm.templates.pages.applicant-docs.populate_nationality",
    callback: function(r) {
      langArray = r.message;
      if(langArray){
        var select = document.getElementById("Nationality");
        for (let i=0; i<=langArray.length;i++) {
          select.options[select.options.length] = new Option(langArray[i], langArray[i]);
     }

      }
    }
  }); 
}

function fetchNationality(code){
  frappe.call({
    type: "GET",
    method: "one_fm.templates.pages.applicant-docs.fetch_nationality",
    args: {code :code},
    callback: function(r) {
      if(r.message){
        document.getElementById("Nationality").value = r.message;
      }
      else{
        document.getElementById("Nationality").value = "";
      }
      
    }
  }); 
}
function send_request(method, data, token, type){
  var request = new XMLHttpRequest();
  // POST to httpbin which returns the POST data as JSON
    request.open('POST', method ,true);
    request.setRequestHeader("X-Frappe-CSRF-Token", token );
    request.setRequestHeader("Accept", "application/json");

    request.send(data);
    request.type = type
    request.onreadystatechange = () => {
      if (request.readyState == XMLHttpRequest.DONE) {
          if (request.status === 200) {
        let r = null;
        try {
          r = JSON.parse(request.responseText);
          fill_form(r.message,request.type);
        } catch (e) {
          r = request.responseText;
        }
        } else if (request.status === 403) {
        let response = JSON.parse(request.responseText);
        frappe.msgprint({
          title: __("Not permitted"),
          indicator: "red",
          message: response._error_message,
        });
        } 
      }
      };
}
function upload(){
  extract_image();
  populate_nationality();

  var method_map = {
    'civil_id': '/api/method/one_fm.templates.pages.applicant-docs.get_civil_id_text',
    'passport': '/api/method/one_fm.templates.pages.applicant-docs.get_passport_text'
  }

  civil_id_image.append("is_kuwaiti",is_kuwaiti)
  
  frappe.call({
    type: "GET",
    method: "one_fm.templates.pages.applicant-docs.token",
    callback: function(r) {
      var token = r.message
      if (civil_id_image){
        send_request(method_map['civil_id'], civil_id_image, token,"Civil ID")
      };
      if (passport_image){
        send_request(method_map['passport'], passport_image, token,"Passport")
      };
    }
  });
};


function fill_form(data, type){
  {/* This Function fills the output form for user to view.
  The value is fetched from the api*/}
  if(data == "Error"){
    alert("Sorry! Some Error Occured during uploading" + type);
  }
  else {
    if(type == "Civil ID"){
      input_data(data,'front_text','Name');
      input_data(data,'front_text','Arabic_Name');
      input_data(data,'front_text','Gender');
      input_data(data,'front_text','Civil_ID_No');
      input_data(data,'front_text','Country_Code');
      input_data(data,'front_text','Date_Of_Birth');
      input_data(data,'front_text','Expiry_Date');
      input_data(data,'back_text','PACI_No');
      if(data['front_text']['Country_Code'] != undefined){
        fetchNationality(data['front_text']['Country_Code']);
      }
      if(is_kuwaiti==1){
        document.getElementById("Sponsor").style.display = "block"; 
      }      
    }
    else if(type == "Passport"){
      input_data(data,'front_text','Passport_Date_of_Issue');
      input_data(data,'front_text','Passport_Date_of_Expiry');
      input_data(data,'front_text','Passport_Number');
      input_data(data,'back_text','Passport_Place_of_Issue');
    }
  }
};

function input_data(Data, key1, key2){
  if(Data[key1][key2]!= undefined){
    document.getElementById(key2).value = Data[key1][key2];
  }
}