import { Field } from "@/types";
import { call } from "frappe-ui";

/**
 * `fetch_from` support for the portal forms.
 *
 * The desk implements this in `frappe/form/controls/link.js` (`add_fetch`), but
 * the helpdesk portal is a standalone frappe-ui SPA and never loads that code.
 * The server still fetches on save (`base_document.set_fetch_from_value`), so
 * this only mirrors that behaviour live in the form.
 */

interface FetchTarget {
  // field on HD Ticket that receives the fetched value
  fieldname: string;
  // field on the linked doctype the value comes from
  sourceFieldname: string;
  fetchIfEmpty: boolean;
}

// how deep a chain of fetch_from -> link -> fetch_from is followed
const MAX_FETCH_DEPTH = 5;

/**
 * Map of link fieldname -> fields that pull their value from it.
 *
 * Mirrors `Meta.get_fields_to_fetch`: the link field is the first segment of
 * `fetch_from` and the source field is the last.
 */
export function getFetchMap(fields: Field[] = []): Record<string, FetchTarget[]> {
  const map: Record<string, FetchTarget[]> = {};

  for (const field of fields) {
    const fetchFrom = field?.fetch_from;
    if (!fetchFrom || !fetchFrom.includes(".")) continue;

    const parts = fetchFrom.split(".");
    const linkFieldname = parts[0];
    const sourceFieldname = parts[parts.length - 1];
    if (!linkFieldname || !sourceFieldname) continue;

    (map[linkFieldname] ||= []).push({
      fieldname: field.fieldname,
      sourceFieldname,
      fetchIfEmpty: Boolean(field.fetch_if_empty),
    });
  }

  return map;
}

/**
 * Populate every field that fetches from `changedFieldname`, then follow the
 * chain in case a fetched field is itself a link with dependents.
 *
 * `doc` must be reactive - values are assigned in place.
 */
export async function applyFetchFrom(
  fields: Field[],
  doc: Record<string, any>,
  changedFieldname: string,
  depth = 0
): Promise<void> {
  if (depth >= MAX_FETCH_DEPTH) return;

  const targets = getFetchMap(fields)[changedFieldname];
  if (!targets?.length) return;

  const linkField = fields.find((f) => f.fieldname === changedFieldname);
  const doctype = linkField?.options;
  const value = doc[changedFieldname];

  // fetch_if_empty fields keep whatever the user typed
  const pending = targets.filter(
    (t) => !t.fetchIfEmpty || !doc[t.fieldname]
  );
  if (!pending.length) return;

  let values: Record<string, any> = {};

  if (value && doctype) {
    try {
      // get_value goes through get_list, so read permissions still apply
      values =
        (await call("frappe.client.get_value", {
          doctype,
          filters: value,
          fieldname: JSON.stringify([
            ...new Set(pending.map((t) => t.sourceFieldname)),
          ]),
        })) || {};
    } catch (e) {
      console.error(`Could not fetch values from ${doctype} ${value}`, e);
      return;
    }
  }

  // link cleared, or the source doc had nothing -> clear the dependents
  for (const target of pending) {
    doc[target.fieldname] = values[target.sourceFieldname] ?? "";
  }

  await Promise.all(
    pending.map((target) =>
      applyFetchFrom(fields, doc, target.fieldname, depth + 1)
    )
  );
}
