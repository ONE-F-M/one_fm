frappe.ready(function () {
  get_website_info_data();
  get_website_info_count();
  get_clients_info();
  get_jobs_info();


  var $form_0 = $("form[id='frmFileUp_0']");

  $form_0.on("change", "[type='file']", function () {
    var $input = $(this);
    var input = $input.get(0);

    if (input.files.length) {
      input.filedata_0 = { "files_data": [] }; //Initialize as json array.

      window.file_reading = true;

      $.each(input.files, function (key, value) {
        setupReader_0(value, input);
      });

      window.file_reading = false;
    }
  });



  var $form_1 = $("form[id='frmFileUp_1']");

  $form_1.on("change", "[type='file']", function () {
    var $input = $(this);
    var input = $input.get(0);

    if (input.files.length) {
      input.filedata_1 = { "files_data": [] }; //Initialize as json array.

      window.file_reading = true;

      $.each(input.files, function (key, value) {
        setupReader_1(value, input);
      });

      window.file_reading = false;
    }
  });

});




function setupReader_0(file, input) {
  var name = file.name;
  var reader = new FileReader();
  reader.onload = function (e) {
    input.filedata_0.files_data.push({
      "__file_attachment": 1,
      "filename": file.name,
      "dataurl": reader.result
    });
  };
  reader.readAsDataURL(file);
}




function setupReader_1(file, input) {
  var name = file.name;
  var reader = new FileReader();
  reader.onload = function (e) {
    input.filedata_1.files_data.push({
      "__file_attachment": 1,
      "filename": file.name,
      "dataurl": reader.result
    });
  };
  reader.readAsDataURL(file);
}



function get_website_info_data() {
  $("#about_us_title").empty();
  $("#about_us_content").empty();

  $("#our_vision").empty();
  $("#our_mission").empty();

  $("#services_title").empty();
  $("#services_content").empty();

  $("#contact_address").empty();
  $("#contact_phone").empty();
  $("#contact_email").empty();

  $("#social_media").empty();

  frappe.call({
    method: 'one_fm.templates.pages.homepage.get_website_info_data',
    callback: function (r) {
      console.log("rr2222");
      if (r) {
        $("#about_us_title").html(r.message[0]);

        var about_us_content = "<h4 class='text-center'>" + r.message[1] + "</h4>";
        $.each(r.message[2] || [], function (i, d) {
          about_us_content += "<p><i class='" + d[0] + "'></i>   " + d[1] + "</p>";

        });
        $("#about_us_content").append(about_us_content);

        var our_vision_content = "";
        $.each(r.message[3] || [], function (i, d) {
          our_vision_content += "<li>" + d[0] + "</li>";

        });
        $("#our_vision").append(our_vision_content);

        var our_mission_content = "";
        $.each(r.message[4] || [], function (i, d) {
          our_mission_content += "<li>" + d[0] + "</li>";

        });
        $("#our_mission").append(our_mission_content);

        $("#services_title").html(r.message[5]);

        var services_content = "";
        $.each(r.message[6] || [], function (i, d) {
          services_content += "<div class='col-12 col-sm-6 col-lg-4'><div class='single-feature'><i class='" + d[0] + "'></i><h5>" + d[1] + "</h5><p>" + d[2] + "</p></div></div>";

        });
        $("#services_content").append(services_content);

        $("#contact_address").append("<p><span>Address:</span> " + r.message[7] + "</p>");
        $("#contact_phone").append("<p><span>Phone:</span> " + r.message[8] + "</p>");
        $("#contact_email").append("<p><span>Email:</span> " + r.message[9] + "</p>");

        var social_media = "";

        if (r.message[10]) {
          social_media += "<a href='" + r.message[10] + "' class='external facebook'><i class='fab fa-facebook-f'></i></a>";
        }
        if (r.message[11]) {
          social_media += "<a href='" + r.message[11] + "' class='external youtube'><i class='fab fa-youtube'></i></a>";
        }
        if (r.message[12]) {
          social_media += "<a href='" + r.message[12] + "' class='external twitter'><i class='fab fa-twitter'></i></a>";
        }
        if (r.message[13]) {
          social_media += "<a href='" + r.message[13] + "' title='' class='external instagram'><i class='fab fa-instagram'></i></a>";
        }
        if (r.message[9]) {
          social_media += "<a href='mailto:" + r.message[9] + "' class='email'><i class='fa fa-envelope'> </i></a>";
        }



        $("#social_media").append(social_media);


      }
    }
  });
}



function get_website_info_count() {
  $("#project_count").empty();
  $("#employee_count").empty();
  $("#sites_count").empty();
  $("#clients_count").empty();

  frappe.call({
    method: 'one_fm.templates.pages.homepage.get_website_info_count',
    callback: function (r) {
      if (r) {
        $("#project_count").html(r.message[0]);
        $("#employee_count").html(r.message[1]);
        $("#sites_count").html(r.message[2]);
        $("#clients_count").html(r.message[3]);
      }
    }
  });





  // console.log('hii');
  // $.ajax({
  //   type: 'POST',
  //     // url: "http://35.222.162.1/api/method/one_fm.templates.pages.homepage.get_website_info_count",
  //     url: "http://35.222.162.1/api/method/version",
  //     dataType: 'json',
  //     success: function(data, textStatus, xhr) {
  //         console.log(data);
  //         alert("Success");
  //     },
  //     error: function(data, textStatus, xhr) {
  //       console.log(data);
  //         alert("Failure");
  //     }
  // });




  // curl -X POST http://35.222.162.1/api/method/one_fm.templates.pages.homepage.get_website_info_count -d "command_string=ON&position=1"


  // $.ajax({
  //     url: "http://159.65.73.207/api/method/one_fm.templates.pages.homepage.get_website_info_count",
  //     type: 'POST',
  //     dataType: 'json',
  //     success: function(data, textStatus, xhr) {
  //         console.log(data)
  //         alert("Success");
  //     },
  //     error: function(data, textStatus, xhr) {
  //         alert("Failure");
  //     }
  // });





}



function get_clients_info() {
  $("#our_clients_info").empty();
  frappe.call({
    method: "one_fm.templates.pages.homepage.get_clients_info",
    callback: function (r) {
      if (r.message) {
        var content = "";

        for (let client = 0; client < r.message[0].length; client++) {

          $("#our_clients_info").empty();

          content += "<div class='col-12 col-md-6 col-lg-2'><div class='single-team-member'><div class='member-image'><img src='" + r.message[0][client] + "' alt=''><div class='team-hover-effects'></div></div><div class='member-text text-center'><h4>" + r.message[1][client] + "</h4></div></div></div>";
        }

        $("#our_clients_info").append(content);

      }
    }
  });

}






function get_jobs_info() {
  $("#our-jobs").empty();
  frappe.call({
    method: "one_fm.templates.pages.homepage.get_jobs_info",
    callback: function (r) {

      var content = "";
      var content_modal = "";
      if (r.message) {
        for (let job = 0; job < r.message[0].length; job++) {

          $("#our-jobs").empty();

          content += "<div class='single-project col-lg-4 col-md-4 col-sm-6 col-xs-12'><div class='hover ehover11'><img class='img-responsive' src='assets/one_fm/assets/img/bg-img/Welcome-Background.jpg' alt=''><div class='projectoverlay'><h2>" + r.message[1][job] + "</h2><button class='info nullbutton showmorebutton' data-toggle='modal' data-target='#modal" + job + "'>Read More</button></div></div></div>";
          content_modal += "<div id='modal" + job + "' class='modal fade'><div class='modal-dialog modal-lg'><div class='modal-content'><div class='modal-header right-to-left'><button type='button' class='close' data-dismiss='modal' aria-hidden='true'>&times;</button><h2 class='modal-title'>Check job description below before apply</h2></div><div class='modal-body'><h3>" + r.message[1][job] + "</h3><p> " + r.message[2][job] + "</p><button type='button' class='btn btn-primary' onclick='document.getElementById(\"" + r.message[0][job] + "\").classList.toggle(\"hidden\");'>Apply</button></div><div class='modal-applyed hidden' id='" + r.message[0][job] + "'><hr><form id='frmFileUp_" + job + "'><div class='form-group'><label for='applicant_name'>Applicant Name</label><input type='text' class='form-control' name='applicant_name_" + job + "' id='applicant_name_" + job + "' placeholder='Enter name' required></div><div class='form-group'><label for='applicant_email'>Email Address</label><input type='email' class='form-control' name='applicant_email_" + job + "' id='applicant_email_" + job + "' placeholder='Enter email' required></div><div class='form-group'><label for='applicant_cover'>Cover Letter</label><textarea class='form-control' name='applicant_cover_" + job + "' id='applicant_cover_" + job + "' rows='3'></textarea></div><div class='form-group'><label for='applicant_files'>Resume Attachment</label><input type='file' class='form-control-file' name='applicant_files_" + job + "' id='applicant_files_" + job + "'></div><button type='button' id='btn_upload_" + job + "' class='btn btn-primary' onclick='add_new_job_applicant(\"" + r.message[0][job] + "\",\"" + job + "\")'>Submit</button></form></div></div></div></div>";

        }

        $("#our-jobs").append(content + content_modal);

      }
    }
  });

}




function send_contact_email() {
  frappe.call({
    method: 'one_fm.templates.pages.homepage.send_contact_email',
    args: {
      contact_name: $('#name').val(),
      contact_email: $('#email').val(),
      contact_subject: $('#subject').val(),
      contact_message: $('#message').val()
    },
    callback: function (r) {
      if (r) {

        console.log(r.message);

        if (r.message == 1) {
          Swal.fire(
            'Successfully Sent!',
            'Your message has been sent.',
            'success'
          );

          $('#name').val('');
          $('#email').val('');
          $('#subject').val('');
          $('#message').val('');
        } else {
          Swal.fire({
            icon: 'error',
            title: 'Could not send...',
            text: 'Please try again!'
          });
        }

      }
    }
  });
}




function add_new_job_applicant(job_opening, job_count) {
  frappe.call({
    method: 'one_fm.templates.pages.homepage.add_new_job_applicant',
    args: {
      job_opening: job_opening,
      applicant_name: $('#applicant_name_' + job_count).val(),
      applicant_email: $('#applicant_email_' + job_count).val(),
      applicant_cover: $('#applicant_cover_' + job_count).val(),
      applicant_files: $('#applicant_files_' + job_count).val()
    },
    callback: function (r) {
      if (r) {
        if (r.message[0] == 1) {
          // console.log(r.message)
          // console.log(r.message[1])

          var filedata = $('#applicant_files_' + job_count).prop('files');

          upload_attach_file(r.message[1], job_count, filedata);

        } else {

          Swal.fire({
            title: 'You have already applied for this job!',
            text: "Do you want to overwrite the existing proposal?",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Yes, overwrite!'
          }).then((result) => {
            if (result.value) {
              edit_job_applicant(r.message, job_opening, job_count);
            }
          });


        }
      }
    }
  });
}



function upload_attach_file(job_applicant, job_count, filedata) {
  var filedata_new = $('#applicant_files_' + job_count).prop('files');

  console.log(filedata);

  frappe.call({
    method: "one_fm.templates.pages.homepage.attach_file_to_application",
    args: { "filedata": filedata, "job_applicant_name": job_applicant },
    freeze: true,
    freeze_message: __("Upload files..."),
    callback: function (r) {

      console.log(r.message);
      if (!r.exc) {

        Swal.fire(
          'Successfully added!',
          'Your proposal has been added.',
          'success'
        );

        $('#applicant_name_' + job_count).val('');
        $('#applicant_email_' + job_count).val('');
        $('#applicant_cover_' + job_count).val('');
        $('#applicant_files_' + job_count).val('');

      } else {

        Swal.fire({
          icon: 'error',
          title: 'Files not uploaded...',
          text: 'Please try again!'
        });

      }
    }
  });
}




function edit_job_applicant(job_applicant, job_opening, job_count) {
  var applicant_name = $('#applicant_name_' + job_count).val();
  var applicant_email = $('#applicant_email_' + job_count).val();
  var applicant_cover = $('#applicant_cover_' + job_count).val();
  var filedata = $('#applicant_files_' + job_count).prop('files');

  frappe.call({
    method: 'one_fm.templates.pages.homepage.edit_job_applicant',
    args: {
      job_applicant: job_applicant,
      job_opening: job_opening,
      applicant_name: applicant_name,
      applicant_email: applicant_email,
      applicant_cover: applicant_cover,
      applicant_files: filedata
    },
    freeze: true,
    freeze_message: __("Upload files..."),
    callback: function (r) {
      if (r) {
        if (r.message == 1) {

          Swal.fire(
            'Edited!',
            'Your proposal has been edited.',
            'success'
          );
          $('#applicant_name_' + job_count).val('');
          $('#applicant_email_' + job_count).val('');
          $('#applicant_cover_' + job_count).val('');
          $('#applicant_files_' + job_count).val('');

        }
      }
    }
  });
}








function request_new_quote() {
  frappe.call({
    method: 'one_fm.templates.pages.homepage.request_new_quote',
    args: {
      person_name: $('#person_name').val(),
      organization_name: $('#organization_name').val(),
      quote_email: $('#quote_email').val(),
      mobile_no: $('#mobile_no').val(),
      quote_notes: $('#quote_notes').val()
    },
    callback: function (r) {
      if (r) {
        if (r.message == 1) {
          Swal.fire(
            'Successfully added!',
            'Your Request has been added.',
            'success'
          );

          $('#person_name').val('');
          $('#organization_name').val('');
          $('#quote_email').val('');
          $('#mobile_no').val('');
          $('#quote_notes').val('');

        } else {
          Swal.fire({
            icon: 'error',
            title: 'Request not added...',
            text: 'Please try again!'
          });
        }
      }
    }
  });
}