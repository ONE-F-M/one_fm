frappe.pages['face-recognition'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Face Recognition',
		single_column: true
	});

	$(wrapper).find('.layout-main-section').empty().append(frappe.render_template('face_recognition'));

	let preview = document.getElementById("preview");
	let enroll_preview = document.getElementById("enroll_preview");
	let startButton = document.getElementById("startButton");
	let endButton = document.getElementById("endButton");
	let hourlyButton = document.getElementById("hourlyButton");
    let locationButton = document.getElementById("locationButton");
	let errorButton = document.getElementById("errorButton");

	frappe.db.get_value("Employee", {"user_id":frappe.session.user}, "*", function(r){
        if(r){
            let {image, employee_name, company, department, designation, enrolled} = r;
            let card = `
            <div class="card">
                <img src="${image}" alt="Profile" style="width:100%">
                <div class="title">${employee_name}</div>
                <h5>${company}</h5>
                <h5>${department}</h5>			
                <h5>${designation}</h5>
            </div>`;
			$('#profile-card').prepend(card);
			page.enrolled = enrolled;
			if(!enrolled){
				$(enrollButton).show();	
			}
			else{
				check_existing(page, startButton, endButton, hourlyButton);
			}
        }
	})

    get_location(page);
    locationButton.addEventListener("click", function() {
        get_location(page);
    }, false);	

	enrollButton.addEventListener("click", function() {
		$('.enrollment').show();
		$('.verification').hide();
		$('#cues').empty().append(`<div class="alert alert-danger">Please remove your spectacles. Follow the instructions here after clicking Enroll button.</div>`);
	}, false);	
	
	errorButton.addEventListener("click", function() {
		make_support_issue();
	}, false);
	
	startButton.addEventListener("click", function() {
        send_log('IN', 0)
    }, false);	
    
	hourlyButton.addEventListener("click", function() {
        send_log('IN', 1)
    }, false);		
    
    endButton.addEventListener("click", function() {
        send_log('OUT', 0)
	}, false);	
    
    $('#enroll').on('click', function(){
		show_cues();
		navigator.mediaDevices.getUserMedia({
			video: {
				width: { ideal: 1024 },
				height: { ideal: 768 },
				frameRate: {ideal: 4},//, max: 20},
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

function load_gmap(position){
	console.log(position);
	let {latitude, longitude} = position.coords;
	var map = new google.maps.Map(document.getElementById('map'), {
		zoom: 15,
		center: {lat: latitude, lng: longitude}
	});
	let locationMarker = new google.maps.Marker({
		map: map,
		animation: google.maps.Animation.DROP,
		position: {lat: latitude, lng: longitude}
	});
	markers.push(locationMarker);
	addYourLocationButton(map, locationMarker);
}
//______________________________________________________________________________________________________________________
//______________________________________________________________________________________________________________________
//______________________________________________________________________________________________________________________
//______________________________________________________________________________________________________________________
//______________________________________________________________________________________________________________________


function get_location(page){
    if (navigator.geolocation) {
		window.markers = [];
		window.circles = [];
		// JS API is loaded and available
		console.log("Called")
		navigator.geolocation.getCurrentPosition(
            position => {
				page.position = position;
				load_gmap(position);
                $('#button-controls').show();
                $('#sync-location').hide();
            },
            error => {
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        frappe.msgprint(__(`
                            <b>Please enable location permissions to proceed further.</b>
                            1. <b>Firefox</b>:
                            <br> Tools > Page Info > Permissions > Access Your Location. Select Always Ask.<br>
                            2. <b>Chrome</b>: 
                            <br> Hamburger Menu > Settings > Show advanced settings.<br> 
                                In the Privacy section, click Content Settings. <br>
                                In the resulting dialog, find the Location section and select Ask when a site tries to... .<br>
                                Finally, click Manage Exceptions and remove the permissions you granted to the sites you are interested in.<br><br>
                            <b>After enabling, click on the <i>Get Location</i> button</b> or <b>Reload</b>.`));
                        break;
                    case error.POSITION_UNAVAILABLE:
                        frappe.msgprint(__("Location information is unavailable."));
                        break;
                    case error.TIMEOUT:
                        frappe.msgprint(__("The request to get user location timed out."));
                        break;
                    case error.UNKNOWN_ERROR:
                        frappe.msgprint(__("An unknown error occurred."));
                        break;
                }
            }
        );
    } else { 
        frappe.msgprint(__("Geolocation is not supported by this browser."));
    }
}

function addYourLocationButton (map, marker){
	console.log(map, marker);
    var controlDiv = document.createElement('div');

    var firstChild = document.createElement('button');
    firstChild.style.backgroundColor = '#fff';
    firstChild.style.border = 'none';
    firstChild.style.outline = 'none';
    firstChild.style.width = '40px';
    firstChild.style.height = '40px';
    firstChild.style.borderRadius = '2px';
    firstChild.style.boxShadow = '0 1px 4px rgba(0,0,0,0.3)';
    firstChild.style.cursor = 'pointer';
    firstChild.style.marginRight = '10px';
    firstChild.style.padding = '0';
    firstChild.title = 'Click to get your location.';
    controlDiv.appendChild(firstChild);

    var secondChild = document.createElement('div');
    secondChild.style.margin = 'auto';
    secondChild.style.width = '19px';
    secondChild.style.height = '19px';
    secondChild.style.backgroundImage = 'url(https://maps.gstatic.com/tactile/mylocation/mylocation-sprite-2x.png)';
    secondChild.style.backgroundSize = '180px 18px';
    secondChild.style.backgroundPosition = '0 0';
    secondChild.style.backgroundRepeat = 'no-repeat';
    firstChild.appendChild(secondChild);

    google.maps.event.addListener(map, 'center_changed', function () {
        secondChild.style['background-position'] = '0 0';
    });

    firstChild.addEventListener('click', function () {
        var imgX = '0',
            animationInterval = setInterval(function () {
                imgX = imgX === '-18' ? '0' : '-18';
                secondChild.style['background-position'] = imgX+'px 0';
            }, 500);

        if(navigator.geolocation) {
            // navigator.geolocation.getCurrentPosition(function(position) {
            //     var latlng = new google.maps.LatLng(position.coords.latitude, position.coords.longitude);
            //     map.setCenter(latlng);
            //     clearInterval(animationInterval);
            //     secondChild.style['background-position'] = '-144px 0';
			// });
			navigator.geolocation.getCurrentPosition(
				position => {
					cur_page.page.position = position;
					let latlng = new google.maps.LatLng(position.coords.latitude, position.coords.longitude);
    	            map.setCenter(latlng);
					clearInterval(animationInterval);
					secondChild.style['background-position'] = '-144px 0';
				},
				error => {
					switch(error.code) {
						case error.PERMISSION_DENIED:
							frappe.msgprint(__(`
								<b>Please enable location permissions to proceed further.</b>
								1. <b>Firefox</b>:
								<br> Tools > Page Info > Permissions > Access Your Location. Select Always Ask.<br>
								2. <b>Chrome</b>: 
								<br> Hamburger Menu > Settings > Show advanced settings.<br> 
									In the Privacy section, click Content Settings. <br>
									In the resulting dialog, find the Location section and select Ask when a site tries to... .<br>
									Finally, click Manage Exceptions and remove the permissions you granted to the sites you are interested in.<br><br>
								<b>After enabling, click on the <i>Get Location</i> button</b> or <b>Reload</b>.`));
							break;
						case error.POSITION_UNAVAILABLE:
							frappe.msgprint(__("Location information is unavailable."));
							break;
						case error.TIMEOUT:
							frappe.msgprint(__("The request to get user location timed out."));
							break;
						case error.UNKNOWN_ERROR:
							frappe.msgprint(__("An unknown error occurred."));
							break;
					}
				}
			);
        } else {
            clearInterval(animationInterval);
            secondChild.style['background-position'] = '0 0';
        }
    });

    controlDiv.index = 1;
    map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(controlDiv);
}



//______________________________________________________________________________________________________________________
//______________________________________________________________________________________________________________________
//______________________________________________________________________________________________________________________
//______________________________________________________________________________________________________________________




function check_existing(page){
	frappe.xcall('one_fm.one_fm.page.face_recognition.face_recognition.check_existing')
	.then(r =>{
		if (!r.exc) {
			// code snippet
			if(r && page.enrolled){
				$('#endButton').show();
				$('#hourlyButton').show();
				$('#enrollButton').hide();
				$('#startButton').hide();
			}
			else{
				$('#endButton').hide();
				$('#hourlyButton').show();
				$('#enrollButton').hide();
				$('#startButton').show();
			}
		}
	})
}

function send_log(log_type, skip_attendance){
    $('.verification').show();
    $('.enrollment').hide();
    countdown();		
    navigator.mediaDevices.getUserMedia({
        video: {
            width: { ideal: 1024 },
            height: { ideal: 768 },
            frameRate: {ideal: 5, max: 10},
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
        console.log(recordedBlob, skip_attendance);
        upload_file(recordedBlob, 'verify', log_type, skip_attendance);
    })
}

function upload_file(file, method, log_type, skip_attendance){
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
        if(method == 'verify'){
            let {timestamp} = cur_page.page.page.position;
            let {latitude, longitude} = cur_page.page.page.position.coords;
            form_data.append("latitude", latitude);
            form_data.append("longitude", longitude);
            form_data.append("timestamp", timestamp);
            form_data.append("log_type", log_type);
            form_data.append("skip_attendance", skip_attendance);
        }
		xhr.onreadystatechange = () => {
			if (xhr.readyState == XMLHttpRequest.DONE) {
			  	$('#cover-spin').hide();
			  	if (xhr.status === 200) {
				let r = null;
				try {
					r = JSON.parse(xhr.responseText);
					console.log(r);
					frappe.msgprint(__(r.message), __("Successful"));
					window.location.reload();
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
    let file = new File([blob], 'recording');

	const reader = new FileReader();
	reader.addEventListener('loadend', () => {
		console.log(reader);
	   // reader.result contains the contents of blob as a typed array
	});
	reader.readAsArrayBuffer(blob);
	const fileurl = URL.createObjectURL(blob);
    let form = new FormData();
    form.append('video', file);
    
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
		$("#cues").empty().append(`<div class="alert alert-info"> <span class="cues"> ${__('Look Straight at the camera.')} <span class="countdown">${__(timeleft - 10)}</span><span></div>`);
	} else if(timeleft <= 10 && timeleft > 5) {
		$("#cues").empty().append(`<div class="alert alert-info"><i class="fa fa-arrow-left fa-icon"></i> <span class="cues"> ${__('Turn your face left slowly and return to straight position.')} <span class="countdown">${__(timeleft - 5)}</span></span></div>`);
	} else if(timeleft <= 5) {
		$("#cues").empty().append(`<div class="alert alert-info"><i class="fa fa-arrow-right fa-icon"></i> <span class="cues"> ${__('Turn your face right slowly and return to straight position.')} <span class="countdown">${__(timeleft)}</span></span></div>`);
	} 
	timeleft -= 1;
	}, 1000);	
}

function make_support_issue(){
	let user = frappe.session.user;
	let {latitude, longitude} = cur_page.page.page.position.coords;
	let loc = `${latitude},${longitude}`;
    frappe.call('one_fm.api.doc_methods.notification_log.make_support_issue', {user, loc});
	frappe.msgprint(__("Please inform your in-line supervisor in person or via direct call about the issue and confirm attendance/exit."))
}   