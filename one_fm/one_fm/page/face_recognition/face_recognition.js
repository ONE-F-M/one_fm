frappe.pages['face-recognition'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Face Recognition',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').empty().append(frappe.render_template('face_recognition'));
	frappe.db.get_value("Employee", {"user_id":frappe.session.user}, "*", function(r){
		let {image, employee_name, company, department, designation} = r;
		let card = `
		<div class="card">
			<img src="${image}" alt="Profile" style="width:100%">
			<div class="title">${employee_name}</div>
			<h5>${company}</h5>
			<h5>${department}</h5>			
			<h5>${designation}</h5>
		</div>`;
		$('#profile-card').prepend(card);
	})

	let preview = document.getElementById("preview");
	let startButton = document.getElementById("startButton");	
	let enrollButton = document.getElementById('enrollButton');
	let enroll_preview = document.getElementById('enroll_preview');
		
	startButton.addEventListener("click", function() {
		$('.verification').show();
		$('.enrollment').hide();
		navigator.mediaDevices.getUserMedia({
			video: true,
			audio: false,
			width: 700
		})
		.then((stream) => {
			window.localStream = stream;
			preview.srcObject = stream;
			preview.captureStream = preview.captureStream || preview.mozCaptureStream;
			return new Promise(resolve => preview.onplaying = resolve);
		})
		
	}, false);	
	$('#verify').on('click', function(){
		takeSnapshot(preview, 'verify');
		stop(preview);
	});
	enrollButton.addEventListener("click", function() {
		$('.enrollment').show();
		$('.verification').hide();
		navigator.mediaDevices.getUserMedia({
			video: true,
			audio: false
		})
		.then((stream) => {
			window.localStream = stream;
			enroll_preview.srcObject = stream;
			enroll_preview.captureStream = enroll_preview.captureStream || enroll_preview.mozCaptureStream;
			return new Promise(resolve => enroll_preview.onplaying = resolve);
		})
	}, false);	
	$('#enroll').on('click', function(){
		
		takeSnapshot(enroll_preview, 'enroll');
		stop(enroll_preview);
	});

}

/**
 *  generates a still frame image from the stream in the <video>
 */
function takeSnapshot(video, type) {
	var img = $('#picture');
	var context;
	var width = '500'
		, height = '400';

	let canvas = document.createElement('canvas');
	canvas.width = width;
	canvas.height = height;

	context = canvas.getContext('2d');
	context.drawImage(video, 0, 0, width, height);
	let image = canvas.toDataURL('image/png');
	if(type == "enroll"){
		enroll(image, frappe.session.user);
	}else{
		verify(image, frappe.session.user);
	}
}

function on_success(uploader, button){
	let btn = $(button)
	let files = uploader.uploader.files;
	let val = ``;

	//check if all the files are uploaded
	if(files[files.length-1].progress === files[files.length-1].total && files[files.length-1].doc){
		for(let i=0; i<files.length; i++){
			let file = files[i].doc.file_url;
			enroll(file, frappe.session.user);
		}
	}
}


function enroll(image, subject_id){
	console.log(image, subject_id);
	var settings = {
		"url": "https://api.kairos.com/enroll",
		"method": "POST",
		"timeout": 0,
		"headers": {
		  "Content-Type": ["application/json", "text/plain"],
		  "app_id": "8b64e789",
		  "app_key": "0fc047c182bd4b7e6e3e7fbf4e43ebce"
		},
		"data": JSON.stringify({
			"image": `${window.location.origin}${image}`,
			"gallery_name": "one-fm",
			"subject_id": subject_id,
			"selector":"liveness"
		}),
	  };
	  
	  $.ajax(settings).done(function (response) {
		console.log(response);
		if(response.face_id){
			frappe.msgprint("Successfully Enrolled. Now you can try face recognition.")
		}
	  });
}
function verify(image, subject_id){
	var settings = {
		"url": "https://api.kairos.com/verify",
		"method": "POST",
		"timeout": 0,
		"headers": {
		  "Content-Type": ["application/json", "text/plain"],
		  "app_id": "8b64e789",
		  "app_key": "0fc047c182bd4b7e6e3e7fbf4e43ebce"
		},
		"data": JSON.stringify({
			"image": `${image}`,
			"gallery_name": "one-fm",
			"subject_id": subject_id,
			"selector":"liveness"
		}),
	  };
	  console.log(settings);
	  $.ajax(settings).done(function (response) {
		if(response.images.length > 0){
			let {confidence, liveness} = response.images[0].transaction;
			frappe.msgprint(`<div>Face Recognition Confidence %age: <b>${confidence * 100}</b> </div><br><div> Liveness Detection %age:<b>${liveness * 100}</b></div>`);
		}
	  });
}

function stop(videoEl){
	localStream.getTracks().forEach( (track) => {
		track.stop();	
	});
	// stop only video
	localStream.getVideoTracks()[0].stop();
	videoEl.srcObject = null;
}
