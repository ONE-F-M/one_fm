def get_google_settings_custom_fields():
    """Where the Proof of Work export delivers (WI-001981).

    On Google Settings because that is where the work item puts it, and because a
    Drive folder is a Google setting - even though the upload authenticates with the
    service account JSON held on ONEFM General Setting rather than with the OAuth
    client this page configures.
    """
    return {
        "Google Settings": [
            {
                "fieldname": "pow_drive_section",
                "fieldtype": "Section Break",
                "insert_after": "google_drive_picker_enabled",
                "label": "Proof of Work",
            },
            {
                "fieldname": "pow_drive_folder_link",
                "fieldtype": "Data",
                "insert_after": "pow_drive_section",
                "label": "Proof of Work Drive Folder",
                "description": (
                    "Shared Drive folder the Proof of Work export uploads into, as a share "
                    "link or a folder id. The folder must be shared with the service account "
                    "configured under ONEFM General Setting. Leave empty to keep downloading "
                    "a ZIP instead."
                ),
            },
        ]
    }
