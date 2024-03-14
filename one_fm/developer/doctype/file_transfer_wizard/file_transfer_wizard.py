# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt

import frappe,socket,paramiko
from frappe.model.document import Document
from frappe.integrations.offsite_backup_utils import get_latest_backup_file


class FileTransferWizard(Document):
    def validate(self):
        self.set_ip_address()
        self.validate_folder_location()
        
        
    @frappe.whitelist()
    def initiate_transfers(self):
        frappe.enqueue(self.transfer_files, timeout=1200)
        
        
    
    def transfer_files(self):
        try:
            self.get_connection()
            # self.sftp_client.put
            last_backups = self.get_last_backups()
            if last_backups.get('db'): #ensure that a database backup is available before proceeding
                for one in last_backups.keys():
                    if last_backups.get(one):
                        old_update = self.updates or ""
                        file_name = last_backups.get(one).split('/')[-1]
                        self.db_set('updates',old_update+f"<br/> Uploading {file_name}......")
                        self.sftp_client.put(last_backups.get(one),self.directory+'/'+file_name)
                        self.db_set('updates',old_update+f"<br/> Uploaded {file_name}")
        except Exception as e:
            frappe.log_error(title = "Error Uploading File",message = frappe.get_traceback())
            
    
    
    def get_connection(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Handle unknown host keys (carefully!)
            self.client.connect(hostname=self.ip_address, username=self.username,password = self.get_password('password'),allow_agent=False, look_for_keys=False)
            self.sftp_client = self.client.open_sftp()
        except paramiko.AuthenticationException:
            frappe.throw("Invalid Credentials! <br> Please review the username and password provided")
        except Exception as e:
            frappe.log_error(title = "Error accessing server",message = frappe.get_traceback())
        

    def validate_folder_location(self):
        """ Ensure that the credentials provided to access the server are correct
        """
        try:
            self.get_connection()
            try:
                self.sftp_client.stat(self.directory)
                
            except FileNotFoundError:
                if self.create_directory_if_missing:
                    self.sftp_client.mkdir(self.directory)
                    self.db_set('transfer_status',"Ready")
                    frappe.db.commit()
                else:
                    self.db_set('transfer_status',"Pending")
                    frappe.db.commit()
                    frappe.throw(f"Folder path {self.directory} not found")
                self.client.close()
                self.sftp_client.close()
            self.client.close()
            self.sftp_client.close()
            self.db_set('transfer_status',"Ready")
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(title = "Error Validating Folder Location",message = frappe.get_traceback())
            
            

    
    
    def get_last_backups(self):
        db_filename, site_config, files_filename, private_files = None,None,None,None
        if self.transfer_public_and_private_files:
            db_filename, site_config, files_filename, private_files = get_latest_backup_file(with_files=1)
        else:
            db_filename, site_config = get_latest_backup_file()
            
        return {'db':db_filename,'site_config':site_config,'files_filename':files_filename,'private_files':private_files}
    
    def set_ip_address(self):
        """
            Set  the IP address if URL is set
        """
        try:
            if self.fetch_ip_from_url:
                url = self.url.split('//')[-1] #get the last item in the list
                ip_address = socket.gethostbyname(url)
                if ip_address != self.ip_address:
                    self.ip_address = ip_address
        except socket.error as e:
    
            frappe.log_error(title = "Error Fetching IP Address",message = e.strerror)
            
            frappe.throw("An error occured while fetching the IP address")


