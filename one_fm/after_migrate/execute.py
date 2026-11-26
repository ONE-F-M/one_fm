import frappe, os, shutil, subprocess

from frappe.utils import cstr, get_bench_path
from one_fm.utils import production_domain

# Anchors move when a vendored app is upgraded. A patch that no longer finds
# its anchor is not an error to the caller, it just silently stops shipping,
# so every miss is collected here and reported at the end of the run.
PATCH_WARNINGS = []


def record_patch_warning(message):
    print(message)
    PATCH_WARNINGS.append(message)

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
    target = os.path.join(
        get_bench_path(), "apps", "hrms", "hrms", "templates", "generators", "job_opening.html",
    )
    source = os.path.join(
        get_bench_path(), "apps", "one_fm", "one_fm", "templates", "generators", "job_opening.html",
    )

    # Guarded: this runs in before_migrate, so an unguarded os.remove on a
    # template hrms has renamed would take the whole migrate down with it.
    if not os.path.exists(source):
        record_patch_warning("[!] Source job_opening.html not found: " + source)
    elif not os.path.exists(os.path.dirname(target)):
        record_patch_warning("[!] hrms generators folder not found: " + os.path.dirname(target))
    else:
        if os.path.exists(target):
            os.remove(target)
        shutil.copy(source, target)

    site_path = os.path.join(get_bench_path(), "sites", cstr(frappe.local.site))
    for folder in ["public/files/user", "public/files/user/magic_link"]:
        os.makedirs(os.path.join(site_path, folder), exist_ok=True)


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

            # Without this guard the file was rewritten unchanged and the patch
            # still reported success, so a dead anchor looked like a live
            # customization and charged the caller a rebuild every time.
            if search_text not in lines:
                record_patch_warning(
                    f"[!] {os.path.basename(file_path)}: anchor not found, patch not applied: '{search_text}'"
                )
                return False

            with open(file_path, 'w') as file_write:
                file_write.write(lines.replace(search_text, appendable_code))
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
                record_patch_warning(
                    f"[!] {os.path.basename(file_path)}: anchor not found, patch not applied: '{search_text}'"
                )
                return False
    except FileNotFoundError:
        record_patch_warning(f"[!] The file '{file_path}' does not exist.")
        return False
    except Exception as e:
        print(f"An error occurred: {e} try", frappe.get_traceback())
        return False

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
        record_patch_warning(str(FILE_PATH) + ' not found')
    return False


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
    """Deploy the one_fm customer ticket views and their route.

    Returns True only when something was actually written: every True here
    costs the caller a full yarn build and a bench restart.
    """
    bench_path = get_bench_path()

    overrides_folder = os.path.join(
        bench_path, "apps", "one_fm", "one_fm", "public", "js",
        "form_overrides", "hd_ticket",
    )
    ticket_target_folder = os.path.join(
        bench_path, "apps", "helpdesk", "desk", "src", "pages", "ticket",
    )

    any_changes = False
    for filename in ["TicketEdit.vue", "TicketCustomer.vue"]:
        if copy_if_changed(
            os.path.join(overrides_folder, filename),
            os.path.join(ticket_target_folder, filename),
            filename,
        ):
            any_changes = True

    if deploy_ticket_edit_route():
        any_changes = True

    return any_changes


def deploy_ticket_edit_route():
    """Add the TicketEdit route to the helpdesk router if it is not there."""
    router_file = os.path.join(
        get_bench_path(), "apps", "helpdesk", "desk", "src", "router", "index.ts",
    )

    if not os.path.exists(router_file):
        record_patch_warning("[!] Router file not found: " + router_file)
        return False

    with open(router_file, "r") as f:
        router_content = f.read()

    if 'name: "TicketEdit"' in router_content:
        print("TicketEdit route already present.")
        return False

    search_text = "const routes = ["
    if search_text not in router_content:
        record_patch_warning(
            "[!] index.ts: anchor not found, TicketEdit route not added: '" + search_text + "'"
        )
        return False

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

    parts = router_content.split(search_text)
    with open(router_file, "w") as f:
        f.write(parts[0] + search_text + appendable_code + parts[1])

    print("TicketEdit route added.")
    return True


def copy_if_changed(source, target, label):
    """Copy source over target only when they differ.

    Returns True when the file was actually written, so callers can skip the
    (expensive) yarn build when nothing changed.
    """
    if not os.path.exists(source):
        record_patch_warning(f"[❌] Source {label} not found: {source}")
        return False

    if not os.path.exists(os.path.dirname(target)):
        record_patch_warning(
            f"[❌] Target folder not found: {os.path.dirname(target)}"
        )
        return False

    with open(source, "r") as f:
        source_content = f.read()

    if os.path.exists(target):
        with open(target, "r") as f:
            if f.read() == source_content:
                print(f"⚠️ {label} already up to date.")
                return False

    shutil.copy2(source, target)
    print(f"[✅] {label} deployed to: {target}")
    return True


def deploy_fetch_from_support():
    """Deploy the fetch_from support for the helpdesk portal forms.

    The portal is a standalone frappe-ui SPA and never loads the desk's
    `add_fetch` implementation, so `fetch_from` on HD Ticket custom fields does
    nothing live in the new / edit ticket forms. These files add it:

      * api.py            - sends fetch_from / fetch_if_empty / read_only to
                            the frontend (the stock query drops them)
      * fetchFrom.ts      - the client-side fetch engine
      * TicketNew.vue     - wires it into the new-ticket form
      * formCustomisation - folds read_only into the parsed `readonly` flag
      * UniInput.vue      - disables fields marked readonly
      * Link.vue          - lazy, paged link search (no 999-row prefetch)
      * FrappeUiAutocomplete.vue - exposes showOptions so Link can load on
                            first open, and shows a loading state
      * Autocomplete.vue  - caps how many options are drawn at once, so a long
                            list (Reference Doctype) stays responsive
      * types.ts          - declares the three props on the Field interface
      * TicketDetailsTab.vue - drops Customer and Team from the agent
                            ticket sidebar
      * TicketCustomerSidebar.vue / TicketCustomerTemplateFields.vue
                          - hide fields depends_on rules out on the customer
                            ticket view, as the agent view already does
    """
    bench_path = get_bench_path()

    overrides_folder = os.path.join(
        bench_path, "apps", "one_fm", "one_fm", "public", "js",
        "form_overrides", "hd_ticket",
    )
    desk_src = os.path.join(bench_path, "apps", "helpdesk", "desk", "src")

    # (source filename, target path, label)
    files = [
        (
            "hd_ticket_template_api.py",
            os.path.join(
                bench_path, "apps", "helpdesk", "helpdesk", "helpdesk",
                "doctype", "hd_ticket_template", "api.py",
            ),
            "HD Ticket Template api.py",
        ),
        (
            "fetchFrom.ts",
            os.path.join(desk_src, "composables", "fetchFrom.ts"),
            "fetchFrom.ts",
        ),
        (
            "formCustomisation.ts",
            os.path.join(desk_src, "composables", "formCustomisation.ts"),
            "formCustomisation.ts",
        ),
        (
            "types.ts",
            os.path.join(desk_src, "types.ts"),
            "types.ts",
        ),
        (
            "UniInput.vue",
            os.path.join(desk_src, "components", "UniInput.vue"),
            "UniInput.vue",
        ),
        (
            "Link.vue",
            os.path.join(desk_src, "components", "frappe-ui", "Link.vue"),
            "Link.vue",
        ),
        (
            "FrappeUiAutocomplete.vue",
            os.path.join(desk_src, "components", "frappe-ui", "Autocomplete.vue"),
            "frappe-ui Autocomplete.vue",
        ),
        (
            "Autocomplete.vue",
            os.path.join(desk_src, "components", "Autocomplete.vue"),
            "Autocomplete.vue",
        ),
        (
            "TicketNew.vue",
            os.path.join(desk_src, "pages", "ticket", "TicketNew.vue"),
            "TicketNew.vue",
        ),
        (
            "TicketDetailsTab.vue",
            os.path.join(desk_src, "components", "ticket-agent", "TicketDetailsTab.vue"),
            "TicketDetailsTab.vue",
        ),
        (
            "TicketCustomerSidebar.vue",
            os.path.join(desk_src, "components", "ticket", "TicketCustomerSidebar.vue"),
            "TicketCustomerSidebar.vue",
        ),
        (
            "TicketCustomerTemplateFields.vue",
            os.path.join(desk_src, "pages", "ticket", "TicketCustomerTemplateFields.vue"),
            "TicketCustomerTemplateFields.vue",
        ),
    ]

    any_changes = False
    for filename, target, label in files:
        if copy_if_changed(os.path.join(overrides_folder, filename), target, label):
            any_changes = True

    return any_changes


def deploy_ticket_editor():
    """Overwrite the helpdesk ticket description editor with the one_fm version.

    Reported on HD Ticket 1934569: dragging a picture into the New Ticket
    description looks like it is ignored. The file does reach the server, it is
    just never put back into the editor, and it is left public, in Home,
    attached to nothing.

    Two defects, both upstream:

      * TicketNew.vue passes :uploadFunction to TicketTextEditor, but neither
        TicketTextEditor nor the TextEditor wrapper declares it, so it never
        reaches frappe-ui. frappe-ui falls back to its own uploader, which
        stores the file public, in Home, with no doctype, which is exactly what
        the two orphaned files on 1934569 look like.

      * frappe-ui's image extension handles a drop by inserting a placeholder
        node, uploading, then swapping the placeholder for the result. The
        placeholder does not survive the editor's content round trip, so the
        swap finds nothing and the picture never appears. Pasting runs through a
        different extension, which is why Cmd+V works.

    The one_fm copies declare the prop down the chain, and take the drop in the
    capture phase before ProseMirror sees it: upload first, then insert the
    finished image, so there is no placeholder to lose.
    """
    bench_path = get_bench_path()

    overrides_folder = os.path.join(
        bench_path, "apps", "one_fm", "one_fm", "public", "js",
        "form_overrides", "hd_ticket",
    )
    desk_src = os.path.join(bench_path, "apps", "helpdesk", "desk", "src")

    files = [
        (
            "TicketTextEditor.vue",
            os.path.join(desk_src, "pages", "ticket", "TicketTextEditor.vue"),
            "TicketTextEditor.vue",
        ),
        (
            "TextEditor.vue",
            os.path.join(desk_src, "components", "TextEditor.vue"),
            "TextEditor.vue",
        ),
    ]

    any_changes = False
    for filename, target, label in files:
        if copy_if_changed(os.path.join(overrides_folder, filename), target, label):
            any_changes = True

    return any_changes


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
        print(f"[❌] Target dashboard folder not found: {os.path.dirname(dashboard_target)}")
        return False

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
    Process Instance controls the HD Ticket. It calls the processa whitelisted
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
        print(f"[❌] Target ticket-agent folder not found: {os.path.dirname(header_target)}")
        return False

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
        record_patch_warning(str(FILE_PATH) + ' not found')
    return False


def remove_code_block_with_regex(file_path, pattern):
    import re
    try:
        with open(file_path, 'r') as file:
            content = file.read()

        # Check if the pattern exists
        if not re.search(pattern, content, flags=re.MULTILINE | re.VERBOSE):
            record_patch_warning(
                f"[!] {os.path.basename(file_path)}: pattern not found, block not removed"
            )
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


def deploy_ticket_field():
    """Overwrite the helpdesk agent TicketField.vue with the one_fm version.

    Stock TicketField.vue lumps "Text Editor" in with the plain text types and
    renders it as a single-line <input>, so an HTML field such as
    resolution_details shows its raw markup in the Ticket Info sidebar - and the
    blur handler writes whatever is left in that input back to the DB. The
    one_fm copy renders Text Editor fields as a sanitized preview that opens a
    real TextEditor dialog, keeping them editable without corrupting the HTML.

    The one_fm copy also carries the Check-field fix (extractValue): the stock
    handler unwrapped the emitted option with a truthy `||` chain, so "No"
    (value 0) fell through and the option OBJECT was written back as the field
    value, which rendered as "Yes" again and kept every depends_on child field
    visible. That fix used to live in a separate surgical patch, which fought
    this copy on every migrate: the copy restored the stock handler, the patch
    put the fix back, and both reported a change, so every migrate paid for a
    rebuild. A file is owned by one mechanism only.
    """
    bench_path = get_bench_path()

    field_source = os.path.join(
        bench_path, "apps", "one_fm", "one_fm", "public", "js",
        "form_overrides", "hd_ticket", "TicketField.vue",
    )
    field_target = os.path.join(
        bench_path, "apps", "helpdesk", "desk", "src", "components",
        "TicketField.vue",
    )

    return copy_if_changed(field_source, field_target, "TicketField.vue")


REFERENCE_DOCTYPE_FIELD = "custom_reference_doctype"
REFERENCE_DOCTYPE_URL_METHOD = "one_fm.overrides.hd_ticket.get_reference_doctypes"


def set_reference_doctype_url_method():
    """Serve the Reference Doctype options from a cached endpoint.

    As a plain Link field it hits frappe.desk.search.search_link on every
    keystroke, and against DocType (~1700 rows) that round trip is what makes
    the dropdown feel frozen. Pointing the template field at a url_method
    switches it to an Autocomplete fed by one cached call, filtered in the
    browser.

    Data-only, so it does not flag a frontend rebuild.
    """
    rows = frappe.get_all(
        "HD Ticket Template Field",
        filters={
            "fieldname": REFERENCE_DOCTYPE_FIELD,
            "parenttype": "HD Ticket Template",
        },
        fields=["name", "parent", "url_method"],
    )
    if not rows:
        print(f"⚠️ No HD Ticket Template Field row for {REFERENCE_DOCTYPE_FIELD}.")
        return

    for row in rows:
        if row.url_method == REFERENCE_DOCTYPE_URL_METHOD:
            print(f"⚠️ {row.parent}.{REFERENCE_DOCTYPE_FIELD} url_method already set.")
            continue
        frappe.db.set_value(
            "HD Ticket Template Field", row.name, "url_method", REFERENCE_DOCTYPE_URL_METHOD
        )
        print(f"[✅] {row.parent}.{REFERENCE_DOCTYPE_FIELD} now served by {REFERENCE_DOCTYPE_URL_METHOD}")


def update_all_ticket_features():
    any_changes = False
    del PATCH_WARNINGS[:]

    set_reference_doctype_url_method()

    if add_resolution_details_updation():
        any_changes = True
    if deploy_ticket_views():
        any_changes = True
    if deploy_fetch_from_support():
        any_changes = True
    if deploy_dashboard_view():
        any_changes = True
    if deploy_ticket_header():
        any_changes = True
    if deploy_ticket_field():
        any_changes = True
    if deploy_ticket_editor():
        any_changes = True
    if update_hd_ticket_side_bar():
        any_changes = True

    if any_changes:
        bench_path = frappe.utils.get_bench_path()
        helpdesk_dir = os.path.join(bench_path, 'apps/helpdesk/desk')

        run_command("NODE_OPTIONS=\"--max-old-space-size=4096\" yarn build", cwd=helpdesk_dir)
        run_command("bench restart", cwd=bench_path)
    else:
        print("No changes detected. Skipping build and restart.")

    # A customization whose anchor has moved stops shipping without failing
    # anything, so say so loudly rather than leaving it in the scrollback.
    if PATCH_WARNINGS:
        print("\n======================================================================")
        print("{0} helpdesk customization(s) did NOT apply:".format(len(PATCH_WARNINGS)))
        for warning in PATCH_WARNINGS:
            print("  - " + warning)
        print("======================================================================")

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