frappe.ready(function () {
	var form = $("#attachment_form");
	var form_data = {};

	frappe.call({
        method: "one_fm.templates.pages.gp_letter_attachment.get_candidates",
        args:{
        	pid: $('#pid').val()
        },
        callback: function (r) {
            if(r.message){
            	$("#attachments_fields").empty();
            	var content = ""

                for (let i = 0; i < r.message.length; i++) {
                	content+= "<div class='form-group'><label class='col-form-label'>"+r.message[i][1]+"</label><div class='input-group'><span class='input-group-addon'><i class='fa fa-file'></i></span><input type='file' name='"+r.message[i][0]+"' id='"+r.message[i][0]+"' class='form-control' required='required'></div></div>"
                }

                $("#attachments_fields").append(content)

            }
        }
    });

	$(':file').on('change', function() {
	    var $input = $(this);
      	var file_input = $input.get(0);

	    if (file_input.files[0].size > 5242880) {
	        alert('max upload size is 5 Mega Byte');
	    }

	    if(file_input.files.length) {
        	file_input.filedata = { "files_data" : [] };
   		}

   		window.file_reading = true;

   		//this will handle multi files input
        $.each(file_input.files, function(key, value) {
          setupReader(value, file_input);
        });

        window.file_reading = false;

	});


	$("#attachment_form").submit(function(e){

		$.each(form.serializeArray(), function (i, field) {
	        form_data[field.name] = field.value || "";
	    });


		// form_data["gp_letter_candidate1"] = $('#gp_letter_candidate1').prop('filedata');


		// frappe.call({
	 //        method: "one_fm.templates.pages.gp_letter_attachment.get_candidates",
	 //        args:{
	 //        	pid: $('#pid').val()
	 //        },
	 //        callback: function (r) {
	 //            if(r.message){
	 //                for (let i = 0; i < r.message.length; i++) {
	 //                	form_data[r.message[i][0]] = $('#'+r.message[i][0]).prop('filedata');		                	
	 //                }

	 //            }
	 //        }
	 //    });

	 qp_letter=[]
	     $("[type='file']").each(function(i){
		    form_data[$(this).attr("id")] = $('#'+$(this).attr("id")).prop('filedata');
		    qp_letter.push($(this).attr("id"))
		  });


		// form_data["GPL-000001"] = $('#GPL-000001').prop('filedata');
		// form_data["GPL-000002"] = $('#GPL-000002').prop('filedata');

		console.log(form_data)
		console.log(qp_letter)

	    frappe.call({
			type: "PUT",
	        method: "one_fm.templates.pages.gp_letter_attachment.get_attachment_details",
	        args:{data: form_data, qp_letter: qp_letter},
	        freeze: true,
			freeze_message: __("Upload files..."), 
	        callback: function (r) {
	            if(r.message){
	                if(r.message ==='success'){
	                    frappe.msgprint(__("Your application was sent"), title='Success', indicator='green')

	                }
	                else{
	                	console.log(r.message)
	                    frappe.msgprint(__(r.message))
	                }
	            }
	        }
	    });

    	return false;
	});
});

function setupReader(file, input) {
	let name = file.name;
	var reader = new FileReader();  
	reader.onload = function(e) {
	  input.filedata.files_data.push({
	    "__file_attachment": 1,
	    "filename": file.name,
	    "dataurl": reader.result
	  })
	}
	reader.readAsDataURL(file);
}

