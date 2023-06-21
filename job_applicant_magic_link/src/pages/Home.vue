<script>
import { Dialog, createResource } from 'frappe-ui'
import Swal from 'sweetalert2'

export default {
  name: 'Home',
  data() {
    return {
      styleConfig: {
        showPage: 'none'
      },
      imageFiles: {},
      showDialog: false,
      magicLink: '',
      job_applicant: ''
    }
  },
  resources: {
    ping: {
      url: 'ping',
    },
  },
  components: {
    Dialog,
  },
  mounted(){
    this.loadContent();
  },
  methods:{
    loadContent(){
      let magicLink = this.$route.query.magic_link;
      if (!magicLink){
        Swal.fire(
          'Error',
          'Magic link not found',
          'warning'
        )
      } else {
        this.magicLink = magicLink;
        let fetchMagicLink = createResource({
          url: '/api/method/one_fm.www.job_applicant_magic_link.index.get_magic_link',
          params: {
            magic_link: this.magicLink
          },
        })
        fetchMagicLink.fetch().then((data)=>{
          if (Object.keys(data).length === 0){
            Swal.fire(
              'Error',
              'Magic link invalid or expired',
              'warning'
            )
          } else {
            this.styleConfig.showPage = 'block'
            this.job_applicant = data.name
          }
        })       
      }
    },
    // Preview Image
    previewImage(e){
      let el = document.querySelector(`#${e.target.id}-preview`);
      if (!el){
        var preview_el = document.createElement("div");
        preview_el.classList="col-md-6"
        preview_el.innerHTML = `
          <h4>${e.target.placeholder}</h4>
            <img src="" alt="${e.target.placeholder}" id="${e.target.id}-preview" class="form-control" style="height: 350px;">
          </div>
        `;
        document.getElementById("image_preview").appendChild(preview_el);
        document.getElementById(`${e.target.id}-preview`).src = window.URL.createObjectURL(e.target.files[0]);
      } else {
        document.getElementById(`${e.target.id}-preview`).src = window.URL.createObjectURL(e.target.files[0]);
      }
      // extract image
      this.extract_image_file(e.target);
    },
    // Extract image file from form
    extract_image_file(el){
      let me = this;
      if(el){
        if (el.files){
          let reader = new FileReader();
          reader.readAsDataURL(el.files[0]);
          reader.onload = function() {
            let result = reader.result;
            result = result.replace(/^data:image\/\w+;base64,/, "");
            me.imageFiles[el.id]=result
          };
        }
        
      }
    },
    // Process image upload
    async upload(){
      let me = this
      console.log(me.imageFiles)
      // if any image was found and process, upload it
      let uploadImage = createResource({
        url: '/api/method/one_fm.www.job_applicant_magic_link.index.upload_image',
        params: me.imageFiles,
        method: 'POST',
        onSuccess(data) {
          console.log(data)
        },
      })
      uploadImage.fetch()
      console.log(uploadImage)
    }
  }
}
</script>

<template>
  <div class="container-fluid">
    <div class="jumbotron">
      <div class="row" :style="'display:'+styleConfig.showPage">
        <div class="col-md-12">
          <div id="cover-spin"><div style="display: grid; height: 100%; width: 100%; place-items: center;"><span>We are extracting your information from the image...Please wait !</span></div></div>
            <main>
                <div
                    class="p-5 text-center bg-image"
                    style="
                    background-image:  linear-gradient( rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0.3) ), url('/assets/one_fm/assets/img/job-application/ja-banner.png'); height: 300px; ">
                    <div class="d-flex justify-content-center align-items-center">
                        <h1 style="color:#ffff; line-height: 100px;" class="mb-3">Applicant Documents</h1>
                    </div>
                    <hr style="width:50%;text-align:left;border-top: 1px solid #ffff;">
                    <div class="text-center mt-10">
                        <h6 style="color:#ffff"><strong>{{applicant_name}}</strong></h6>
                        <h6 style="color:#ffff"><strong>{{email_id}}</strong></h6>
                        <h6 style="color:#ffff"><strong>{{applicant_designation}}</strong></h6>
                    </div>
                </div>

                <br><br>

                <article class="main-container m-auto p-auto">
                  <div>
                    <div class="row col-lg-12 col-md-12 mb-12">
                        <h6>Dear {{applicant_name}}, greetings from One Facilities Management!</h6>
                        <h6>As a part of the onboarding process for the {{applicant_designation}} role, we request you to provide us with the following documents and complete the below form.</h6>
                        <ul>
                            <li><h6>Passport - front and back side</h6></li>
                            <li><h6>Civil ID - front and back side</h6></li>
                        </ul>
                    </div>
                    <section class="form-wrapper">
                        <div class="form-container">
                          <form class="form" name="file_upload" id="file_upload">
                            <h2>File Upload
                                <small id="passwordHelpInline" class="text-muted" style="font-size: small;">
                                    Only image files of type png/jpeg accepted*
                                </small>
                            </h2>
                            <hr>
                            <div class="row">
                                    <div class="form-group col-md-12">
                                        <label  for="file">International Passport Data Page</label>
                                        <input class="form-control" type="file" id="passport_data_page" placeholder="Passport Data"  name="passport_data_page"  accept="image/png, image/jpeg" :onchange="previewImage">
                                    </div>
                            </div>
                            <div class="row">
                                <div class="form-group col-md-6">
                                    <label class="form-label" for="file" >Civil ID Front Side</label> <span class="required_indicator" style="color: red;">*</span>
                                    <input class="form-control" type="file" id="civil_id_front" placeholder="Front Civil ID" name="file"  accept="image/png, image/jpeg" :onchange="previewImage">
                                    <span id="tooltiptext1">* Please Upload Your Civil ID</span>
                                </div>
                                <div class="form-group col-md-6">
                                    <label class="form-label" for="file" >Civil ID Back Side</label> <span class="required_indicator" style="color: red;">*</span>
                                    <input class="form-control" type="file" id="civil_id_back" placeholder="Back Civil ID"  name="file"  accept="image/png, image/jpeg" :onchange="previewImage">
                                    <span id="tooltiptext2">* Please Upload Your Civil ID</span>
                                    <br>
                                </div>
                            </div>
                            
                            <hr>
                            
                            <div class="row col-md-12">
                                <div id="image_preview"></div>
                            </div>


                            <div style="margin-top: 30px; display: flex; justify-content: end">
                                <button class="btn btn-dark" type="button" href="json.json" value="submit" id="fileUpload" @click.prevent="upload">Get Passport Details and Upload</button>
                            </div>
                        </form>
                      </div>
                    </section>
                </div>
                <br><br>

                <div  class="m-auto p-auto">
                    <div>
                        <section class="form-wrapper" id="finalForm" style="display:block;">
                            <div class="message-block-head d-flex">
                            <div class="message-block-info p-1 h2 m-1">
                                    <p id="output_message" style="font-size: 22px;"></p>
                                </div>
                            </div>

                            <div class="form-container">
                                <form class="form" id="perdonal-detail">
                                    <h2>Personal Details</h2>
                                    <hr>
                                  <div class="row">
                                    <!-- Name section -->
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label class="form-label" for="first_name">First Name *</label>
                                            <input class="form-control input" type="text" id="first_name" name="first_name">
                                        </div>
                                        <div class="form-group">
                                            <label class="form-label" for="second_name">Second Name</label>
                                            <input class="form-control input" type="text" id="second_name" name="second_name">
                                        </div>
                                        <div class="form-group">
                                            <label class="form-label" for="third_name">Third Name</label>
                                            <input class="form-control input" type="text" id="third_name" name="third_name">
                                        </div>
                                        <div class="form-group">
                                            <label class="form-label" for="last_name">Last Name *</label>
                                            <input class="form-control input" type="text" id="last_name" name="last_name">
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                      <div class="form-group">
                                          <label  class="form-label">First Name(Arabic)</label>
                                          <input class="form-control input" type="text" id="first_ar_name" name="first_ar_name">
                                      </div>
                                      <div class="form-group">
                                          <label  class="form-label">Second Name(Arabic)</label>
                                          <input class="form-control input" type="text" id="second_ar_name" name="second_ar_name">
                                      </div>
                                      <div class="form-group">
                                          <label  class="form-label">Third Name(Arabic)</label>
                                          <input class="form-control input" type="text" id="third_ar_name" name="third_ar_name">
                                      </div>
                                      <div class="form-group">
                                          <label  class="form-label">Last Name(Arabic)</label>
                                          <input class="form-control input" type="text" id="last_ar_name" name="last_ar_name">
                                      </div>
                                    </div>
                                    <!-- End name section -->
                                    <!-- Gender, marital, DoB and Religion -->
                                    <div class="col-md-4">
                                      <div class="form-group">
                                          <label class="form-label" for="gender">Gender *</label>
                                          <select class="form-control input" id="gender" name="gender" aria-placeholder="Gender">
                                              <option value="select" selected disabled></option>
                                              <option value="Male">Male</option>
                                              <option value="Female">Female</option>
                                          </select>
                                      </div>
                                      <div class="form-group">
                                          <label class="form-label" for="marital_status">Marital Status *</label>
                                          <select class="form-control input" id="marital_status" name="marital_status" aria-placeholder="Marital Status" required=1>
                                              <option value="select" selected disabled></option>
                                              <option value="Unmarried">Unmarried</option>
                                              <option value="Married">Married</option>
                                              <option value="Widow">Widow</option>
                                              <option value="Divorce">Divorce</option>
                                              <option value="Unknown">Unknown</option>
                                          </select>
                                      </div>
                                      <div class="form-group">
                                          <label class="form-label" for="dob">Date Of Birth *</label>
                                          <input class="form-control input" type="date" id="dob" onchange="test(this)" name="dob" size="50" required=1>
                                      </div>
                                      <div class="form-group">
                                        <label class="form-label" for="religion">Religion *</label>
                                        <select class="form-control input" id="religion" name="religion" aria-placeholder="Religion"  required=1>
                                            <option value="select" disabled></option>
                                            <option value="Muslim">Muslim</option>
                                            <option value="Christian">Christian</option>
                                            <option value="Hindu">Hindu</option>
                                            <option value="Buddhist">Buddhist</option>
                                            <option value="Unknown">Unknown</option>
                                        </select>
                                      </div>
                                    </div>
                                  <!-- ENd Gender, marital, DoB and Religion -->
                                  <!-- QUalification, Nationality -->
                                  </div>
                                  <hr>
                                  <div class="row">
                                    <div class="col-md-4">
                                      <div class="form-group">
                                          <label class="form-label" for="educational_qualification">Highest Educational Qualification *</label>
                                          <select class="form-control input" id="educational_qualification" name="educational_qualification" aria-placeholder="Select Your Highest Educational Qualification"  required=1>
                                              <option value="select" selected disabled></option>
                                              <option value="Post Graduate">Post Graduate</option>
                                              <option value="Masters">Masters</option>
                                              <option value="Graduate">Graduate</option>
                                              <option value="Diploma">Diploma</option>
                                              <option value="Under Graduate">Under Graduate</option>
                                              <option value="High School">High School</option>
                                          </select>      
                                      </div>
                                      <div class="form-group">
                                          <label  for="university">University / School *</label>
                                          <input class="form-control input" type="text" id="university" name="university" required=1>
                                      </div>
                                    </div>
                                    <div class="col-md-4">
                                      <div class="form-group">
                                          <label class="form-label" for="nationality">Nationality *</label>
                                          <select class="form-control input2" id="nationality" name="nationality" aria-placeholder="Select Your Nationality"  required=1>
                                              <option value="select" selected disabled></option>
                                            
                                          </select>
                                      </div>
                                      <div class="form-group">
                                          <label class="form-label" for="country_code">Country Code</label>
                                          <input class="form-control input2" type="text" id="country_code" name="country_code" onchange="fetchNationality(this)" size="50">
                                      </div>
                                    </div>
                                    <div class="col-md-4">
                                      <div class="form-group">
                                          <label class="form-label" for="sponsor">Sponsor</label>
                                          <input class="form-control input"  type="text" id="sponsor" name="sponsor">
                                      </div>
                                    </div>
                                  </div>
                                  <!-- End QUalification, Nationality -->
                                  <hr>
                                  <!-- Civil -->
                                  <div class="row">
                                    <div class="col-md-4">
                                      <div class="form-group">
                                          <label for="civilid">Civil ID Number</label>
                                          <input class="form-control input" type="text" id="civilid" name="civilid" size="50">
                                      </div>
                                    </div>
                                    <div class="col-md-4">
                                      <div class="form-group">
                                          <label class="form-label" for="civil_expiry_date">Civil ID Expiry Date</label>
                                          <input class="form-control input" type="date" id="civil_expiry_date" name="civil_expiry_date" size="50">
                                      </div>
                                    </div>
                                    <div class="col-md-4">
                                      <div class="form-group">
                                          <label class="form-label" for="paci_no">PACI Number</label>
                                          <input class="form-control input" type="text" id="paci_no" name="paci_no">
                                      </div>
                                    </div>
                                  </div>
                                  <!-- End Civil -->
                                  <hr>
                                  <!-- Passport -->
                                  <div class="row">
                                    <div class="col-md-4">
                                      <div class="form-group">
                                          <label class="form-label" for="passport_no">Passport Number *</label>
                                          <input class="form-control input" type="text" id="passport_no" name="passport_no" required=1>
                                      </div>
                                      <div class="form-group">
                                          <label class="form-label" for="passport_type">Passport Type</label>
                                          <select class="form-control input" id="passport_type" name="passport_type" aria-placeholder="Select Passport Type">
                                              <option value="select" selected disabled></option>
                                              <option value="Normal">Normal</option>
                                              <option value="Diplomat">Diplomat</option>
                                              
                                          </select>
                                      </div>
                                    </div>
                                    <div class="col-md-4">
                                      <div class="form-group">
                                          <label class="form-label" for="passport_date_of_issue">Passport Date of Issue *</label>
                                          <input class="form-control input2" type="date" id="passport_date_of_issue" name="passport_date_of_issue" required=1>
                                      </div>
                                      <div class="form-group">
                                          <label class="form-label" for="passport_expiry_date">Passport Expiry Date *</label>
                                          <input class="form-control input2" type="date" id="passport_expiry_date" name="passport_expiry_date" required=1>
                                      </div>
                                    </div>
                                    <div class="col-md-4">
                                      <div class="form-group">
                                          <label class="form-label" for="birth_place">Place of Birth *</label>
                                          <select class="form-control input2" id="birth_place" name="birth_place" aria-placeholder="Select Your Birth Place"  required=1>
                                            <option value="select" selected disabled></option>
                                          </select>
                                      </div>
                                      <div class="form-group">
                                          <label class="form-label" for="passport_place_of_issue">Passport Place of Issue *</label>
                                          <select class="form-control input2" id="passport_place_of_issue" name="passport_place_of_issue" aria-placeholder="Select Place of Issue" required=1>
                                              <option value="" selected disabled></option>
                                          </select>
                                      </div>
                                    </div>
                                  </div>
                                  <!-- End Passport -->
                                  <hr>
                                  <div class="form-check" id="declare-div">
                                      <input class="form-check-input" type="checkbox" value="" id="confirmData" onchange="document.getElementById('submitForm').disabled = !this.checked;">
                                      <label class="form-check-label" for="confirmData">
                                          <span>I hereby confirm that the above information is correct</span> <span style="color:red">*</span>
                                      </label>
                                  </div>
                                  <br>
                                  <div>
                                      <button class="btn btn-dark" type="button" href="json.json" value="save" id="saveForm" onclick="Save()" >Save</button>
                                      <button class="btn btn-dark" type="button" href="json.json" value="submit" id="submitForm" onclick="Submit()" disabled="disabled" >Submit</button>
                                  </div>
                                </form>

                            </div>

                        </section>
                    </div>
                </div>

              </article>
            </main>
        </div>
      </div>
    </div>
  </div>
</template>




<style>
.jumbotron{
  margin-left: 4%; margin-right: 4%; margin-top: 4%; margin-botton: 4%;
}
.main-container{
    width: 100%;
    height: auto;
    display: block;
}
.form-container{
    width: 100%;
}
.message-block-icon {
	width: 50px;
	min-width: 50px;
	height: 50px;
	display: flex;
	align-items: center;
	justify-content: center;
	background: #5e64ff12;
	border-radius: 50%;
	margin-right: 0.5em;
	color: #fff;
	font-size: 1.5em;
	color: #5e64ff;
	border: 1px solid #5e64ff1c;
}
.message-block-info {
	font-size: 1.8rem;
	font-weight: 700;
	/* color: #5e64ff; */
}
.message-block-info span {
	font-size: 0.875rem;
	font-weight: 400;
	display: block;
	color: #bebfca;
}
.message-block-head{
    display: flex;
}
.tooltiptext {
    color: red;
    /* border: 2px solid black; */
    text-align: center;
    border-radius: 6px;
    padding: 5px 0;
    position: absolute;
    z-index: 1;
    top: 75%;
}
#cover-spin {
	position: fixed;
	width: 100%;
	left: 0;
	right: 0;
	top: 0;
	bottom: 0;
	background-color: rgb(255 255 255 / 0.7);
	z-index: 9999;
	display: none;
}

@-webkit-keyframes spin {
	from {
	  -webkit-transform: rotate(0deg);
	}
	to {
	  -webkit-transform: rotate(360deg);
	}
  }
  
@keyframes spin {
	from {
		transform: rotate(0deg);
	}
	to {
		transform: rotate(360deg);
	}
}

#cover-spin::after {
	content: "";
	display: grid;
	place-items: center;
	position: absolute;
	left: 48%;
	top: 40%;
	width: 40px;
	height: 40px;
	border-style: solid;
	border-color: black;
	border-top-color: transparent;
	border-width: 4px;
	border-radius: 50%;
	-webkit-animation: spin 0.8s linear infinite;
	animation: spin 0.8s linear infinite;
  }
</style>