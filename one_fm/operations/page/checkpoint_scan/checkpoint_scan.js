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
		navigator.geolocation.getCurrentPosition(
            position => {
				page.position = position;
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