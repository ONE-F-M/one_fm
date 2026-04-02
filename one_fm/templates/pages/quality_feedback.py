from __future__ import unicode_literals
import frappe, json, os
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, getdate, today, formatdate
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link as authenticate_magic_link
from one_fm.overrides.workflow import apply_workflow_ignore_permissions
from one_fm.utils import expire_magic_link, translate_words

def get_context(context):
    """
    Get the context for the quality feedback page.
    """
    context.no_cache = 1
    context.title = _("Quality Feedback")

    provided_magic_link = frappe.form_dict.get('magic_link')
    
    if not provided_magic_link:
        frappe.throw(_("Magic Link is required to access this page."))

    # Authenticate Magic Link
    magic_link = authenticate_magic_link(provided_magic_link, 'Quality Feedback', 'Quality Feedback')
    if magic_link:
        context.docname = frappe.db.get_value('Magic Link', magic_link, 'reference_docname')

@frappe.whitelist(allow_guest=True)
def get_feedback_data(docname, target_language='en'):
    """
    Get feedback data for rendering the form.
    Returns employee details, questions, and related information.
    """
    try:
        doc = frappe.get_doc('Quality Feedback', docname)
        
        # Get employee details
        employee_name = doc.get('custom_employee_name') or ''
        employee_id = doc.get('custom_employee') or ''
        operation_site = doc.get('custom_operations_site') or ''
        issued_on = formatdate(doc.get('custom_issued_on')) if doc.get('custom_issued_on') else ''
        feedback_schedule = doc.get('custom_feedback_schedule') or ''

        # Get item details
        item_code = doc.get('custom_item_code') or ''
        item_name = doc.get('custom_item_name') or ''
        item_quantity = doc.get('custom_quantity') or ''

        item_type = frappe.db.get_value('Quality Feedback Template', doc.template, 'custom_item_type') or ''
        
        # Get template and questions
        template = doc.get('template')
        questions = []
        
        if template:
            template_doc = frappe.get_doc('Quality Feedback Template', template)
            
            # Get parameters (questions) from template
            if hasattr(template_doc, 'parameters'):
                for param in template_doc.parameters:
                    rating_scale = param.get('custom_rating_scale') or ''
                    question_text = param.get('parameter') or ''
                    options_list = frappe.get_all('Rating Scale Item', filters={'parent': rating_scale}, fields=['rating_option', 'rating_score'], order_by='idx asc')
                    options = [{'option': option.rating_option, 'score': option.rating_score} for option in options_list]

                    if len(options) > 0:
                        questions.append({
                            'name': param.name,
                            'question': question_text,
                            'options': options
                        })

        # Translate dynamic data if a target language is provided
        if target_language and target_language != 'en':
            def _translate(text):
                return translate_words(text, target_language) if text else ''

            employee_name = _translate(employee_name)
            operation_site = _translate(operation_site)
            feedback_schedule = _translate(feedback_schedule)
            item_type = _translate(item_type)
            item_name = _translate(item_name)
            # item_code and item_quantity are usually not translated (codes/quantities)

        return {
            'employee_name': employee_name,
            'employee_id': employee_id,
            'operation_site': operation_site,
            'issued_on': issued_on,
            'current_feedback_schedule': feedback_schedule,
            'item_type': item_type,
            'item_code': item_code,
            'item_name': item_name,
            'item_quantity': item_quantity,
            'questions': questions
        }
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title='Quality Feedback Data Fetch Failed')
        return None

@frappe.whitelist(allow_guest=True)
def submit_feedback(docname, ratings=None, noticed_damage=None, damage_description=None, feedback_text=None, damage_attachment_url=None, damage_attachment_name=None):
    """
    Submit feedback for a given Quality Feedback document.
    Accepts ratings array, damage information, feedback text, and damage attachment.
    """
    try:
        doc = frappe.get_doc('Quality Feedback', docname)
        
        # Parse ratings if provided as string
        if isinstance(ratings, str):
            ratings = json.loads(ratings)
        
        # Save ratings to parameters
        if ratings and hasattr(doc, 'parameters'):
            # Get template parameters to match by name
            template_doc = frappe.get_doc('Quality Feedback Template', doc.template)
            template_parameters = list(template_doc.parameters) if hasattr(template_doc, 'parameters') else []
            
            # Ensure parameters exist in the document
            if not doc.parameters:
                # If parameters don't exist, create them from template
                for param in template_parameters:
                    doc.append('parameters', {
                        'parameter': param.parameter,
                        'custom_rating_scale_name': param.custom_rating_scale
                    })
            
            # Create a map of template parameter names to document parameter rows
            param_map = {}
            for idx, param_row in enumerate(doc.parameters):
                if idx < len(template_parameters):
                    template_param_name = template_parameters[idx].name
                    param_map[template_param_name] = param_row
            
            # Update parameters with ratings using parameter_name only
            for rating_data in ratings:
                parameter_name = rating_data.get('parameter_name', '')
                rating_score = rating_data.get('rating_score')
                rating_option = rating_data.get('rating_option', '')
                
                # Match by parameter_name only
                if parameter_name and parameter_name in param_map:
                    param_row = param_map[parameter_name]
                    param_row.custom_rating_option = rating_option
                    param_row.custom_rating_score = rating_score
        
        # Save damage information
        if noticed_damage:
            if hasattr(doc, 'custom_noticed_damage'):
                doc.custom_noticed_damage = noticed_damage
        
        if damage_description:
            if hasattr(doc, 'custom_damage_description'):
                doc.custom_damage_description = damage_description
        
        # Save feedback text
        if feedback_text:
            if hasattr(doc, 'custom_feedback'):
                doc.custom_feedback = feedback_text
            # Also save to feedback field if it exists
            if hasattr(doc, 'feedback'):
                doc.feedback = feedback_text
        
        # Attach damage file if provided
        if damage_attachment_url:
            # The file should already be attached by upload_file API when doctype/docname are provided
            # Just ensure the custom field is set
            if hasattr(doc, 'custom_damage_attachment'):
                doc.custom_damage_attachment = damage_attachment_url
            
            # Verify file attachment exists, create if not
            existing_file = frappe.db.exists('File', {
                'attached_to_doctype': 'Quality Feedback',
                'attached_to_name': docname,
                'attached_to_field': 'custom_damage_attachment'
            })
            
            if not existing_file:
                # File might not be linked, find it by URL and link it
                file_doc = frappe.db.get_value('File', {'file_url': damage_attachment_url}, 'name')
                if file_doc:
                    file_doc = frappe.get_doc('File', file_doc)
                    file_doc.attached_to_doctype = 'Quality Feedback'
                    file_doc.attached_to_name = docname
                    file_doc.attached_to_field = 'custom_damage_attachment'
                    file_doc.save(ignore_permissions=True)
        
        if damage_attachment_url:
            rename_damage_attachment(doc, damage_attachment_url)

        doc.save(ignore_permissions=True)
        frappe.db.commit()
        apply_workflow_ignore_permissions(doc, "Submit")
        expire_magic_link('Quality Feedback', docname, 'Quality Feedback')
        
        return {'success': True, 'message': _('Feedback submitted successfully.')}
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title='Quality Feedback Submission Failed')
        return {'success': False, 'message': _('An error occurred while submitting feedback.')}


def rename_damage_attachment(doc, damage_attachment_url):
    if not damage_attachment_url:
        return
    
    try:
        file_doc_name = frappe.db.get_value('File', {'file_url': damage_attachment_url}, 'name')
        if not file_doc_name:
            return
        
        file_doc = frappe.get_doc('File', file_doc_name)
        
        employee_id = getattr(doc, "custom_employee", None)
        template_name = getattr(doc, "template", None)
        if not employee_id or not template_name:
            frappe.log_error(title="Missing custom_employee or template in doc for file rename.", message="File Rename Failed")
            return
        clean_template = template_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        
        file_ext = os.path.splitext(file_doc.file_name)[1]
        
        counter = 1
        new_file_name = f"{employee_id}_{clean_template}_{counter:03d}{file_ext}"
        
        while frappe.db.exists('File', {'file_name': new_file_name, 'name': ['!=', file_doc.name]}):
            counter += 1
            new_file_name = f"{employee_id}_{clean_template}_{counter:03d}{file_ext}"
        
        file_doc.file_name = new_file_name
        file_doc.save(ignore_permissions=True)
        
    except Exception as e:
        frappe.log_error(message=f"{frappe.get_traceback()}\nException: {str(e)}", title='File Rename Failed')



@frappe.whitelist(allow_guest=True)
def translate_text(text, target_language='en'):
    """
    Translate text using Google Translate.
    """
    try:
        if not text or target_language == 'en':
            return text
        
        translated = translate_words(text, target_language)
        return translated
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title='Translation Failed')
        return text  # Return original text if translation fails

@frappe.whitelist(allow_guest=True)
def get_all_languages():
    """
    Get all languages from Quality Feedback Form Languages in Stock Settings.
    """
    try:
        # Get Stock Settings document
        stock_settings = frappe.get_single("Stock Settings")
        
        # Get the quality_feedback_form_languages field (Table MultiSelect)
        # Access as attribute (Frappe pattern for child tables)
        language_rows = getattr(stock_settings, "quality_feedback_form_languages", []) or []
        
        if not language_rows:
            return []
        
        # Extract language names from the child table rows
        # The child table has a 'language' field that links to Language doctype
        language_names = []
        for row in language_rows:
            # Handle both dict and object access patterns
            language_name = row.get('language') if isinstance(row, dict) else getattr(row, 'language', None)
            if language_name:
                language_names.append(language_name)
        
        if not language_names:
            return []
        
        # Get language details from Language doctype
        languages = frappe.get_all(
            'Language',
            filters={'name': ['in', language_names]},
            fields=['name', 'language_name'],
            order_by='language_name'
        )
        
        return languages
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title='Failed to fetch languages')
        return []

@frappe.whitelist(allow_guest=True)
def translate_multiple(texts, target_language='en'):
    """
    Translate multiple texts at once.
    """
    try:
        if not texts or target_language == 'en':
            return texts if isinstance(texts, list) else [texts]
        
        if isinstance(texts, str):
            texts = json.loads(texts)
        
        translated = []
        for text in texts:
            if text:
                translated.append(translate_words(text, target_language))
            else:
                translated.append(text)
        
        return translated
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title='Batch Translation Failed')
        return texts if isinstance(texts, list) else [texts]
