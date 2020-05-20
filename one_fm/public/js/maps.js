frappe.call('frappe.client.get_value', {
    doctype: "Google Settings", 
    fieldname: "api_key"
})
.then(res => {
    if(!res.exc){
        let {api_key} = res.message;
        var script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${api_key}`;
        script.defer = true;
        script.async = true;
    
        // Attach your callback function to the `window` object
        window.initMap = function() {
        // JS API is loaded and available
        };
    
        // Append the 'script' element to 'head'
        document.head.appendChild(script);         
    }
});