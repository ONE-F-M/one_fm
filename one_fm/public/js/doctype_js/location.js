frappe.ui.form.on('Location',{
    onload_post_render: function(frm){
        $('[data-fieldname="map_html"]').append(`<div style='width:100%; height:300px' id='map'></div>`);

        // JS API is loaded and available
        window.map = new google.maps.Map(document.getElementById('map'), {
            center: {lat: 29.338392, lng: 48.005867},
            zoom: 17
        });
        if(frm.doc.__islocal === 1){
            let marker = new google.maps.Marker({
                position: {lat: 29.338392, lng: 48.005867},
                map: map,
                title: 'Armor Services'
            });
        }else{
            loadGoogleMap(frm);
        }
    },
    latitude: function(frm){
        loadGoogleMap(frm);
    },
    longitude: function(frm){
        loadGoogleMap(frm);
    }
})

function loadGoogleMap(frm){
    let lat = frm.doc.latitude;
    let lng = frm.doc.longitude;
    if(lat !== undefined && lng !== undefined){
        let marker = new google.maps.Marker({
            position: {lat, lng},
            map: map,
            title: frm.doc.location_name
        });
        marker.setMap(map);
        map.setCenter({lat, lng});            
    }
} 