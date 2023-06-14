frappe.ready_events = [];
frappe.ready = function (fn) {
    frappe.ready_events.push(fn);
}
window.dev_server = {{dev_server}};
window.socketio_port = {{frappe.socketio_port}};

var is_kuwaiti = $('#First_Name').attr('is_kuwaiti');
var civil_id_reqd = $('#First_Name').attr('civil_id_reqd');

var applicant_name = $('#First_Name').attr('data');

const TOTAL_FORM_FIELDS = 22;

// List of fields relevant to CIVIL ID's front side text
const CIVIL_ID_FRONT_TEXT_FIELDS = [
  'First_Name',
  'Second_Name',
  'Third_Name',
  'Last_Name',
  'First_Arabic_Name',
  'Second_Arabic_Name',
  'Third_Arabic_Name',
  'Last_Arabic_Name',
  'Gender',
  'Civil_ID_No',
  'Country_Code',
  'Date_Of_Birth',
  'Expiry_Date',
]

// List of fields relevant to CIVIL ID's back side text
const CIVIL_ID_BACK_TEXT_FIELDS = [
  'PACI_No',
  'Sponsor_Name'
]

// List of fields relevant to passport front side text
const PASSPORT_FRONT_TEXT_FIELDS = [
  'Passport_Number',
  'Passport_Date_of_Issue',
  'Passport_Date_of_Expiry'
]

// List of fields relevant to passport back side text
const PASSPORT_BACK_TEXT_FIELDS = [
  'Passport_Place_of_Issue'
]

var front_cid_filepath = "";
var back_cid_filepath = "";
var front_passport_filepath = "";
var back_passport_filepath = "";

window.onload = () => {
  $(".required_indicator").hide();
  $("#tooltiptext1").hide();
  $("#tooltiptext2").hide();

  $("#Sponsor").hide();
  if(is_kuwaiti == 0){
    $("#Sponsor").show();
  }
  if(civil_id_reqd == 1){
    $(".required_indicator").show()
  }
  populate_nationality();
  populate_country();
}

let civil_id_image;
let passport_image;

function extract_image(){
  if (civil_id_reqd == 1){
    extract(document.getElementById("Civil_ID_Front").files[0],"Civil_ID","front_civil")
    extract(document.getElementById("Civil_ID_Back").files[0],"Civil_ID","back_civil")
  }
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
        var nationality = document.getElementById("Nationality");
        for (let i=0; i<=langArray.length;i++) {
          nationality.options[nationality.options.length] = new Option(langArray[i], langArray[i]);
        }
      }
    }
  });
}
function populate_country(){
  frappe.call({
    type: "GET",
    method: "one_fm.templates.pages.applicant_docs.populate_country",
    callback: function(r) {
      langArray = r.message;

      if(langArray){
        var place_of_issue = document.getElementById("Passport_Place_of_Issue");
        var place_of_birth = document.getElementById("Birth_Place");
        for (let i=0; i<=langArray.length;i++) {
          place_of_issue.options[place_of_issue.options.length] = new Option(langArray[i], langArray[i]);
          place_of_birth.options[place_of_birth.options.length] = new Option(langArray[i], langArray[i]);
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
  // if($("#Civil_ID_Front").val().length == 0 ){
  //   $("#tooltiptext1").show()
  // }
  // else if($("#Civil_ID_Back").val().length == 0 ){
  //   $("#tooltiptext2").show();
  // }
  // else{
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
        // disable button
        $('#fileUpload').prop('disabled', 1)
      };
    }
  });
  $('#declare-div').prop('hidden', true);
  $('#submitForm').prop('hidden', true);
}
// };


function fill_form(data, type,token){
  {/* This Function fills the output form for user to view.
  The value is fetched from the api*/}
  if(data == "Error"){
    alert("Sorry! Some Error Occured during uploading" + type);
  }
  else {

    let total_fill_counter = 0;

    if(type == "Civil ID"){
      input_data(data,'front_text','First_Name');
      input_data(data,'front_text','Second_Name');
      input_data(data,'front_text','Third_Name');
      input_data(data,'front_text','Last_Name');
      input_data(data,'front_text','First_Arabic_Name');
      input_data(data,'front_text','Second_Arabic_Name');
      input_data(data,'front_text','Third_Arabic_Name');
      input_data(data,'front_text','Last_Arabic_Name');
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

      let front_side_cid_filled_fields_count = count_filled_fields(data, 'front_text', CIVIL_ID_FRONT_TEXT_FIELDS);
      let back_side_cid_filled_fields_count = count_filled_fields(data, 'back_text', CIVIL_ID_BACK_TEXT_FIELDS);

      total_fill_counter += (front_side_cid_filled_fields_count + back_side_cid_filled_fields_count);
    }
    else if(type == "Passport"){
      // front_passport_filepath = input_filepath(data, 'front_text', 'Passport_Front',token)
      // back_passport_filepath = input_filepath(data, 'back_text', 'Passport_Back',token)

      function_set_passport_data(data)
      // input_data(data,'front_text','Passport_Number');
      // input_data(data,'front_text','Passport_Date_of_Issue');
      // input_data(data,'front_text','Passport_Date_of_Expiry');
      // input_data(data,'back_text','Passport_Place_of_Issue');

      // let front_side_pp_filled_fields_count = count_filled_fields(data, 'front_text', PASSPORT_FRONT_TEXT_FIELDS);
      // let back_side_pp_filled_fields_count = count_filled_fields(data, 'back_text', PASSPORT_BACK_TEXT_FIELDS);

      // total_fill_counter += (front_side_pp_filled_fields_count + back_side_pp_filled_fields_count);
    }

    // if (total_fill_counter < TOTAL_FORM_FIELDS){
    //   frappe.msgprint({
    //     title: __("Could not obtain all information"),
    //     indicator: "orange",
    //     message: __("Some fields in the below form may be empty. Please fill them out correctly."),
    //   });
    // }

  }
};

function count_filled_fields(data, text_side, list_of_keys){
  let fill_counter = 0;

  list_of_keys.forEach(field => {
    if(data[text_side][field]){
      fill_counter++;
    }
  });

  return fill_counter;
}

function input_filepath(Data, key1, key2,token){
  if(Data[key1][key2]!= undefined){
    upload_image(document.getElementById(key2).files[0],Data[key1][key2],applicant_name+"_"+key2+'.png',token)
    return Data[key1][key2]
  }
};

function sentenceCase (str) {
  if ((str===null) || (str===''))
    return false;
  else
  str = str.toString();

  return str.replace(/\w\S*/g,
  function(txt){return txt.charAt(0).toUpperCase() +
    txt.substr(1).toLowerCase();});
}


function function_set_passport_data(data){
  console.log(data);
  let doc = data.front_text;
  if(doc.surname){
    $('#Last_Name').val(doc.surname);
  }
  if (doc.birth_date){
    $('#Date_Of_Birth').val(doc.birth_date)
  }
  if (doc.gender){
    $('#Gender').val(doc.gender=='M' ? 'Male' : 'Female')
  }
  if (doc.id_number){
    $('#Passport_Number').val(doc.id_number)
  }
  if (doc.issuance_date){
    $('#Passport_Date_of_Issue').val(doc.issuance_date)
  }
  if (doc.expiry_date){
    $('#Passport_Date_of_Expiry').val(doc.expiry_date)
  }
  if (doc.birth_place){
    $.makeArray($('#Birth_Place>option')).forEach((item)=>{
      if (item.value.toLowerCase()==doc.birth_place.toLowerCase()){
        $('#Birth_Place').val(sentenceCase(doc.birth_place))
      }
    })
    
  }
  if (doc.given_names.length){
    let fields = ["#First_Name", "#Second_Name", "#Third_Name"]
    doc.given_names.forEach((item, index)=>{
      $(fields[index]).val(item);
    })
  }
  if($('#perdonal-detail :input')){
    $.makeArray($('#perdonal-detail :input')).forEach((item)=>{if (!item.value && item.required){$(`#${item.id}`).prop('style', 'border: 2px solid red;')};})
    $.makeArray($('select')).forEach((item)=>{if (!item.value && item.required && item.id){$(`#${item.id}`).prop('style', 'border: 2px solid red;')};})
  }

  // end
  $("#cover-spin").hide();
  $('#finalForm').css('display', 'block');
  get_uploaded_data(data);
  
  
  
}

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
  
  if($('#First_Name').attr("data")){
    // frappe.freeze();
		frappe.confirm('Are you sure you want to Submit?, On Submit the link will be expired!',
    () => {

      var frontPassport = document.getElementById('Passport_Front');
      var backPassport = document.getElementById('Passport_Back');

      upload_image_to_server(frontPassport.files[0]);
      upload_image_to_server(backPassport.files[0]);

      applicant_details['applicant_doc']['Passport Front'] = frontPassport.value;
      applicant_details['applicant_doc']['Passport Back'] =  backPassport.value;


			frappe.call({
				type: "POST",
				method: "one_fm.templates.pages.applicant_docs.update_job_applicant",
				args: {
					job_applicant: $('#First_Name').attr("data"),
					data: applicant_details
				},
				btn: this,
				callback: function(r){
					frappe.unfreeze();
					frappe.msgprint(frappe._("Succesfully Submitted your Details and our HR team will be responding to you soon."));
					if(r.message){
            setTimeout(()=>{window.location.href = "/careers"}, 3000);
					}
				}
			});
    }, () => {
      frappe.unfreeze();
        // action to perform if No is selected
    })
  }
  else{
    frappe.msgprint(frappe._("Please fill All the details to submit the Job Applicant"));
  }
}

function Save(){
  // $.makeArray($('#perdonal-detail :input')).forEach((item)=>{if (!item.value && item.required){$(`#${item.id}`).prop('style', 'border: 2px solid red;')};})
  // $.makeArray($('select')).forEach((item)=>{if (!item.value && item.required && item.id){$(`#${item.id}`).prop('style', 'border: 2px solid red;')};})
  let goodTogo = false;
    $.makeArray($('#perdonal-detail :input')).forEach((item)=>{if (!item.value && item.required){
      $('#declare-div').prop('hidden', true);
      $('#submitForm').prop('hidden', true);
      frappe.throw("Please fill all fields in red box.");
      return;
    };})

    $.makeArray($('select')).forEach((item)=>{if (!item.value && item.required){
      $('#declare-div').prop('hidden', true);
      $('#submitForm').prop('hidden', true);
      frappe.throw("Please fill all fields in red box.");
      return;
    };})

      var applicant_details = get_details_from_form();

      if($('#First_Name').attr("data")){
        // frappe.freeze();
        frappe.call({
          type: "POST",
          method: "one_fm.templates.pages.applicant_docs.save_as_draft",
          args: {
            job_applicant: $('#First_Name').attr("data"),
            data: applicant_details
          },
          btn: this,
          callback: function(r){
            frappe.unfreeze();
            frappe.msgprint(frappe._("Succesfully Saved your application as draft, you can finish up and Submit later!."));
            $('#declare-div').prop('hidden', false);
            $('#submitForm').prop('hidden', false);
          }
        });

      } else{
        frappe.msgprint(frappe._("Please, you need to fill some details before you can save "));
      }
  
}

function get_details_from_form() {
  var applicant_details = {};
  applicant_details['one_fm_first_name'] = $('#First_Name').val();
  applicant_details['one_fm_second_name'] = $('#Second_Name').val();
  applicant_details['one_fm_third_name'] = $('#Third_Name').val();
  applicant_details['one_fm_last_name'] = $('#Last_Name').val();
  applicant_details['one_fm_first_name_in_arabic'] = $('#First_Arabic_Name').val();
  applicant_details['one_fm_second_name_in_arabic'] = $('#Second_Arabic_Name').val();
  applicant_details['one_fm_third_name_in_arabic'] = $('#Third_Arabic_Name').val();
  applicant_details['one_fm_last_name_in_arabic'] = $('#Last_Arabic_Name').val();
  applicant_details['one_fm_gender'] = $('#Gender').val();
  applicant_details['one_fm_educational_qualification'] = $('#EducationalQualification').val();
  applicant_details['one_fm_university'] = $('#University').val();
  applicant_details['one_fm_marital_status'] = $('#MaritalStatus').val();
  applicant_details['one_fm_religion'] = $('#Religion').val();
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
  applicant_details['one_fm_country_code'] = $('#Country_Code').val();
  

  applicant_details['applicant_doc']={}

  
  get_filepath(applicant_details['applicant_doc'],front_cid_filepath, "Civil ID Front" )
  get_filepath(applicant_details['applicant_doc'],back_cid_filepath, "Civil ID Back" )
  //get_filepath(applicant_details['applicant_doc'],front_passport_filepath, "Passport Front" )
  //get_filepath(applicant_details['applicant_doc'],back_passport_filepath, "Passport Back" )

  // applicant_details['paci_no'] = $('#PACI_No').val();
  return applicant_details;
};

function get_filepath(object, value, key){
  if(value != ""){
    var file_name = key.replaceAll(" ","_")
    object[key] = applicant_name+"_"+file_name+'.png';
  }
  return object
}


function preview_front(input){
  var uploaded_pics = `
  <h4>Passport Front Image</h4>
  <img src="" alt="Front Page Of Passport" id="passport-front" class="form-control" style="height: 350px;">
`;

  document.getElementById("uploaded-passport-front").innerHTML = uploaded_pics;
  document.getElementById('passport-front').src = window.URL.createObjectURL(input.files[0]);
}


function preview_back(input){
  var uploaded_pics = `
  <h4>Passport Back Image</h4>
  <img src="" alt="Front Page Of Passport" id="passport-back" class="form-control" style="height: 350px;">
`;
  document.getElementById("uploaded-passport-back").innerHTML = uploaded_pics;
  document.getElementById('passport-back').src = window.URL.createObjectURL(input.files[0]);
}


function get_uploaded_data(data){
  return frappe.call({
    method: "one_fm.templates.pages.applicant_docs.get_uploaded_data",
    args: {
      data: data
    },
    callback: function(r){
      frappe.unfreeze();
      frappe.msgprint(frappe._(`The following were extracted from the Image <ul>${r.message.map(item => (
        `<li>${item}</li>`
      )).join('')}</ul> Kindly fill the remaining fields correctly.`));

    }
  })
}



function upload_image_to_server(file){
  var xhr = new XMLHttpRequest();
  let form_data = new FormData();

  xhr.open('POST', '/api/method/upload_file', false);

  xhr.setRequestHeader("X-Frappe-CSRF-Token", frappe.csrf_token);
  xhr.setRequestHeader("Accept", "application/json");

  form_data.append('file', file);
  form_data.append('is_private', true)
  xhr.send(form_data);

}
