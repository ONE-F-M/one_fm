def get_location_custom_fields():
    return {
        "Location": [
            {
                "fieldname": "map_html",
                "fieldtype": "HTML",
                "insert_after": "sb_geolocation",
                "label": "map html"
            },
            {
                "fieldname": "geofence_radius",
                "fieldtype": "Int",
                "insert_after": "cb_latlong",
                "label": "Geofence Radius",
                "description": "(In metres)",
                "reqd": 1
            },
            {
                "fieldname": "section_break_15",
                "fieldtype": "Section Break",
                "insert_after": "location"
            },
            {
                "fieldname": "project",
                "fieldtype": "Link",
                "insert_after": "cb_details",
                "label": "Project",
                "options": "Project"
            },
            {
                "fieldname": "governorate_area",
                "fieldtype": "Link",
                "insert_after": "area",
                "label": "Governorate Area",
                "options": "Governorate Area"
            }
        ]
    }
