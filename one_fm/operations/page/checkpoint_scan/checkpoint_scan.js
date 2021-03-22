frappe.pages['checkpoint-scan'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'SCAN CHECKPOINT',
		single_column: true
	});
	$(wrapper).find('.layout-main-section').empty().append(frappe.render_template('checkpoint_scan'));
	//Get/set current user location
	get_location(page);
	
	//Initialize qrcode
	const html5QrCode = new Html5Qrcode("reader");
	const config = { fps: 10 };
	page.qr_code = html5QrCode;
	

	//Start scanning on clicking button
	$('#scan').on('click', function(){
		// If you want to prefer back camera
		html5QrCode.start({ facingMode: "environment" }, config, onScanSuccess);
	})	
}


function onScanSuccess(qrMessage) {
	// handle the scanned code as you like
	console.log(`QR matched = ${qrMessage}`);
	let {latitude, longitude} = cur_page.page.page.position.coords;
	let qr_code = qrMessage;
	//Stop scanning
	cur_page.page.page.qr_code.stop();
	
	frappe.xcall('one_fm.operations.page.checkpoint_scan.checkpoint_scan.scan_checkpoint', {qr_code, latitude, longitude})
	.then(res => {
		frappe.msgprint(__("Done!"));
	})

}

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
