frappe.ready_events = [];
frappe.ready = function (fn) {
    frappe.ready_events.push(fn);
}
window.dev_server = {{dev_server}};
window.socketio_port = {{frappe.socketio_port}};

var is_kuwaiti = $('#Name').attr('is_kuwaiti');

var applicant_name = (($('#Name').attr('data')).split(' ').slice(0, 2).join(' ')).replace(' ', '_');

var front_cid_filepath = "";
var back_cid_filepath = "";
var front_passport_filepath = "";
var back_passport_filepath = "";

window.onload = () => {
  $("#Sponsor").hide();
  if(is_kuwaiti == 0){
    $("#Sponsor").show();
  }
  populate_nationality();
}

let civil_id_image;
let passport_image;

function extract_image(){
  extract(document.getElementById("Civil_ID_Front").files[0],"Civil_ID","front_civil")
  extract(document.getElementById("Civil_ID_Back").files[0],"Civil_ID","back_civil")
  extract(document.getElementById("Passport_Front").files[0],"Passport","front_passport")
  extract(document.getElementById("Passport_Back").files[0],"Passport","back_passport")
}

function upload_image(file, file_url, filename, token){
  var xhr = new XMLHttpRequest();
  let form_data = new FormData();

  xhr.open('POST', '/api/method/upload_file', true);

  xhr.setRequestHeader("X-Frappe-CSRF-Token", token);
  xhr.setRequestHeader("Accept", "application/json");

  form_data.append('file', file, filename);
  form_data.append('is_private', true)
  form_data.append('file_url', file_url)
  xhr.send(form_data);
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
}

function populate_nationality(){
  frappe.call({
    type: "GET",
    method: "one_fm.templates.pages.applicant_docs.populate_nationality",
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
    method: "one_fm.templates.pages.applicant_docs.fetch_nationality",
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
            $("#cover-spin").hide();
            $('#finalForm').css('display', 'block');
            fill_form(r.message,request.type, token);
          } catch (e) {
            $("#cover-spin").hide();
            $('#finalForm').css('display', 'block');
            r = request.responseText;
          }
        } else if (request.status === 403) {
          $("#cover-spin").hide();
          $('#finalForm').css('display', 'block');
          let response = JSON.parse(request.responseText);
          frappe.msgprint({
            title: __("Not permitted"),
            indicator: "red",
            message: response._error_message,
          });
        } else {
          $("#cover-spin").hide();
          $('#finalForm').css('display', 'block');
          frappe.msgprint({
            title: __("Error extracting text"),
            indicator: "orange",
            message: __("Please fill out the below form manually."),
          });
        }
      }
    };
}


function upload(){
  civil_id_image = new FormData();
  passport_image = new FormData();
  extract_image();

  var method_map = {
    'civil_id': '/api/method/one_fm.templates.pages.applicant_docs.get_civil_id_text',
    'passport': '/api/method/one_fm.templates.pages.applicant_docs.get_passport_text'
  }
  frappe.call({
    type: "GET",
    method: "one_fm.templates.pages.applicant_docs.token",
    callback: function(r) {
      var token = r.message
       if (!!civil_id_image.entries().next().value){
        civil_id_image.append("is_kuwaiti",is_kuwaiti)
        $("#cover-spin").show(0);
        send_request(method_map['civil_id'], civil_id_image, token,"Civil ID")
      };
      if (!!passport_image.entries().next().value){
        $("#cover-spin").show(0);
        send_request(method_map['passport'], passport_image, token,"Passport")
      };
    }
  });
};


function fill_form(data, type,token){
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
      input_data(data,'front_text','Passport_Number');
      if(data['front_text']['Country_Code'] != undefined){
        fetchNationality(data['front_text']['Country_Code']);
      }

      front_cid_filepath = input_filepath(data, 'front_text', 'Civil_ID_Front',token)
      back_cid_filepath = input_filepath(data, 'back_text', 'Civil_ID_Back',token)

      if(is_kuwaiti==0){
        input_data(data,'back_text','Sponsor_Name');
      }
    }
    else if(type == "Passport"){
      front_passport_filepath = input_filepath(data, 'front_text', 'Passport_Front',token)
      back_passport_filepath = input_filepath(data, 'back_text', 'Passport_Back',token)
      input_data(data,'front_text','Passport_Date_of_Issue');
      input_data(data,'front_text','Passport_Date_of_Expiry');
      input_data(data,'back_text','Passport_Place_of_Issue');
    }
  }
};


function input_filepath(Data, key1, key2,token){
  if(Data[key1][key2]!= undefined){
    upload_image(document.getElementById(key2).files[0],Data[key1][key2],applicant_name+"_"+key2+'.png',token)
    return Data[key1][key2]
  }
};

function input_data(Data, key1, key2){
  if(Data[key1][key2]!= undefined){
    if(key2 =="Gender"){
      if(Data[key1][key2]=="M"){
        document.getElementById(key2).value = "Male"
      }
      else if(Data[key1][key2]=="F"){
        document.getElementById(key2).value = "Female"
      }
    }
    document.getElementById(key2).value = Data[key1][key2];
  }
}

function Submit(){
  var applicant_details = get_details_from_form();

  if($('#Name').attr("data")){
    frappe.freeze();
    frappe.call({
      type: "POST",
      method: "one_fm.templates.pages.applicant_docs.update_job_applicant",
      args: {
        job_applicant: $('#Name').attr("data"),
        data: applicant_details
      },
      btn: this,
      callback: function(r){
        frappe.unfreeze();
        frappe.msgprint(frappe._("Succesfully Submitted your Details and our HR team will be responding to you soon."));
        if(r.message){
          window.location.href = "/applicant_docs";
        }
      }
    });
  }
  else{
    frappe.msgprint(frappe._("Please fill All the details to submit the Job Applicant"));
  }
}

function get_details_from_form() {
  var applicant_details = {};
  applicant_details['one_fm_first_name_in_arabic'] = $('#Arabic_Name').val();
  applicant_details['one_fm_gender'] = $('#Gender').val();
  applicant_details['one_fm_date_of_birth'] = $('#Date_Of_Birth').val();
  applicant_details['one_fm_cid_number'] = $('#Civil_ID_No').val();
  applicant_details['one_fm_cid_expire'] = $('#Expiry_Date').val();
  applicant_details['one_fm_nationality'] = $('#Nationality').val();
  applicant_details['one_fm_place_of_birth'] = $('#Birth_Place').val();
  applicant_details['one_fm_passport_number'] = $('#Passport_Number').val();
  applicant_details['one_fm_passport_type'] = $('#Passport_Type').val();
  applicant_details['one_fm_passport_issued'] = $('#Passport_Date_of_Issue').val();
  applicant_details['one_fm_passport_expire'] = $('#Passport_Date_of_Expiry').val();
  applicant_details['one_fm_passport_holder_of'] = $('#Passport_Place_of_Issue').val();

  applicant_details['applicant_doc']={}

  get_filepath(applicant_details['applicant_doc'],front_cid_filepath, "Civil ID Front" )
  get_filepath(applicant_details['applicant_doc'],back_cid_filepath, "Civil ID Back" )
  get_filepath(applicant_details['applicant_doc'],front_passport_filepath, "Passport Front" )
  get_filepath(applicant_details['applicant_doc'],back_passport_filepath, "Passport Back" )

  // applicant_details['paci_no'] = $('#PACI_No').val();
  return applicant_details;
};

function get_filepath(object, value, key){
  if(value != ""){
    var file_name = key.replaceAll(" ","_")
    console.log(file_name)
    object[key] = applicant_name+"_"+file_name+'.png';
  }
  return object
}
