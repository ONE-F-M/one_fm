frappe.pages['face-recognition'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Face Recognition',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').empty().append(frappe.render_template('face_recognition'));
	
	frappe.db.get_value("Employee", {"user_id":"k.sharma@armor-services.com"}, "*", function(r){
		// console.log(r)
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
	let stopButton = document.getElementById("stopButton");

	let recordingTimeMS = 5000;

	function wait(delayInMS) {
		return new Promise(resolve => setTimeout(resolve, delayInMS));
	}

	function startRecording(stream, lengthInMS) {
		let recorder = new MediaRecorder(stream);
		let data = [];

		recorder.ondataavailable = event => data.push(event.data);
		recorder.start();
		// console.log(recorder.state + " for " + (lengthInMS/1000) + " seconds...");

		let stopped = new Promise((resolve, reject) => {
		recorder.onstop = resolve;
		recorder.onerror = event => reject(event.name);
		});

		let recorded = wait(lengthInMS).then(
		() => recorder.state == "recording" && recorder.stop()
		);

		return Promise.all([
			stopped,
			recorded
		])
		.then(() => data);
	}

	function stop(stream) {
		stream.getTracks().forEach(track => track.stop());
	}

	startButton.addEventListener("click", function() {
		navigator.mediaDevices.getUserMedia({
				video: true,
				audio: false
			})
			.then((stream) => {
				preview.srcObject = stream;
				preview.captureStream = preview.captureStream || preview.mozCaptureStream;
				return new Promise(resolve => preview.onplaying = resolve);
			})
			.then(() => {
				let recorder = new MediaRecorder(preview.captureStream());

				setTimeout(function(){ 
					$('#cover-spin').show(0);
					recorder.stop(); 
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
				upload_file(recordedBlob);
			})
		}, false);	
}


function upload_file(file){
	return new Promise((resolve, reject) => {
        let xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/method/one_fm.one_fm.page.face_recognition.face_recognition.upload_file", true);
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
					frappe.msgprint(r.message);
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
	// console.log(blob);
    let file = new File([blob], 'recording');

    // console.log(file); // test to see if appending form data would work, it didn't this is completely empty. 
	const reader = new FileReader();
	reader.addEventListener('loadend', () => {
		// console.log(reader);
	   // reader.result contains the contents of blob as a typed array
	});
	reader.readAsArrayBuffer(blob);
	const fileurl = URL.createObjectURL(blob);
    let form = new FormData();
    form.append('video', file);
    // console.log(fileurl); // test to see if appending form data would work, it didn't this is completely empty. 
    
    frappe.xcall('one_fm.one_fm.page.face_recognition.face_recognition.upload_image',{file: fileurl})
	.then(r =>{
		if (!r.exc) {
			// code snippet
		}
	})
	
}
