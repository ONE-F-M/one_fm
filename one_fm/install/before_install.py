import frappe, requests, os


def execute():
    sync_custom_fields()
    install_face_predictor()

def sync_custom_fields():
    """Create custom fields before DocType sync to avoid 'Unknown column' errors.

    During app installation, sync_for() runs before after_install(). If any
    DocType module references a custom field at import time (e.g. class-level
    DB queries), the column must already exist in the database. This function
    ensures all custom fields are created early in the before_install hook.
    """
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    from one_fm.setup.custom_field import get_custom_fields
    create_custom_fields(get_custom_fields(), ignore_validate=True)

def install_face_predictor():
    # download facial predictor
    path =  f"{frappe.get_site_path()}/private/files/"
    filename = "shape_predictor_68_face_landmarks.dat"
    url = 'https://github.com/italojs/facial-landmarks-recognition/raw/master/shape_predictor_68_face_landmarks.dat'
    print("Checking if Landmark facial recogintion exists...", path)
    if(os.path.exists(path+filename)):
        print("Facial recognition found!.")
    else:
        print('Downloading Landmark facial recognition')
        r = requests.get(url, stream=True)
        if r.ok:
            print("saving 'Landmark facial recognition to' ", path)
            with open(f"{path}{filename}", 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 8):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        os.fsync(f.fileno())
        else:  # HTTP status code 4XX/5XX
            print("Download failed: status code {}\n{}".format(r.status_code, r.text))

    