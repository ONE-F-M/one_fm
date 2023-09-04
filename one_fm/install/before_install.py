import frappe, requests, os

from one_fm.hooks import required_apps


def execute():
    install_face_predictor()
    install_required_apps()

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
    
            
def install_required_apps():
    installed_apps = frappe.get_all_apps()
    
    if required_apps:
        for app in required_apps:
            if app not in installed_apps:
                installed_apps.append(app)
                
        frappe.local.flags.in_install = True
        frappe.flags.all_apps = installed_apps