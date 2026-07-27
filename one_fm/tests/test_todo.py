import unittest
from unittest.mock import patch, MagicMock, call
from frappe.tests.utils import FrappeTestCase

# python


import one_fm.overrides.todo as todo_mod

class TestToDoOverrides(FrappeTestCase):
    def setUp(self):
        self.doc = MagicMock()
        self.doc.is_new.return_value = False
        self.doc.doctype = "ToDo"
        self.doc.name = "TODO-001"
        self.doc.status = "Open"
        self.doc.assigned_by = "user1"
        self.doc.allocated_to = "user2"
        self.doc.reference_type = "Task"
        self.doc.reference_name = "TASK-001"
        self.doc.description = "<p>Test Description</p>"
        self.doc.creation = "2024-06-01"
        self.doc.date = "2024-06-10"
        self.doc.custom_google_task_title = ""
        self.doc.custom_google_task_id = ""
        self.doc.type = ""
        self.doc.notify_allocated_to_via_email = True
        self.doc.custom_source = "ERPNext"
        self.doc.get_doc_before_save.return_value = None

    @patch.object(todo_mod.FrappeToDo, "on_trash")
    @patch("one_fm.overrides.todo.delete_google_task_on_todo_delete")
    @patch.object(todo_mod.ToDo, "__init__", lambda self: None)
    def test_on_trash_calls_super_and_close(self, mock_close, mock_super):
        todo = todo_mod.ToDo()
        todo.on_trash()
        mock_super.assert_called_once_with()
        mock_close.assert_called_once_with(todo)

    @patch("one_fm.overrides.todo.notify_todo_status_change")
    @patch("one_fm.overrides.todo.set_todo_type_from_refernce_doc")
    @patch("one_fm.overrides.todo.validate_google_task_title")
    def test_validate_todo_calls_all(self, mock_val_title, mock_set_type, mock_notify):
        todo_mod.validate_todo(self.doc, "on_update")
        mock_notify.assert_called_once_with(self.doc)
        mock_set_type.assert_called_once_with(self.doc)
        mock_val_title.assert_called_once_with(self.doc)

    @patch("frappe.session")
    @patch("frappe.db.get_value")
    @patch("frappe.new_doc")
    @patch("one_fm.overrides.todo.send_notification_alert_only")
    @patch("frappe.get_meta")
    def test_notify_todo_status_change_creates_notification(self, mock_meta, mock_alert_only, mock_new_doc, mock_get_value, mock_session):
        # Setup
        self.doc.is_new.return_value = False
        def get_value_side_effect(doctype, name, field, **kwargs):
            if doctype == "User" and kwargs.get("as_dict"):
                return {"first_name": "Test", "last_name": "User"}
            if field == "status":
                return "Closed"
            return "Task Subject"
        mock_get_value.side_effect = get_value_side_effect
        mock_alert_only.return_value = False
        mock_session.user = "user3"
        notification_log = MagicMock()
        mock_new_doc.return_value = notification_log

        todo_mod.notify_todo_status_change(self.doc)

        mock_get_value.assert_any_call(self.doc.doctype, self.doc.name, "status")
        mock_new_doc.assert_called_once_with("Notification Log")
        self.assertIn("assignment is", notification_log.subject)
        self.assertIn("Description", notification_log.email_content)
        self.assertEqual(notification_log.for_user, self.doc.assigned_by)
        self.assertEqual(notification_log.document_type, self.doc.doctype)
        self.assertEqual(notification_log.document_name, self.doc.name)
        self.assertEqual(notification_log.from_user, "user3")
        self.assertEqual(notification_log.type, "Assignment")
        notification_log.insert.assert_called_once_with(ignore_permissions=True)

    def test_send_notification_alert_only(self):
        with patch("one_fm.overrides.todo.is_user_id_company_prefred_email_in_employee") as mock_pref:
            # Administrator always True
            self.assertTrue(todo_mod.send_notification_alert_only("Administrator"))
            # Not company preferred
            mock_pref.return_value = False
            self.assertTrue(todo_mod.send_notification_alert_only("userX"))
            # Company preferred
            mock_pref.return_value = True
            self.assertFalse(todo_mod.send_notification_alert_only("userY"))

    @patch("frappe.db.get_value")
    @patch("one_fm.overrides.todo.convert_html_to_plain_text")
    def test_validate_google_task_title_sets_title(self, mock_convert, mock_get_value):
        # Already set
        self.doc.custom_google_task_title = "Already Set"
        todo_mod.validate_google_task_title(self.doc)
        self.assertEqual(self.doc.custom_google_task_title, "Already Set")

        # Task reference
        self.doc.custom_google_task_title = ""
        self.doc.reference_type = "Task"
        self.doc.reference_name = "TASK-001"
        mock_get_value.return_value = "Task Subject"
        todo_mod.validate_google_task_title(self.doc)
        self.assertEqual(self.doc.custom_google_task_title, "Task Subject")

        # Other reference
        self.doc.custom_google_task_title = ""
        self.doc.reference_type = "Project"
        self.doc.reference_name = "PROJ-001"
        todo_mod.validate_google_task_title(self.doc)
        self.assertIn("Action required for Project", self.doc.custom_google_task_title)

        # No reference
        self.doc.custom_google_task_title = ""
        self.doc.reference_type = None
        self.doc.reference_name = None
        mock_convert.return_value = "Plain text"
        todo_mod.validate_google_task_title(self.doc)
        self.assertEqual(self.doc.custom_google_task_title, "Plain text")

    @patch("frappe.get_meta")
    @patch("frappe.db.get_value")
    def test_set_todo_type_from_refernce_doc(self, mock_get_value, mock_get_meta):
        # With type field
        self.doc.reference_type = "Project"
        self.doc.reference_name = "PROJ-001"
        meta = MagicMock()
        meta.has_field.return_value = True
        mock_get_meta.return_value = meta
        mock_get_value.return_value = "Bug"
        todo_mod.set_todo_type_from_refernce_doc(self.doc)
        self.assertEqual(self.doc.type, "Bug")

        # Without type field
        meta.has_field.return_value = False
        todo_mod.set_todo_type_from_refernce_doc(self.doc)
        self.assertEqual(self.doc.type, "Action")

        # No reference
        self.doc.reference_type = None
        self.doc.reference_name = None
        self.doc.type = ""
        todo_mod.set_todo_type_from_refernce_doc(self.doc)
        self.assertEqual(self.doc.type, "")
    
    @patch("frappe.utils.get_url_to_form", side_effect=lambda doctype, name: f"/app/{doctype.lower()}/{name}")
    def test_create_description_for_google_todo(self, mock_get_url_to_form):
        # Only description
        self.doc.description = "<p>Desc</p>"
        self.doc.reference_type = None
        self.doc.reference_name = None
        with patch("one_fm.overrides.todo.convert_html_to_plain_text", return_value="Desc") as mock_convert:
            result = todo_mod.create_description_for_google_todo(self.doc)
            self.assertEqual(result, "Desc")

        # With reference
        self.doc.reference_type = "Task"
        self.doc.reference_name = "TASK-001"
        self.doc.name = "TODO-001"
        with patch("one_fm.overrides.todo.convert_html_to_plain_text", return_value="Desc") as mock_convert, \
            patch("frappe.utils.get_url_to_form", side_effect=lambda doctype, name: f"/app/{doctype.lower()}/{name}"):
            result = todo_mod.create_description_for_google_todo(self.doc)
            self.assertIn("Hey you can't update this task", result)
            self.assertIn("TODO-001", result)
            self.assertIn("TASK-001", result)

    def test_convert_html_to_plain_text(self):
        # Simple paragraph
        html = "<p>Hello</p>"
        result = todo_mod.convert_html_to_plain_text(html)
        self.assertIn("Hello", result)

        # Table
        html = "<table><tr><td>A</td><td>B</td></tr></table>"
        result = todo_mod.convert_html_to_plain_text(html)
        self.assertIn("A : B", result)
        self.assertIn("Details:", result)

        # No html
        html = "Just text"
        result = todo_mod.convert_html_to_plain_text(html)
        self.assertEqual(result, "Just text")

        # Exception
        with patch("one_fm.overrides.todo.BeautifulSoup", side_effect=Exception("fail")):
            with patch("frappe.log_error") as mock_log:
                result = todo_mod.convert_html_to_plain_text("<p>fail</p>")
                self.assertEqual(result, "Failed to parse content.")
                mock_log.assert_called()

    @patch("frappe.sendmail")
    @patch("frappe.db.get_value")
    @patch("frappe.session")
    @patch("frappe.render_template")
    @patch("one_fm.overrides.todo.sendemail") 
    @patch("one_fm.processor.is_user_id_company_prefred_email_in_employee", return_value={
    "prefered_contact_email": "Company Email",
    "prefered_email": "user2@example.com",
    "company_email": "user2@example.com",
    "personal_email": "user2@example.com",
    "status": "Active"
})
    def test_send_email_on_todo_created(self, mock_is_user_id_company_prefred_email_in_employee, mock_sendemail, mock_render, mock_session, mock_get_value, mock_sendmail):
        # notify_allocated_to_via_email False
        self.doc.notify_allocated_to_via_email = False
        todo_mod.send_email_on_todo_created(self.doc, "on_update")
        mock_sendemail.assert_not_called()

        # notify_allocated_to_via_email True, user_email == allocated_to
        self.doc.notify_allocated_to_via_email = True
        mock_get_value.return_value = "user2"
        mock_session.user = "user2"
        todo_mod.send_email_on_todo_created(self.doc, "on_update")
        mock_sendemail.assert_not_called()

        # notify_allocated_to_via_email True, user_email != allocated_to
        self.doc.notify_allocated_to_via_email = True
        mock_get_value.return_value = "user1@example.com"
        mock_session.user = "user1"
        self.doc.allocated_to = "user2@example.com"
        self.doc.reference_type = "Task"
        self.doc.reference_name = "TASK-001"
        self.doc.name = "TODO-001"
        mock_render.return_value = "Rendered Message"
        todo_mod.send_email_on_todo_created(self.doc, "on_update")

        mock_sendemail.assert_called_once()
        args, kwargs = mock_sendemail.call_args
        self.assertIn("user2@example.com", kwargs["recipients"])
        self.assertIn("Rendered Message", kwargs["message"])
        self.assertIn("A Task has been Created", kwargs["subject"])

    @patch("frappe.db.get_value")
    def test_build_notification_subject_content(self, mock_get_value):
        # Setup
        doc = MagicMock()
        doc.reference_type = "Task"
        doc.reference_name = "TASK-001"
        doc.status = "Open"
        doc.description = "Test Desc"
        doc.creation = "2024-06-01"
        doc.date = "2024-06-10"
        user = "test_user"
        def get_value_side_effect(doctype, name, field, **kwargs):
            if doctype == "User" and kwargs.get("as_dict"):
                return {"first_name": "Test", "last_name": "User"}
            if doctype == "Task" and field == "subject":
                return "Task Subject"
            return None

        mock_get_value.side_effect = get_value_side_effect
        # Test
        subject, email_content = todo_mod.build_notification_subject_content(doc, user)
        self.assertIn("Task", subject)
        self.assertIn("Task Subject", subject)
        self.assertIn("Test Desc", email_content)
        self.assertIn("Subject:Task Subject", email_content)

    @patch("frappe.db.exists", return_value=True)
    @patch("one_fm.overrides.todo.create_description_for_google_todo", return_value="notes")
    @patch("one_fm.overrides.todo.get_google_task_service")
    def test_create_google_task_writes_id_without_save(self, mock_service_fn, mock_notes, mock_exists):
        """The background job must persist the Google Task id via db_set (no save())."""
        service = MagicMock()
        service.tasks.return_value.insert.return_value.execute.return_value = {"id": "GTASK-123"}
        mock_service_fn.return_value = service

        self.doc.custom_google_task_id = ""
        self.doc.allocated_to = "user2@example.com"
        self.doc.custom_google_task_title = "Some Title"
        self.doc.date = "2024-06-10"

        result = todo_mod.create_google_task_on_todo_creation_in_erp(self.doc, "after_insert")

        # Reloaded, then wrote only the id column without touching modified timestamp.
        self.doc.reload.assert_called_once_with()
        self.doc.db_set.assert_called_once_with(
            "custom_google_task_id", "GTASK-123", update_modified=False
        )
        # A bare save() would re-fire hooks and risk the TimestampMismatchError.
        self.doc.save.assert_not_called()
        self.assertEqual(result["id"], "GTASK-123")

    @patch("frappe.db.exists", return_value=False)
    @patch("one_fm.overrides.todo.create_description_for_google_todo", return_value="notes")
    @patch("one_fm.overrides.todo.get_google_task_service")
    def test_create_google_task_skips_when_todo_deleted(self, mock_service_fn, mock_notes, mock_exists):
        """If the ToDo was removed while the job was queued, bail out cleanly."""
        service = MagicMock()
        service.tasks.return_value.insert.return_value.execute.return_value = {"id": "GTASK-123"}
        mock_service_fn.return_value = service

        self.doc.custom_google_task_id = ""
        self.doc.allocated_to = "user2@example.com"

        result = todo_mod.create_google_task_on_todo_creation_in_erp(self.doc, "after_insert")

        self.doc.reload.assert_not_called()
        self.doc.db_set.assert_not_called()
        self.doc.save.assert_not_called()
        self.assertIsNone(result)

    @patch("frappe.new_doc")
    @patch("one_fm.overrides.todo.send_notification_alert_only", return_value=False)
    def test_create_notification_log(self, mock_alert_only, mock_new_doc):
        doc = MagicMock()
        doc.assigned_by = "user1"
        doc.doctype = "ToDo"
        doc.name = "TODO-001"
        subject = "Test Subject"
        email_content = "Test Content"
        user = "test_user"
        notification_log = MagicMock()
        mock_new_doc.return_value = notification_log
        todo_mod.create_notification_log(doc, user, subject, email_content)
        mock_new_doc.assert_called_once_with("Notification Log")
        self.assertEqual(notification_log.subject, subject)
        self.assertEqual(notification_log.email_content, email_content)
        self.assertEqual(notification_log.for_user, doc.assigned_by)
        self.assertEqual(notification_log.document_type, doc.doctype)
        self.assertEqual(notification_log.document_name, doc.name)
        self.assertEqual(notification_log.from_user, user)
        self.assertEqual(notification_log.type, "Assignment")
        notification_log.insert.assert_called_once_with(ignore_permissions=True)
