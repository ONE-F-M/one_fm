# Processa document actions (`processa.py`)

Read this before you write or change any API that approves, rejects, submits or otherwise moves a record whose DocType runs on a Processa (one_bpmn) process map. Reuse these two endpoints. Do not add a new endpoint per DocType for the same purpose.

## When to use it

Use it when the record's lifecycle is driven by a Processa map. That is, an active BPMN Process Model starts on the DocType, or targets it. On those records:

- The actions come from the map's User Tasks, not from a Frappe Workflow.
- `apply_workflow(doc, "...")`, `doc.submit()` and hardcoded Approve/Reject buttons either fail ("Workflow not found" once the Frappe Workflow is inactive) or move the record without the map.

To list the DocTypes run by Processa, call `one_bpmn.api.instance_api.get_processa_controlled_doctypes()`.

## Endpoints

### `one_fm.api.v1.processa.get_document_actions` (GET)

| Argument | Type | Notes |
|---|---|---|
| `doctype` | str | Any DocType |
| `docname` | str | The record |

Checks read permission on the record. Returns:

```json
{
  "workflow_state": "Pending Relieving Date Correction",
  "actions": [
    {"instance_name": "nouabqm7ap", "task_id": "8c1f...", "task_name": "Resubmit Date", "action": "Resubmit Date", "confirm": false}
  ],
  "pending_with": [],
  "editable_fields": ["resignation_initiation_date", "relieving_date", "resignation_letter"]
}
```

- `actions`: one entry per action on each Waiting User Task the session user may complete (assignee, reliever, approved Contingency Task Completion, or BPMN super user). `confirm` is the map's `confirmTransition`. A task with no configured actions gives one entry with `action: ""` and `confirm: true`.
- `pending_with`: full names of the assignees (or the role) of Waiting tasks the user cannot complete. The desk shows this as "Pending action from".
- `editable_fields`: what the DocType's `get_processa_editable_fields()` returns, or `[]` if the DocType does not define it.

### `one_fm.api.v1.processa.apply_document_action` (POST)

| Argument | Type | Notes |
|---|---|---|
| `doctype` | str | |
| `docname` | str | |
| `task_id` | str | From `actions` |
| `action` | str | From `actions`; `""` for a task with no configured actions |
| `values` | dict or JSON str, optional | Field values to save before completing the task |
| `attachments` | dict or JSON str, optional | `{fieldname: {"attachment_name": "letter.jpg", "attachment": "<base64>"}}` |

Steps, in one request:

1. Checks read permission on the record.
2. Refuses with `PermissionError` unless the `(task_id, action)` pair is in the user's current `actions`. The process instance is taken from the server, never from the client.
3. If `values` or `attachments` are sent: refuses with `PermissionError` any field not in `editable_fields`. Otherwise checks write permission, runs `doc.update(values)` and `doc.save()`, then stores each attachment through the File DocType with `handle_attachment_internal`.
4. Calls `one_bpmn.api.instance_api.complete_task`, which re-checks assignment, the allowed action and write permission.
5. Returns the same shape as `get_document_actions`, plus:
   - `process_status`: the instance status after the engine pass;
   - `messages`: anything the map raised with `frappe.msgprint`, for example a validation step's message.

Example:

```json
{
  "doctype": "Employee Resignation",
  "docname": "HR-RSGN-202610-00003",
  "task_id": "8c1f...",
  "action": "Resubmit Date",
  "values": {"relieving_date": "2026-11-30"},
  "attachments": {"resignation_letter": {"attachment_name": "letter.jpg", "attachment": "<base64>"}}
}
```

A `PermissionError` or `ValidationError` from any step rolls back the whole request, including saved values. `complete_task` does not raise on other engine errors: it marks the instance Errored and returns normally. In that case the values stay saved, and `process_status` is `"Errored"`.

## Letting a step change fields

A map User Task has no form fields. When the user must change fields before an action, the DocType controller declares which fields are editable at the current step. The rule lives on the server, and the endpoint enforces it:

```python
class EmployeeResignation(Document):
	def get_processa_editable_fields(self):
		"""Fields the mobile app may change at the current step of the Processa map."""
		if self.workflow_state in ("Draft", "Pending Relieving Date Correction"):
			return ["resignation_initiation_date", "relieving_date", "resignation_letter"]
		return []
```

Mirror the editability rule the desk form already applies. Return `[]` for steps where nothing may change. Leave the method out if the user only takes actions.

## Moving a process to Processa: checklist

1. **Create endpoint:** only insert the record. Remove any `apply_workflow`, `doc.submit()` or `workflow_state` assignment. The map starts on insert.
2. **Editable fields:** add `get_processa_editable_fields` to the controller only if a step needs field changes.
3. **Actions:** do not add an approve, reject or submit endpoint. The client calls `get_document_actions` and `apply_document_action`.
4. **Old action endpoints:** remove those that called `apply_workflow` for this DocType once no client uses them.
5. **Tests:** test your controller method and your create endpoint. The endpoints here are covered by `one_fm/tests/test_processa_document_actions.py`.

## Do not

- Call `apply_workflow`, `doc.submit()` or `db_set("workflow_state", ...)` to move a Processa-controlled record from request code. Processa's guard blocks submit and cancel, but not workflow actions: `before_workflow_action` never fires in Frappe v15. The record would move while the map keeps waiting.
- Call `one_bpmn.api.instance_api.get_active_bpmn_tasks` from a whitelisted method without checking permission on the record first. It does no document permission check of its own.
- Accept an `instance_name` from the client. Resolve it from the user's actions, as `_find_task` does.
- Hardcode action labels such as "Approve" or "Submit for Review" in an API. The process owner can rename them in the map.
