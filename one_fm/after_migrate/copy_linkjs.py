import os, frappe, shutil
from frappe.utils import get_bench_path, get_backups_path

def execute():
    frappe_link_path = get_bench_path()+'/apps/frappe/frappe/public/js/frappe/form/controls'
    onefm_link_path = get_bench_path()+'/apps/one_fm/one_fm/public/js/frappe/form/controls'
    print("Copying", onefm_link_path, " to", frappe_link_path)
    try:
        os.remove(frappe_link_path+"/link.js")
    except:
        pass
    shutil.copy2(onefm_link_path+"/link.js", frappe_link_path)