import frappe, os, shutil, subprocess
from frappe.utils import cstr
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


"""
The below code updates HRMS Ticket detail to
1. Add a new button for creating Pivotal tracker ticket 
"""
def append_line_after_in_ticketagent(file_path, search_line, new_code):
    try:
        # Read the file contents
        code_lines = '\n'.join(new_code) + '\n'
        with open(file_path, 'r') as file:
            lines = file.read()
            #  check for existing code
            if (code_lines in lines):
                print("Code exists")
                return False

        with open(file_path, 'r') as file:
            lines = file.readlines()
            
        
        # Create a flag to track if the line was found and new lines were appended
        line_found = False
        
        # Open the file again in write mode to overwrite the contents
        with open(file_path, 'w') as file:
            for line in lines:
                # Write the current line to the file
                file.write(line)
                # If the current line matches the search line, append the new lines after it
                if line.strip() == search_line:
                    file.write(code_lines)
                    line_found = True
        
        # Check if the line was found and new lines were appended
        if line_found:
            print(f"The lines were successfully appended after '{search_line}'.")
            return True
        else:
            print(f"The line '{search_line}' was not found in the file.")
            return False
    except FileNotFoundError:
        print(f"The file '{file_path}' does not exist.")
        return False
    except Exception as e:
        print(f"An error occurred: {e} try", frappe.get_traceback())
        return False

def append_code_before_in_ticketagent(file_path, search_line, new_code, replacement=None):
    try:
        # Read the file contents
        with open(file_path, 'r') as file:
            lines = file.read()
            #  check for existing code
            if (new_code in lines):
                print("Code exists")
                return False
            
        if replacement:
            with open(file_path, 'r') as file:
                lines = file.read()
                if search_line in lines:
                    lines = lines.replace(search_line, new_code)
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
                    # If the current line matches the search line, append the new code before it
                    if line.strip() == search_line:
                        file.write(new_code + '\n')
                        line_found = True
                    # Write the current line to the file
                    file.write(line)
            
            # Check if the line was found and new code was appended
            if line_found:
                print(f"The new code was successfully appended before '{search_line}'.")
                return True
            else:
                print(f"The line '{search_line}' was not found in the file.")
                return False
    except FileNotFoundError:
        print(f"The file '{file_path}' does not exist.")
        return False
    except Exception as e:
        print(f"An error occurred: {e} try", frappe.get_traceback())
        return False

def update_hd_ticket_agent():
    # Define the file path and search line
    TICKET_AGENT_FILE = frappe.utils.get_bench_path()+'/apps/helpdesk/desk/src/pages/TicketAgent.vue'
    if (os.path.exists(TICKET_AGENT_FILE)):

        # Append lines after 'const showSubjectDialog = ref(false);'
        search_text = 'const showSubjectDialog = ref(false);'
        new_code = [
            'let showcreateDevTicket = ref(false);',
            'let completeDevTicket = ref(false);'
        ]
        first_change = append_line_after_in_ticketagent(TICKET_AGENT_FILE, search_text, new_code)

        # Append code before 'const ticket = createResource({'
        search_text = 'const ticket = createResource({'
        new_code = '''const createDevTicket = () => {
        showcreateDevTicket.value = false;
        completeDevTicket.value=true;
        if (!ticket.data.custom_development_story_ticket || true) {
            createResource({
            url: "one_fm.overrides.hd_ticket.log_pivotal_tracker",
            auto: true,
            params: {
            name: ticket.data.name,
            description: ticket.data.description
            },
            transform: (data) => {
            
            },
            onSuccess: (data) => {
            completeDevTicket.value=false;
            ticket.reload();
            },
        });
        }
        }

        const viewDevTicket = () => {
            if (ticket.data.custom_development_story_ticket) {
                window.open(ticket.data.custom_development_story_ticket, "_blank");
            }
        }\n\n
        '''
        second_change = append_code_before_in_ticketagent(TICKET_AGENT_FILE, search_text, new_code)
    
    
        # Append Template code for button and modal
        search_text = '''      </template>
    </LayoutHeader>'''
        new_code = '''
        <div>
          <Button @click="viewDevTicket" v-if="ticket.data.custom_development_story_ticket">
            View Dev Ticket
          </Button>
          <Button @click="showcreateDevTicket = true"  v-if="!ticket.data.custom_development_story_ticket">
            Create Dev Ticket
          </Button>
          <Dialog v-model="showcreateDevTicket">
            <template #body-title>
              <h3>Create Development Ticket</h3>
            </template>
            <template #body-content>
              <p>By clicking on Confirm, a story will be created on Pivotal Tracker</p>
            </template>
            <template #actions>
              <Button variant="solid"
              @click="createDevTicket">
                Confirm
              </Button>
              <Button
                class="ml-2"
                @click="showcreateDevTicket = false"
              >
                Close
              </Button>
            </template>
          </Dialog>
          
          <Dialog v-model="completeDevTicket">
            <template #body-title>
              <h3>Creating Development Ticket</h3>
            </template>
            <template #body-content>
              <p>Development Ticket has been created...</p>
              <p>
                <Spinner class="w-8"/>
              </p>
            </template>
            <template #actions>
              <Button
                class="ml-2"
                @click="completeDevTicket = false"
              >
                Close
              </Button>
            </template>
          </Dialog>
        </div>
        </template>
        </LayoutHeader>
        '''
        third_change = append_code_before_in_ticketagent(TICKET_AGENT_FILE, search_text, new_code, replacement=True)
        print(first_change, second_change, third_change)
        if (first_change and second_change and third_change):
            # execute build
            print("Rebuilding Helpdesk")
            # Define the directories
            bench_path = frappe.utils.get_bench_path()
            helpdesk_dir = os.path.join(bench_path, 'apps/helpdesk/desk')

            # Run yarn build
            yarn_build_command = 'yarn build'
            run_command(yarn_build_command, cwd=helpdesk_dir)
            #  Restart bench
            bench_restart_command = "bench restart"
            run_command(bench_restart_command, cwd=bench_path)
    else:
        print(TICKET_AGENT_FILE, 'NOT found')
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
