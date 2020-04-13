frappe.pages['face-recognition'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Face Recognition',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').empty().append(frappe.render_template('face_recognition'));
	
	let preview = document.getElementById("preview");
	let recording = document.getElementById("recording");
	let startButton = document.getElementById("startButton");
	let stopButton = document.getElementById("stopButton");
	let downloadButton = document.getElementById("downloadButton");
	let logElement = document.getElementById("log");

	let recordingTimeMS = 5000;


	function wait(delayInMS) {
		return new Promise(resolve => setTimeout(resolve, delayInMS));
	}

	function startRecording(stream, lengthInMS) {
		let recorder = new MediaRecorder(stream);
		let data = [];

		recorder.ondataavailable = event => data.push(event.data);
		recorder.start();
		console.log(recorder.state + " for " + (lengthInMS/1000) + " seconds...");

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
				let data = [];
		
				recorder.ondataavailable = event => data.push(event.data);
				recorder.start();
				console.log(recorder.state + " for " + (60000/1000) + " seconds...");
		
				let stopped = new Promise((resolve, reject) => {
					recorder.onstop = resolve;
					recorder.onerror = event => reject(event.name);
				});
		
				$('#stopButton').click(function () {
					recorder.stop();
				});
		
				return Promise.all([ stopped ]).then(() => data);
			})
			.then ((recordedChunks) => {
				let recordedBlob = new Blob(recordedChunks, {
					type: "video/webm"
				});
				recording.src = URL.createObjectURL(recordedBlob);
				$('#preview').hide();
				$('#recording').show();
				console.log(recordedBlob);
				console.log("Successfully recorded " + recordedBlob.size + " bytes of " +
					recordedBlob.type + " media.");
				// let rec = new File([recordedBlob], 'rec');
				// console.log(rec);
				
				// $('button.upload').click(function() {
				sendVideoToAPI(recordedBlob);
				// });
			})
			// .catch(log);
			// .then(stream => {
			// 	console.log(stream);
			// 	preview.srcObject = stream;
			// 	downloadButton.href = stream;
			// 	preview.captureStream = preview.captureStream || preview.mozCaptureStream;
			// 	return new Promise(resolve => preview.onplaying = resolve);
			// })
			// .then(() => {
			// 	console.log("Called");
			// 	startRecording(preview.captureStream(), recordingTimeMS)
			// })
			// .then(recordedChunks => {
			// 	let recordedBlob = new Blob(recordedChunks, { type: "video/webm" });
			// 	console.log(recordedBlob);
			// 	//upload it to server part start............................

			// 	/*you have **recordedBlob**  data that is nothing but video data which is getting recorded you can send this data directly to server */

			// 	//Here I am writing sample code to send it to server
			// 	//making request
			// 	var xhr = new XMLHttpRequest();
			// 	//creating form data to append files
			// 	var fd = new FormData();
			// 	//append the recorded blob
			// 	fd.append("video",recordedBlob);
			// 	//send data to server..............
			// 	xhr.send(fd);

			// 	//upload it to server part finish............................

			// 	recording.src = URL.createObjectURL(recordedBlob);  
			// 	downloadButton.href = recording.src;
			// 	downloadButton.download = "RecordedVideo.webm";

			// 	log("Successfully recorded " + recordedBlob.size + " bytes of " +
			// 		recordedBlob.type + " media.");
			// })
			
		}, false);	

		// stopButton.addEventListener("click", function() {
		// stop(preview.srcObject);
		// }, false);

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
    // let request = new XMLHttpRequest();
    // form.append("file",file);
    // request.open("POST",  "/demo/upload", true);
    // request.send(form); // hits the route but doesn't send the file
    // console.log(request.response) // returns nothing

    frappe.xcall('one_fm.one_fm.page.face_recognition.face_recognition.upload_image',{file: fileurl})
	.then(r =>{
		if (!r.exc) {
			// code snippet
		}
	})
	
	// $.ajax({
	// 	url: 'one_fm.one_fm.page.face_recognition.face_recognition.upload_image',
	// 	type: 'POST',   
	// 	success: function (res) {
	// 	   // your code after succes
	// 	},      
	// 	data: fileurl,                
	// 	cache: false,
	// 	contentType: false,
	// 	processData: false
	// });  
  
    // I have also tried this method which hits the route and gets a response however the file is not present in the request when it hits the server. 
    // $.ajax({
    //     url: Routing.generate('upload'),
    //     data: file,
    //     contentType: false,
    //     processData: false,
    //     error: function (res) {
    //         console.log(res);
    //     },
    //     success: function(res) {
    //         console.log(res);
    //     }
    // });
}
