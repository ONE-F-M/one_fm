frappe.ui.form.on('Location',{
    onload_post_render: function(frm){
        $('[data-fieldname="map_html"]').append(`<div style='width:100%; height:500px' id='map'></div>`);
        let {latitude, longitude}= frm.doc;
        window.markers = [];
        window.circles = [];
        // JS API is loaded and available
        console.log("Called")
        window.map = new google.maps.Map(document.getElementById('map'), {
            center: {lat: 29.338394, lng: 48.005958},
            zoom: 17
        });
        loadGoogleMap(frm);

        // Configure the click listener.
        map.addListener('click', function(mapsMouseEvent) {
          clearMarkers();
          clearCircles();
          console.log(mapsMouseEvent.latLng);
          frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'latitude', mapsMouseEvent.latLng.lat());
          frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'longitude',mapsMouseEvent.latLng.lng());
        });

    },
    latitude: function(frm){
        loadGoogleMap(frm);
    },
    longitude: function(frm){
        loadGoogleMap(frm);
    },
    geofence_radius: function(frm){
        clearCircles();
        loadGoogleMap(frm);    
    }
})

function loadGoogleMap(frm){
    let lat = frm.doc.latitude === 19.0800 ? 29.338394 : frm.doc.latitude;
    let lng = frm.doc.longitude === 72.8961 ? 48.005958 : frm.doc.longitude;
    let radius = frm.doc.geofence_radius;
    console.log(lat, lng, radius);
    if(lat !== undefined && lng !== undefined){
        let marker = new google.maps.Marker({
            position: {lat, lng},
            map: map,
            title: frm.doc.location_name
        });
        marker.setMap(map);
        map.setCenter({lat, lng});
        markers.push(marker);

        if(radius){
            let geofence_circle = new google.maps.Circle({
                strokeColor: '#FF0000',
                strokeOpacity: 0.8,
                strokeWeight: 2,
                fillColor: '#FF0000',
                fillOpacity: 0.35,
                map: map,
                center: {lat, lng},
                radius: radius
            });
            circles.push(geofence_circle);
        }
    }
} 

function clearMarkers(){
    for (var i = 0; i < markers.length; i++) {
        markers[i].setMap(null);
      }
}
function clearCircles(){
    for (var i = 0; i < circles.length; i++) {
        circles[i].setMap(null);
      }
}