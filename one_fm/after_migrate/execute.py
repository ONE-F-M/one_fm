import frappe, os, shutil, subprocess

from frappe.utils import cstr, get_bench_path
from one_fm.utils import production_domain

def comment_timesheet_in_hrms():
    """
        HRMS overrides Timesheet, this affects restricts the overide in ONE_FM
    """
    app_path = frappe.utils.get_bench_path()+"/apps/hrms/hrms/"
    f = open(app_path+"hooks.py",'r')
    filedata = f.read()
    f.close()

    newdata = ""
    found = False
    if not filedata.find('#"Timesheet": "hrms.overrides.employee_timesheet.EmployeeTimesheet",') > 0:
        newdata = filedata.replace(
            '"Timesheet": "hrms.overrides.employee_timesheet.EmployeeTimesheet",',
            '#"Timesheet": "hrms.overrides.employee_timesheet.EmployeeTimesheet",'
        )
        filedata = newdata
        found = True

    if not filedata.find('#"Employee": "hrms.overrides.employee_master.EmployeeMaster",') > 0:
        newdata = filedata.replace(
            '"Employee": "hrms.overrides.employee_master.EmployeeMaster",',
            '#"Employee": "hrms.overrides.employee_master.EmployeeMaster",',
        )
        found = True

    if found:
        f = open(app_path+"hooks.py",'w')
        f.write(newdata)
        f.close()

    # delete restaurant menu
    custom_fields = [
		{"dt": "Sales Invoice", "fieldname": "restaurant"},
		{"dt": "Sales Invoice", "fieldname": "restaurant_table"},
		{"dt": "Price List", "fieldname": "restaurant_menu"},
	]
    for field in custom_fields:
        try:
            print("Removing ", field, " from custom field")
            custom_field = frappe.db.get_value("Custom Field", field)
            frappe.delete_doc("Custom Field", custom_field, ignore_missing=True)
        except:
            print(field, "Does not exist in custom field")



def comment_payment_entry_in_hrms():
    """
        HRMS overrides Payment Entry, this restricts the overide in ONE_FM
    """

    app_path = frappe.utils.get_bench_path()+"/apps/hrms/hrms/"
    f = open(app_path+"hooks.py",'r')
    filedata = f.read()
    f.close()

    if not filedata.find('#"Payment Entry": "hrms.overrides.employee_payment_entry.EmployeePaymentEntry",') > 0:
        newdata = filedata.replace(
                '"Payment Entry": "hrms.overrides.employee_payment_entry.EmployeePaymentEntry",',
                '#"Payment Entry": "hrms.overrides.employee_payment_entry.EmployeePaymentEntry",'
        )

        f = open(app_path+"hooks.py",'w')
        f.write(newdata)
        f.close()


def replace_send_anniversary_reminder():
    """
        Replace the default email notification for birthdays with a custom function
    """
    app_path = frappe.utils.get_bench_path()+"/apps/hrms/hrms/"
    f = open(app_path+"hooks.py",'r')
    filedata = f.read()
    f.close()

    if  filedata.find('"hrms.controllers.employee_reminders.send_work_anniversary_reminders"') > 0:
        newdata = filedata.replace(
                '"hrms.controllers.employee_reminders.send_work_anniversary_reminders",',
                '#"hrms.controllers.employee_reminders.send_work_anniversary_reminders",'
        )
        f = open(app_path+"hooks.py",'w')
        f.write(newdata)
        f.close()
        
        

def replace_send_birthday_reminder():
    """
        Replace the default email notification for birthdays with a custom function
    """
    app_path = frappe.utils.get_bench_path()+"/apps/hrms/hrms/"
    f = open(app_path+"hooks.py",'r')
    filedata = f.read()
    f.close()

    if  filedata.find('"hrms.controllers.employee_reminders.send_birthday_reminders",') > 0:
        newdata = filedata.replace(
                '"hrms.controllers.employee_reminders.send_birthday_reminders",',
                '#"hrms.controllers.employee_reminders.send_birthday_reminders",'
        )
        f = open(app_path+"hooks.py",'w')
        f.write(newdata)
        f.close()
        
        

def comment_process_expired_allocation_in_hrms():
    """
        Comment hrms scheduler to process_expired_allocation
    """

    app_path = frappe.utils.get_bench_path()+"/apps/hrms/hrms/"
    f = open(app_path+"hooks.py",'r')
    filedata = f.read()
    f.close()

    if not filedata.find('#"hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry.process_expired_allocation",') > 0:
        newdata = filedata.replace(
                '"hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry.process_expired_allocation",',
                '#"hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry.process_expired_allocation",'
        )

        f = open(app_path+"hooks.py",'w')
        f.write(newdata)
        f.close()



def disable_workflow_emails():
    """
        This disables workflow emails on workflow doctype if not on production server.
    """
    if not production_domain():
        # Disable Work Contract
        doctypes = ['Contracts']
        print("Disabling workflow email for:")
        for i in doctypes:
            print(i)
            try:
                frappe.db.set_value('Workflow', 'Contracts', 'send_email_alert', 0)
            except Exception as e:
                print(str(e))
        frappe.db.commit()

def before_migrate():
    """
        Things to do before migrate
    """
    print("Removing column_break_20 from Salary Structure Assignment in Custom Field.")
    frappe.db.sql("""
        DELETE FROM `tabCustom Field` WHERE name='Salary Structure Assignment-column_break_20'
    """)

def set_files_directories():
    """
        Set files and directories if not exists
    """
    user_files_path = frappe.utils.get_bench_path()+'/sites/'+frappe.utils.get_site_base_path().replace('./', '')+'/private/files/user'
    if not os.path.exists(user_files_path):
        os.mkdir(user_files_path)

def replace_job_opening():
    """
        Replace job opening in HRMS
    """
    print("Replacing job_opening.html")
    app_path = frappe.utils.get_bench_path()+"/apps/hrms/hrms/templates/generators"
    os.remove(app_path+'/job_opening.html')
    shutil.copy(frappe.utils.get_bench_path()+"/apps/one_fm/one_fm/templates/generators/job_opening.html", app_path+'/job_opening.html')
    bench_path = frappe.utils.get_bench_path()+'/sites/'+cstr(frappe.local.site)+'/'
    private = "private/"
    public = "public/"
    user_files_path = "private/files/user"
    user_magic_link = "private/files/user/magic_link"
    user_files_path = "public/files/user"
    user_magic_link = "public/files/user/magic_link"
    for i in [user_files_path, user_magic_link]:
        if not os.path.exists(bench_path+i):
            os.mkdir(bench_path+i)


def replace_prompt_message_in_goal():
    """
    Replace the prompt message that pop us while changing the KRA of a parent goal
    """
    doctype_path = frappe.utils.get_bench_path() + "/apps/hrms/hrms/hr/doctype/goal/"
    file_path = os.path.join(doctype_path, "goal.js")

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            filedata = f.read()

        if not filedata.find("Modifying the KRA in the parent goal will specifically impact those child goals that share the same KRA; any other child goals with different KRAs will remain unaffected.") > 0:
            newdata = filedata.replace(
                "Changing KRA in this parent goal will align all the child goals to the same KRA, if any.",
                "Modifying the KRA in the parent goal will specifically impact those child goals that share the same KRA; any other child goals with different KRAs will remain unaffected."
            )

            with open(file_path, 'w') as f:
                f.write(newdata)


def append_code_in_file(file_path, search_text, appendable_code, insert_before_search_text = False, replace_with_search_text = False):
    try:
        # Read the file contents
        with open(file_path, 'r') as file:
            lines = file.read()
            #  check for existing code
            if (appendable_code in lines):
                print("Code exists")
                return False

        if replace_with_search_text:
            with open(file_path, 'r') as file:
                lines = file.read()
                if search_text in lines:
                    lines = lines.replace(search_text, appendable_code)
            with open(file_path, 'w') as file_write:
                file_write.write(lines)
                return True
        else:
            # Read the file contents
            with open(file_path, 'r') as file:
                lines = file.readlines()

            # Create a flag to track if the line was found and new code was appended
            line_found = False

            # Open the file again in write mode to overwrite the contents
            with open(file_path, 'w') as file:
                for line in lines:
                    if insert_before_search_text:
                        # If the current line matches the search line, append the new code before it
                        if line.strip() == search_text:
                            file.write(appendable_code + '\n')
                            line_found = True
                        # Write the current line to the file
                        file.write(line)
                    else:
                        # Write the current line to the file
                        file.write(line)
                        # If the current line matches the search line, append the new lines after it
                        if line.strip() == search_text:
                            file.write(appendable_code + '\n')
                            line_found = True

            # Check if the line was found and new code was appended
            if line_found:
                print(f"The new code was successfully appended {'before' if insert_before_search_text else 'after'} '{search_text}'.")
                return True
            else:
                print(f"The line '{search_text}' was not found in the file.")
                return False
    except FileNotFoundError:
        print(f"The file '{file_path}' does not exist.")
        return False
    except Exception as e:
        print(f"An error occurred: {e} try", frappe.get_traceback())
        return False

def update_hd_ticket_agent():
    FILE_PATH = frappe.utils.get_bench_path()+'/apps/helpdesk/desk/src/pages/ticket/TicketAgent.vue'
    if (os.path.exists(FILE_PATH)):
        # Append lines before 'const showSubjectDialog = ref(false);'
        search_text = 'const showSubjectDialog = ref(false);'
        appendable_code = '''
            const showCreateStoryConfirmationDialog = ref(false);
            const showStoryCreationProgressDialog = ref(false);
        '''
        first_change = append_code_in_file(FILE_PATH, search_text, appendable_code, False)

        # Append code before 'const ticket = createResource({'
        search_text = 'const ticket = createResource({'
        appendable_code = '''
        const createDevTicket = () => {
        
            showCreateStoryConfirmationDialog.value = false;
            showStoryCreationProgressDialog.value = true;

            if (!ticket.data.custom_dev_ticket || true) {
                createResource({
                url: "one_fm.overrides.hd_ticket.create_dev_ticket",
                auto: true,
                params: {
                    name: ticket.data.name,
                    description: ticket.data.description,
                },
                transform: (data) => {},
                onSuccess: (data) => {
                    showStoryCreationProgressDialog.value = false;
                    if (data.error){
                    toast.error(data.message || "Something went wrong in creating dev ticket")
                  } else if (data.status == 'success' ) {

                    toast.success("Dev ticket created successfully")

                  }
                    ticket.reload();
                },
                onError: (error) => {
                    showStoryCreationProgressDialog.value = false;
                    toast.error(error.message || "Something went wrong in creating dev ticket")
                },
                });
            }
        };

        const viewDevTicket = () => {
            if (ticket.data.custom_dev_ticket) {
                window.open(ticket.data.custom_dev_ticket, "_blank");
            }
        };\n\n
        '''
        second_change = append_code_in_file(FILE_PATH, search_text, appendable_code, insert_before_search_text=True)


        # Append Template code for button and modal
        search_text = '''    <CustomActions
          v-if="ticket.data._customActions"
          :actions="ticket.data._customActions"
        />'''
        appendable_code = '''    <CustomActions
          v-if="ticket.data._customActions"
          :actions="ticket.data._customActions"
        />
            <div v-if="['Open', 'Replied'].includes(ticket.data.status)">
                <Button @click="viewDevTicket" v-if="ticket.data.custom_dev_ticket">
                    View Dev Ticket
                </Button>
                <Button @click="showCreateStoryConfirmationDialog = true"  v-if="!ticket.data.custom_dev_ticket">
                    Create Dev Ticket
                </Button>
                <Dialog v-model="showCreateStoryConfirmationDialog">
                    <template #body-title>
                    <h3>Create Dev Ticket</h3>
                    </template>
                    <template #body-content>
                    <p>By clicking on "Confirm", a dev ticket will be created</p>
                    </template>
                    <template #actions>
                    <Button variant="solid"
                    @click="createDevTicket">
                        Confirm
                    </Button>
                    <Button
                        class="ml-2"
                        @click="showCreateStoryConfirmationDialog = false;"
                    >
                        Close
                    </Button>
                    </template>
                </Dialog>
                
                <Dialog v-model="showStoryCreationProgressDialog">
                    <template #body-title>
                    <h3>Please Wait</h3>
                    </template>
                    <template #body-content>
                    <p>Please hold while we are creating dev ticket</p>
                    </template>
                    <template #actions>
                    <Button
                        class="ml-2"
                        @click="showStoryCreationProgressDialog = false"
                    >
                        Close
                    </Button>
                    </template>
                </Dialog>
            </div>

        '''
        third_change = append_code_in_file(FILE_PATH, search_text, appendable_code, insert_before_search_text=True, replace_with_search_text=True)
        search_text = "subjectInput.value = data.subject;"
        appendable_code = """
                                    setTimeout(()=>{
                        if((data.communications.length) && communicationAreaRef.value!=null){
                            
                            let last_index = data.communications.length - 1
                            let last_content = data.communications[last_index].content
                            
                            communicationAreaRef.value.$refs.emailEditorRef.addToReply(last_content,[data.raised_by])
                            
                        }
                        else if(communicationAreaRef.value==null){
                            
                            
                            let last_index = data.communications.length - 1
                            let last_content = data.communications[last_index].content
                            localStorage.setItem('emailBoxContent',last_content)
                            
                        }

                        }, 1000);
                    """
        fourth_change = append_code_in_file(FILE_PATH, search_text, appendable_code, False)
        if (first_change or second_change or third_change or fourth_change):
            return True
    else:
        print(FILE_PATH, 'not found')
    return



def add_resolution_details_updation():
    FILE_PATH = frappe.utils.get_bench_path()+'/apps/helpdesk/desk/src/pages/ticket/TicketAgent.vue'
    if (os.path.exists(FILE_PATH)):
        # Append lines before '} from "frappe-ui";' to import TextEditor
        search_text = '} from "frappe-ui";'
        appendable_code = '''TextEditor'''
        first_change = append_code_in_file(FILE_PATH, search_text, appendable_code, insert_before_search_text=True)

        # Append code before 'const ticket = createResource({'
        search_text = 'const showSubjectDialog = ref(false);'
        appendable_code = '''
            \n\nconst showResolutionDialog = ref(false);
            const resolutionDetails = ref('');

            const submitResolution = () => {
                updateTicket('resolution_details', resolutionDetails.value);
                showResolutionDialog.value = false
            };\n\n
        '''
        second_change = append_code_in_file(FILE_PATH, search_text, appendable_code)

        # Append Template code for button and modal
        search_text = '''    <CustomActions
          v-if="ticket.data._customActions"
          :actions="ticket.data._customActions"
        />'''
        appendable_code = '''
            <CustomActions
                v-if="ticket.data._customActions"
                :actions="ticket.data._customActions"
                />
            <div v-if="!['Closed', 'Resolved'].includes(ticket.data.status)">
                <Button @click="showResolutionDialog = true">
                    Update Resolution Details
                </Button>
                <Dialog v-model="showResolutionDialog">
                    <template #body-title>
                    <h3>Update Resolution Details</h3>
                    </template>

                    <template #body-content>
                    <div class="mb-1.5 text-sm text-gray-600">Resolution Details</div>
                    <TextEditor ref="content" variant="outline"
                        editor-class="!prose-sm overflow-auto min-h-[180px] max-h-80 py-1.5 px-2 rounded border border-gray-300 bg-white hover:border-gray-400 hover:shadow-sm focus:bg-white focus:border-gray-500 focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-gray-400 text-gray-800 transition-colors"
                        :bubble-menu="true" :content="resolutionDetails" :placeholder="'Add resolution details here...'" :disabled="isLoading"
                        @change="(val) => (resolutionDetails = val)" />
                    </template>

                    <template #actions>
                    <Button variant="solid" :loading="isLoading" :disabled="!resolutionDetails"
                        @click="submitResolution">
                        Submit
                    </Button>
                    <Button class="ml-2" @click="showResolutionDialog = false">Cancel</Button>
                    </template>
                </Dialog>
            </div>
        '''
        third_change = append_code_in_file(FILE_PATH, search_text, appendable_code, replace_with_search_text=True)

        # Append predefined value for resolution details
        search_text = 'subjectInput.value = data.subject;'
        appendable_code = 'resolutionDetails.value = data.resolution_details'
        fourth_change = append_code_in_file(FILE_PATH, search_text, appendable_code)

        if (first_change or second_change or third_change or fourth_change):
            return True
    else:
        print(FILE_PATH, 'not found')
    return


def run_command(command, cwd=None, shell=True):
    try:
        result = subprocess.run(command, cwd=cwd, shell=shell, check=True, text=True, capture_output=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running the command: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")



def deploy_ticket_views():
    bench_path = get_bench_path()

    ticket_target_folder = os.path.join(bench_path, "apps", "helpdesk", "desk", "src", "pages", "ticket")

    ticket_edit_source = os.path.join(bench_path, "apps", "one_fm", "one_fm", "public", "js", "form_overrides", "hd_ticket", "TicketEdit.vue")
    ticket_edit_target = os.path.join(ticket_target_folder, "TicketEdit.vue")

    if not os.path.exists(ticket_edit_source):
        print(f"[❌] Source TicketEdit.vue not found: {ticket_edit_source}")
        return False

    shutil.copy2(ticket_edit_source, ticket_edit_target)
    print(f"[✅] TicketEdit.vue deployed to: {ticket_edit_target}")

    ticket_customer_source = os.path.join(bench_path, "apps", "one_fm", "one_fm", "public", "js", "form_overrides", "hd_ticket", "TicketCustomer.vue")
    ticket_customer_target = os.path.join(ticket_target_folder, "TicketCustomer.vue")

    if not os.path.exists(ticket_customer_source):
        print(f"[❌] Source TicketCustomer.vue not found: {ticket_customer_source}")
        return False

    shutil.copy2(ticket_customer_source, ticket_customer_target)
    print(f"[✅] TicketCustomer.vue deployed to: {ticket_customer_target}")


    router_file = os.path.join(bench_path, "apps", "helpdesk", "desk", "src", "router", "index.ts")

    if not os.path.exists(router_file):
        print("❌ Router file not found:", router_file)
        return False

    with open(router_file, "r") as f:
        router_content = f.read()

    if 'name: "TicketEdit"' in router_content:
        print("⚠️ TicketEdit route already exists.")
    else:
        search_text = "const routes = ["
        appendable_code = '''
  {
    path: "/edit-ticket/:ticket_name?",
    name: "TicketEdit",
    component: () => import("@/pages/ticket/TicketEdit.vue"),
    props: true,
    meta: {
      onSuccessRoute: "TicketCustomer",
      parent: "TicketsCustomer",
    },
  },'''

        updated_content = ""
        if search_text in router_content:
            parts = router_content.split(search_text)
            updated_content = parts[0] + search_text + appendable_code + parts[1]

            with open(router_file, "w") as f:
                f.write(updated_content)

            print("✅ TicketEdit route added.")
        else:
            print("⚠️ Could not find insertion point for router update.")
            return False

    print("[🎉] TicketEdit and TicketCustomer views deployed successfully.")
    return True

def update_hd_ticket_side_bar():
    FILE_PATH = frappe.utils.get_bench_path()+'/apps/helpdesk/desk/src/components/ticket/TicketAgentFields.vue'
    if (os.path.exists(FILE_PATH)):
        # Replace lines 'agent_group'
        
        search_pattern = r"""
            \s*{                         
            \s*field:\s*"priority",     
            \s*label:\s*"Priority",     
            \s*store:\s*useTicketPriorityStore\(\), 
            \s*},                       
            \s*{                         
            \s*field:\s*"agent_group",  
            \s*label:\s*"Team",         
            \s*store:\s*useTeamStore\(\), 
            \s*},                       
        """
        
        fourth_change = remove_code_block_with_regex(FILE_PATH, search_pattern)
        if fourth_change:
            return True
    else:
        print(FILE_PATH, 'not found')
    return


def remove_code_block_with_regex(file_path, pattern):
    import re
    try:
        with open(file_path, 'r') as file:
            content = file.read()

        # Check if the pattern exists
        if not re.search(pattern, content, flags=re.MULTILINE | re.VERBOSE):
            print("Pattern not found in file.")
            return False

        # Remove the block
        updated_content = re.sub(pattern, '', content, flags=re.MULTILINE | re.VERBOSE)

        with open(file_path, 'w') as file:
            file.write(updated_content)

        print("Pattern removed successfully.")
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def update_all_ticket_features():
    any_changes = False

    if update_hd_ticket_agent():
        any_changes = True
    if add_resolution_details_updation():
        any_changes = True
    if deploy_ticket_views():
        any_changes = True
    if update_hd_ticket_side_bar():
        any_changes = True
    if update_ticket_status():
        any_changes = True

    if any_changes:
        bench_path = frappe.utils.get_bench_path()
        helpdesk_dir = os.path.join(bench_path, 'apps/helpdesk/desk')

        run_command("NODE_OPTIONS=\"--max-old-space-size=4096\" yarn build", cwd=helpdesk_dir)
        run_command("bench restart", cwd=bench_path)
    else:
        print("No changes detected. Skipping build and restart.")

def disable_email_and_sync_on_developer_mode():
    if not frappe.conf.get("developer_mode"):
        return
    disable_email_accounts_on_developer_mode()
    disable_sync_on_developer_mode()

def disable_email_accounts_on_developer_mode():
    if not frappe.conf.get("developer_mode"):
        return
    email_accounts = frappe.get_all("Email Account", pluck="name")
    for account in email_accounts:
        frappe.db.set_value(
            "Email Account",
            account,
            {
                "enable_outgoing": 0,
                "default_outgoing": 0,
                "enable_incoming": 0,
                "default_incoming": 0
            }
        )
        print(f"Disabled Email Account: {account}")
    print("All Email Accounts have been disabled.")

def disable_sync_on_developer_mode():
    if not frappe.conf.get("developer_mode"):
        return
    sync_ = frappe.db.get_single_value("ONEFM General Setting", "google_task_synchronization_enabled")
    if sync_:
        frappe.db.set_single_value(
            "ONEFM General Setting",
            "google_task_synchronization_enabled",
            0
        )
        print(f"Disabled Google Task Synchronization")


def update_ticket_status():
    """
    Replaces the standard Helpdesk ticketStatus.ts file with the custom version from one_fm
    and triggers a build to apply the changes.
    """
    print("🚀 Overriding Helpdesk ticketStatus.ts file...")

    # Get the base path of the bench directory
    bench_path = frappe.utils.get_bench_path()

    # Define the source and destination file paths
    source_file = os.path.join(
        bench_path, "apps", "helpdesk", "desk", "src", "stores", "ticketStatus.ts"
    )
    replacement_file = os.path.join(
        bench_path, "apps", "one_fm", "one_fm", "public", "js", "form_overrides", "hd_ticket", "ticketStatus.ts"
    )

    # Ensure the custom replacement file actually exists before proceeding
    if not os.path.exists(replacement_file):
        print(f"❌ Error: Replacement file not found at: {replacement_file}")
        return False

    try:
        # Copy the content from your custom file to the source file, overwriting it
        print(f"📄 Copying from {replacement_file} to {source_file}")
        shutil.copy2(replacement_file, source_file)
        print("✅ Successfully replaced ticketStatus.ts.")
        
        return True

    except FileNotFoundError:
        print(f"⚠️ Warning: Original file not found at: {source_file}. Skipping replacement.")
    except Exception as e:
        print(f"🔥 An unexpected error occurred: {e}")
        frappe.log_error("ONEFM TicketStatus.ts Override Failed", frappe.get_traceback())

    return False
