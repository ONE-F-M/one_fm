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


def run_command(command, cwd=None, shell=True):
    try:
        result = subprocess.run(command, cwd=cwd, shell=shell, check=True, text=True, capture_output=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        raise



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
        raise FileNotFoundError(f"Helpdesk router not found: {router_file}")

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
      public: true,
      auth: true,
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
            raise ValueError(f"'{search_text}' not found in {router_file}; the TicketEdit route was not added.")

    print("[🎉] TicketEdit, TicketCustomer and TicketNew views deployed successfully.")
    return True


def deploy_dashboard_view():
    """Overwrite the helpdesk Dashboard.vue with the one_fm version.

    The one_fm copy renders the trend and master charts in a single flowing
    grid so the extra "Tickets by Status" chart (added server-side via the
    one_fm.overrides.dashboard override) doesn't leave a gap mid-dashboard.
    """
    bench_path = get_bench_path()

    dashboard_source = os.path.join(
        bench_path, "apps", "one_fm", "one_fm", "public", "js",
        "form_overrides", "dashboard", "Dashboard.vue",
    )
    dashboard_target = os.path.join(
        bench_path, "apps", "helpdesk", "desk", "src", "pages",
        "dashboard", "Dashboard.vue",
    )

    if not os.path.exists(dashboard_source):
        print(f"[❌] Source Dashboard.vue not found: {dashboard_source}")
        return False

    if not os.path.exists(os.path.dirname(dashboard_target)):
        raise FileNotFoundError(f"Helpdesk dashboard folder not found: {os.path.dirname(dashboard_target)}")

    # Skip the copy (and the resulting rebuild) if the file is already in sync.
    with open(dashboard_source, "r") as f:
        source_content = f.read()
    if os.path.exists(dashboard_target):
        with open(dashboard_target, "r") as f:
            if f.read() == source_content:
                print("⚠️ Dashboard.vue already up to date.")
                return False

    shutil.copy2(dashboard_source, dashboard_target)
    print(f"[✅] Dashboard.vue deployed to: {dashboard_target}")
    return True

def deploy_ticket_header():
    """Overwrite the helpdesk agent TicketHeader.vue with the one_fm version.

    The one_fm copy replaces the native Status dropdown with a Status-style
    dropdown of BPMN User Task actions (coloured per action) whenever a BPMN
    Process Instance controls the HD Ticket. It calls the one_bpmn whitelisted
    APIs get_active_bpmn_tasks / complete_task.
    """
    bench_path = get_bench_path()

    header_source = os.path.join(
        bench_path, "apps", "one_fm", "one_fm", "public", "js",
        "form_overrides", "hd_ticket", "TicketHeader.vue",
    )
    header_target = os.path.join(
        bench_path, "apps", "helpdesk", "desk", "src", "components",
        "ticket-agent", "TicketHeader.vue",
    )

    if not os.path.exists(header_source):
        print(f"[❌] Source TicketHeader.vue not found: {header_source}")
        return False

    if not os.path.exists(os.path.dirname(header_target)):
        raise FileNotFoundError(f"Helpdesk ticket-agent folder not found: {os.path.dirname(header_target)}")

    # Skip the copy (and the resulting rebuild) if the file is already in sync.
    with open(header_source, "r") as f:
        source_content = f.read()
    if os.path.exists(header_target):
        with open(header_target, "r") as f:
            if f.read() == source_content:
                print("⚠️ TicketHeader.vue already up to date.")
                return False

    shutil.copy2(header_source, header_target)
    print(f"[✅] TicketHeader.vue deployed to: {header_target}")
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

    if deploy_ticket_views():
        any_changes = True
    if deploy_dashboard_view():
        any_changes = True
    if deploy_ticket_header():
        any_changes = True
    if update_hd_ticket_side_bar():
        any_changes = True

    if any_changes:
        bench_path = frappe.utils.get_bench_path()
        helpdesk_dir = os.path.join(bench_path, 'apps/helpdesk/desk')

        run_command("NODE_OPTIONS=\"--max-old-space-size=4096\" yarn build", cwd=helpdesk_dir)
    else:
        print("No changes detected. Skipping build.")

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