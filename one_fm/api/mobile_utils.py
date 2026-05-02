"""
one_fm.api.mobile_utils
=======================
Shared utilities for mobile-facing Frappe APIs.

The Problem
-----------
Frappe behaves differently depending on the authentication method:

    Auth Method    | POST body goes to       | GET query goes to
    ---------------|-------------------------|-------------------
    Cookie/Session | frappe.form_dict        | frappe.form_dict
    Token (mobile) | nowhere (raw bytes only)| frappe.request.args ONLY

This means that every API function that is called by the mobile app
with `Authorization: token key:secret` will receive None for all
parameters unless it explicitly reads from the raw request body or
request.args.

Solution
--------
Use `get_param(key)` or `get_all_params()` instead of accessing
frappe.form_dict directly. These functions check all possible sources
in the correct priority order for both auth methods.

Usage
-----
    from one_fm.api.mobile_utils import get_param, get_all_params

    @frappe.whitelist()
    def my_api(employee_id=None, data=None, **kwargs):
        employee_id = get_param('employee_id', employee_id)
        ...
"""

import json
import frappe
from urllib.parse import parse_qs


def _get_raw_body_params():
    """Parse the raw HTTP request body into a dict.
    Supports application/json and application/x-www-form-urlencoded.
    Called once and cached per request.
    """
    cache_key = '_mobile_utils_body_params'
    if hasattr(frappe.local, cache_key):
        return getattr(frappe.local, cache_key)

    result = {}
    try:
        if hasattr(frappe, 'request'):
            body = frappe.request.get_data(as_text=True)
            if body:
                # Try JSON first
                try:
                    parsed = json.loads(body)
                    if isinstance(parsed, dict):
                        result.update(parsed)
                except (json.JSONDecodeError, ValueError):
                    # Fall back to URL-encoded (key=val&key2=val2)
                    parsed_qs = parse_qs(body, keep_blank_values=True)
                    for k, v in parsed_qs.items():
                        result[k] = v[0] if len(v) == 1 else v

                # Handle nested 'data' JSON string (e.g. data={"key":"val"})
                if 'data' in result and isinstance(result['data'], str):
                    try:
                        nested = json.loads(result['data'])
                        if isinstance(nested, dict):
                            # Nested data fills in missing keys only
                            for k, v in nested.items():
                                if k not in result or result[k] is None:
                                    result[k] = v
                    except (json.JSONDecodeError, ValueError):
                        pass
    except Exception:
        pass

    setattr(frappe.local, cache_key, result)
    return result


def get_param(key, explicit_value=None, default=None):
    """
    Get a single request parameter from any source, in priority order:
    1. explicit_value  — the function argument (highest priority)
    2. frappe.form_dict — populated by cookie/session auth for both GET and POST
    3. frappe.request.args — GET query string under token auth
    4. raw request body — POST body under token auth (JSON or form-encoded)
    5. default

    Args:
        key (str): Parameter name to look up.
        explicit_value: The value received as a function argument (may be None).
        default: Fallback value if not found anywhere.

    Returns:
        The resolved value, or default.

    Example:
        @frappe.whitelist()
        def my_api(employee_id=None, **kwargs):
            employee_id = get_param('employee_id', employee_id)
    """
    # 1. Explicit function argument (Frappe populates these for session auth)
    if explicit_value is not None:
        return explicit_value

    # 2. frappe.form_dict (session/cookie auth, always populated)
    form_val = frappe.form_dict.get(key)
    if form_val is not None:
        return form_val

    # 3. request.args (GET query string under token auth)
    if hasattr(frappe, 'request') and hasattr(frappe.request, 'args'):
        args_val = frappe.request.args.get(key)
        if args_val is not None:
            return args_val

    # 4. Raw body (POST under token auth)
    body_params = _get_raw_body_params()
    body_val = body_params.get(key)
    if body_val is not None:
        return body_val

    return default


def get_all_params(*keys, **explicit_values):
    """
    Resolve multiple parameters at once. Returns a dict.

    Args:
        *keys: Parameter names to resolve (uses get_param with no explicit value).
        **explicit_values: key=value pairs for parameters that have explicit values.

    Example:
        params = get_all_params(
            'resignation_id', 'new_date',
            employee_id=employee_id,
            attachment=attachment,
        )
        employee_id = params['employee_id']
        resignation_id = params['resignation_id']
    """
    result = {}
    # Keys with explicit values
    for k, v in explicit_values.items():
        result[k] = get_param(k, v)
    # Keys without explicit values
    for k in keys:
        if k not in result:
            result[k] = get_param(k)
    return result
