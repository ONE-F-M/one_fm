import { Field } from "@/types";

export async function setupCustomizations(doc, obj) {
  // Supporting old format, will have to refactor later
  let data = doc.data ?? doc;
  if (!data) return;
  if (!data._form_script) return [];
  let actions = [];
  let onChangeFieldMap = {};
  if (Array.isArray(data._form_script)) {
    for (const script of data._form_script) {
      const parsed = await parseScript(script, obj);
      actions = actions.concat(parsed.actions);
      if (parsed.onChange) {
        parseOnChangeFn(onChangeFieldMap, parsed.onChange);
      }
    }
  } else {
    const parsed = await parseScript(data._form_script, obj);
    actions = parsed.actions;
    if (parsed.onChange) {
      parseOnChangeFn(onChangeFieldMap, parsed.onChange);
    }
  }
  data._customActions = actions;
  if (Object.keys(onChangeFieldMap).length) {
    data._customOnChange = onChangeFieldMap;
  }
}

function parseOnChangeFn(fieldMap: object, currentField: object) {
  for (const [key, value] of Object.entries(currentField)) {
    if (!fieldMap[key]) {
      fieldMap[key] = new Set();
    }
    fieldMap[key].add(value);
  }
}

async function parseScript(script, obj) {
  const scriptFn = new Function(script + "\nreturn setupForm")();
  const formScript = await scriptFn(obj);
  return {
    actions: formScript?.actions || [],
    onChange: formScript?.onChange || null,
  };
}

const DOCTYPE_ISSUE = "Doctype Issue";
const PROCESS_ISSUE = "Process Issue";
const CATEGORY_FIELD = "custom_ticket_category";
const REFERENCE_DOCTYPE_FIELD = "custom_reference_doctype";
const PROCESS_FIELD = "custom_process";

/**
 * Desk parity for the Ticket Category / Reference Doctype / Process trio.
 *
 * one_fm/public/js/doctype_js/hd_ticket.js does this on the desk form, but the
 * portal is a standalone SPA and never loads desk client scripts - so picking a
 * reference doctype left Process untouched on the new / edit ticket pages.
 *
 * Mirrors the desk behaviour: on a Doctype Issue the Process options are
 * restricted to the processes that cover the chosen doctype, a process the new
 * doctype does not cover is dropped, and a lone match is selected outright
 * (Process is read-only on a Doctype Issue, so it can only be set this way).
 * Changing the category away from either issue type clears the field that no
 * longer applies.
 */
export async function applyCategoryDependencies(
  fieldname: string,
  doc: any,
  call: Function,
  applyFilters: Function
) {
  if (fieldname === CATEGORY_FIELD) {
    if (doc[CATEGORY_FIELD] !== DOCTYPE_ISSUE) doc[REFERENCE_DOCTYPE_FIELD] = "";
    if (![DOCTYPE_ISSUE, PROCESS_ISSUE].includes(doc[CATEGORY_FIELD])) {
      doc[PROCESS_FIELD] = "";
    }
  }

  if (fieldname !== CATEGORY_FIELD && fieldname !== REFERENCE_DOCTYPE_FIELD) return;
  if (doc[CATEGORY_FIELD] !== DOCTYPE_ISSUE || !doc[REFERENCE_DOCTYPE_FIELD]) return;

  let processes = [];
  try {
    const res = await call("one_fm.overrides.hd_ticket.get_filtered_processes", {
      doctype_name: doc[REFERENCE_DOCTYPE_FIELD],
      is_doctype_related: "Yes",
    });
    // frappe-ui's call unwraps `message`, but tolerate either shape
    processes = Array.isArray(res) ? res : res?.message || [];
  } catch (e) {
    console.error("Failed to fetch processes for the reference doctype", e);
    return;
  }
  if (!processes.length) return;

  // applyFilters clears the field it narrows, so remember the current process
  // and put it back if the new doctype still covers it
  const current = doc[PROCESS_FIELD];
  applyFilters?.(PROCESS_FIELD, processes);

  if (processes.length === 1) {
    doc[PROCESS_FIELD] = processes[0];
  } else if (current && processes.includes(current)) {
    doc[PROCESS_FIELD] = current;
  }
}

export function handleSelectFieldUpdate(
  f: Field,
  fieldname: string,
  filters: any,
  doc: any,
  oldDoc: any
) {
  if (!filters || !filters.length) {
    f.options = oldDoc.find((f) => f.fieldname === fieldname).options;
    f.disabled = true;
  } else {
    f.options = filters.join("\n");
    f.disabled = false;
  }
  // reset dependent field
  doc[fieldname] = "";
}

export function handleLinkFieldUpdate(
  f: Field,
  fieldname: string,
  filters: any,
  doc: any,
  oldDoc: any
) {
  if (!filters || !filters.length) {
    f.link_filters = oldDoc.find((f) => f.fieldname === fieldname).link_filters;
    f.disabled = true;
    return;
  }
  f.link_filters = JSON.stringify([[f.options, "name", "in", filters]]);
  f.disabled = false;

  // reset dependent field
  doc[fieldname] = "";
}

//
export function parseField(field, doc) {
  return {
    display_via_depends_on: evaluateDependsOnValue(field?.depends_on, doc),
    ...field,
    required:
      field.required ||
      (field.mandatory_depends_on &&
        evaluateDependsOnValue(field.mandatory_depends_on, doc)),
    filters: field.link_filters && JSON.parse(field.link_filters),
    disabled: field.disabled,
    readonly:
      field.readonly ||
      Boolean(field.read_only) ||
      (field.read_only_depends_on &&
        evaluateDependsOnValue(field.read_only_depends_on, doc)),
  };
}
export function evaluateDependsOnValue(expression, doc) {
  if (!expression) return true;
  let out = null;
  if (expression.substr(0, 5) == "eval:") {
    try {
      out = _eval(expression.substr(5), { doc });
    } catch (e) {
      out = true;
    }
  } else if (expression.substr(0, 4) == "doc.") {
    out = doc[expression.substr(4)];
  } else {
    let value = doc[expression];
    if (Array.isArray(value)) {
      out = !!value.length;
    } else {
      out = !!value;
    }
  }
  return out;
}
function _eval(code, context = {}) {
  let variable_names = Object.keys(context);
  let variables = Object.values(context);
  code = `let out = ${code}; return out`;
  try {
    let expression_function = new Function(...variable_names, code);
    return expression_function(...variables);
  } catch (error) {
    console.log("Error evaluating the following expression:");
    console.error(code);
    throw error;
  }
}
