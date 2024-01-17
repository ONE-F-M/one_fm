# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe, os, json
from frappe.utils import get_datetime
from frappe.model.document import Document
from semantic_version import Version
from frappe.utils.change_log import get_versions
import datetime


def load_versions(change_log_folder,folder,app,args):
    def append_to_iter(frappe_dict):
        version_data.append(frappe_dict)

    version_data =[]
    for file in os.listdir(os.path.join(change_log_folder, folder)):
        file_path = os.path.join(change_log_folder, folder, file)
        content = frappe.read_file(file_path)
        version = Version(os.path.splitext(file)[0][1:].replace("_", "."))
        version_str = os.path.splitext(file)[0][1:].replace("_", ".")
        file_data = frappe._dict({'name':" ".join([app,version_str]),'version_id':version_str,'application':app,'release_notes':content})
        if args.filters:
            #Filter the results based on filters in args
            for each in args.filters:
                if each[1] in ['application','version_id','name']:
                    if file_data.get(each[1]) in each[3]:
                        creation_datetime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                        append_to_iter(frappe._dict({
                            "name":" ".join([app,version_str]),
                            "owner":"Administrator",
                            "date_time":creation_datetime,
                            "creation":creation_datetime,
                            "modified":creation_datetime,
                            "modified_by":"Administrator",
                            "docstatus":0,
                            "_comment_count":0,
                            "release_notes":content,
                            "version_id":version_str,
                            "application":app.title().replace('_', ' ')
                            }))
                    else:
                        continue
                else:
                    frappe.throw("Invalid Filter Selected")
        else:
            creation_datetime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            append_to_iter(frappe._dict({
                "name":" ".join([app,version_str]),
                "owner":"Administrator",
                "date_time":creation_datetime,
                "creation":creation_datetime,
                "modified":creation_datetime,
                "modified_by":"Administrator",
                "docstatus":0,
                "_comment_count":0,
                "release_notes":content,
                "version_id":version_str,
                "application":app.title().replace('_', ' ')
                }))
    return version_data


@frappe.whitelist()
def fetch_data(args = frappe._dict()):
    """
        Fetch all the release notes in the change log folder of each installed app
        Variables like page length and filters will affect the size of the return set
    """
    app_data = []
    start_version = Version("0.0.1")
    last_known_versions = frappe._dict(
        json.loads(frappe.db.get_value("User", frappe.session.user, "last_known_versions") or "{}")
    )
    if not last_known_versions:
        last_known_versions  = get_versions()
    for each in frappe.get_installed_apps():
        if each in last_known_versions and last_known_versions[each]:
            change_log_folder = os.path.join(frappe.get_app_path(each), "change_log")
            if os.path.exists(change_log_folder):
                app_current_version = Version(last_known_versions[each].get('version'))
                major_version_folders = [f"v{i}" for i in range(start_version.major, app_current_version.major + 1)]
                for folder in os.listdir(change_log_folder):
                    if folder in major_version_folders:
                        app_data+=(load_versions(change_log_folder,folder,each,args))
    sorted_versions = sorted(app_data, key=lambda x: tuple(map(int, x.version_id.split("."))), reverse=True)
    if args.filters:
        for each in args.filters:
            pass
    return sorted_versions

class ApplicationReleaseNotes(Document):

    def on_trash(self):
        frappe.throw("This document cannot be deleted.")

    def get_selected_note(self):
        if not self.name:
            frappe.throw("Error Occured while opening the document")
        data = fetch_data()
        for each  in data:
            if each.name == self.name:

                setattr(self,'_table_fieldnames',[])
                for key,value in each.items():
                    setattr(self,key,value)
                    if key=='release_notes':
                        docfield = self.meta.get_field(key)
                        docfield.options = value


    def db_insert(self, *args, **kwargs):
        pass

    def on_trash(self):
        frappe.throw("This Document cannot be deleted!")

    def load_from_db(self):
        self.get_selected_note()
        pass


    def db_update(self, *args, **kwargs):
        pass


    @staticmethod
    def get_list(args):
        data =  fetch_data(args)
        return data[:int(args.page_length)]

    @staticmethod
    def get_count(args):
        data =  fetch_data(args)
        return len(data)

    @staticmethod
    def get_stats(args):
        pass
