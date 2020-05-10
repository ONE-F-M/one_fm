frappe.pages['face-recognition'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Face Recognition',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').empty().append(frappe.render_template('face_recognition'));
	
	frappe.db.get_value("Employee", {"user_id":frappe.session.user}, "*", function(r){
		console.log(r)
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
	let enroll_preview = document.getElementById("enroll_preview");
	let startButton = document.getElementById("startButton");


	enrollButton.addEventListener("click", function() {
		$('.enrollment').show();
		$('.verification').hide();
		$('#cues').empty().append(`<div class="alert alert-danger">Please remove your spectacles. Follow the instructions here after clicking Enroll button.</div>`);
	}, false);	

	startButton.addEventListener("click", function() {
		$('.verification').show();
		$('.enrollment').hide();
		countdown();		
		navigator.mediaDevices.getUserMedia({
			video: {
				width: { ideal: 1024 },
				height: { ideal: 768 },
				frameRate: {ideal: 10, max: 20},
				facingMode: 'user'
			},
			audio: false
		})
		.then((stream) => {			
			window.localStream = stream;
			preview.srcObject = stream;
			preview.captureStream = preview.captureStream || preview.mozCaptureStream;
			return new Promise(resolve => preview.onplaying = resolve);
		})
		.then(() => {
			let recorder = new MediaRecorder(preview.captureStream());

			setTimeout(function(){ 
				$('#cover-spin').show(0);
				recorder.stop(); 
				stop(preview);
			}, 5000);
			let data = [];
	
			recorder.ondataavailable = event => data.push(event.data);
			recorder.start();
	
			let stopped = new Promise((resolve, reject) => {
				recorder.onstop = resolve;
				recorder.onerror = event => reject(event.name);
			});
	
			return Promise.all([ stopped ]).then(() => data);
		})
		.then ((recordedChunks) => {
			let recordedBlob = new Blob(recordedChunks, {
				type: "video/mp4",
			});
			console.log(recordedBlob);
			upload_file(recordedBlob, 'verify');
		})
	}, false);	

	$('#enroll').on('click', function(){
		show_cues();
		navigator.mediaDevices.getUserMedia({
			video: {
				width: { ideal: 1024 },
				height: { ideal: 768 },
				frameRate: {ideal: 10, max: 20},
				facingMode: 'user'
			},
			audio: false
		})
		.then((stream) => {			
			window.localStream = stream;
			enroll_preview.srcObject = stream;
			enroll_preview.captureStream = enroll_preview.captureStream || enroll_preview.mozCaptureStream;
			return new Promise(resolve => enroll_preview.onplaying = resolve);
		})
		.then(() => {
			let recorder = new MediaRecorder(enroll_preview.captureStream());

			setTimeout(function(){ 
				$('#cover-spin').show(0);
				recorder.stop(); 
				stop(enroll_preview);
			}, 13000);
			let data = [];
	
			recorder.ondataavailable = event => data.push(event.data);
			recorder.start();
	
			let stopped = new Promise((resolve, reject) => {
				recorder.onstop = resolve;
				recorder.onerror = event => reject(event.name);
			});
	
			return Promise.all([ stopped ]).then(() => data);
		})
		.then ((recordedChunks) => {
			let recordedBlob = new Blob(recordedChunks, {
				type: "video/mp4",
			});
			console.log(recordedBlob);
			upload_file(recordedBlob, 'enroll');
		})	
	});	
}


function upload_file(file, method){
	let method_map = {
		'enroll': '/api/method/one_fm.one_fm.page.face_recognition.face_recognition.enroll',
		'verify': '/api/method/one_fm.one_fm.page.face_recognition.face_recognition.verify'
	}

	return new Promise((resolve, reject) => {
        let xhr = new XMLHttpRequest();
        xhr.open("POST", method_map[method], true);
        xhr.setRequestHeader("Accept", "application/json");
        xhr.setRequestHeader("X-Frappe-CSRF-Token", frappe.csrf_token);

		let form_data = new FormData();
    	form_data.append("file", file, frappe.session.user+".mp4");
		xhr.onreadystatechange = () => {
			if (xhr.readyState == XMLHttpRequest.DONE) {
			  	$('#cover-spin').hide();
			  	if (xhr.status === 200) {
				let r = null;
				try {
					r = JSON.parse(xhr.responseText);
					console.log(r);
					frappe.msgprint(__(r.message), __("Successful"));
				} catch (e) {
					r = xhr.responseText;
				}
			  } else if (xhr.status === 403) {
				let response = JSON.parse(xhr.responseText);
				frappe.msgprint({
				  title: __("Not permitted"),
				  indicator: "red",
				  message: response._error_message,
				});
			  } else {
				let error = null;
				try {
				  error = JSON.parse(xhr.responseText);
				} catch (e) {
				  // pass
				}
				frappe.request.cleanup({}, error);
			  }
			}
		  };
		xhr.send(form_data);
    });
}

function sendVideoToAPI (blob) {
	// let fd = new FormData();
	console.log(blob);
    let file = new File([blob], 'recording');

    console.log(file); // test to see if appending form data would work, it didn't this is completely empty. 
	const reader = new FileReader();
	reader.addEventListener('loadend', () => {
		console.log(reader);
	   // reader.result contains the contents of blob as a typed array
	});
	reader.readAsArrayBuffer(blob);
	const fileurl = URL.createObjectURL(blob);
    let form = new FormData();
    form.append('video', file);
    console.log(fileurl); // test to see if appending form data would work, it didn't this is completely empty. 
    
    frappe.xcall('one_fm.one_fm.page.face_recognition.face_recognition.upload_image',{file: fileurl})
	.then(r =>{
		if (!r.exc) {
			// code snippet
		}
	})
	
}

function countdown(){
	let timeleft = 5;
	let downloadTimer = setInterval(function(){
	if(timeleft <= 0){
		clearInterval(downloadTimer);
		$("#countdown").empty();
	} else {
		$("#countdown").empty().append(`<div class="alert alert-info"><span class="cues">Blink your eyes. <span class="countdown">${timeleft}</span><span></div>`);
	}
	timeleft -= 1;
	}, 1000);
}

function stop(videoEl){
	localStream.getTracks().forEach( (track) => {
		track.stop();	
	});
	// stop only video
	localStream.getVideoTracks()[0].stop();
	videoEl.srcObject = null;
}

function show_cues(){
	let timeleft = 13;
	let downloadTimer = setInterval(function(){
	if(timeleft <= 0){
		clearInterval(downloadTimer);
		$("#cues").empty()
	} else if(timeleft > 10) {
		$("#cues").empty().append(`<div class="alert alert-info"> <span class="cues"> Look Straight at the camera. <span class="countdown">${timeleft - 10}</span><span></div>`);
	} else if(timeleft <= 10 && timeleft > 5) {
		$("#cues").empty().append(`<div class="alert alert-info"><i class="fa fa-arrow-left fa-icon"></i> <span class="cues"> Turn your face left slowly and return to straight position. <span class="countdown">${timeleft - 5}</span></span></div>`);
	} else if(timeleft <= 5) {
		$("#cues").empty().append(`<div class="alert alert-info"><i class="fa fa-arrow-right fa-icon"></i> <span class="cues"> Turn your face right slowly and return to straight position. <span class="countdown">${timeleft}</span></span></div>`);
	} 
	timeleft -= 1;
	}, 1000);	
}
