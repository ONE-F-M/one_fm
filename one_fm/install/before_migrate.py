import os, importlib, frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


FRAPPE_BENCH_PATH = frappe.utils.get_bench_path()


def create_custom_fields():
    """Create or update custom fields before migration."""
    print("Migrating custom fields before any action for ONE FM")
    CUSTOM_FIELDS_PATH = os.path.join(FRAPPE_BENCH_PATH, "apps/one_fm/one_fm/custom/custom_field")

    if not os.path.exists(CUSTOM_FIELDS_PATH):
        raise FileNotFoundError(f"Path does not exist: {CUSTOM_FIELDS_PATH}")

    py_files = [
        f for f in os.listdir(CUSTOM_FIELDS_PATH)
        if f.endswith(".py") and f != "__init__.py"
    ]

    for py_file in py_files:
        module_name = py_file[:-3]
        import_path = f"one_fm.custom.custom_field.{module_name}"
        module = importlib.import_module(import_path)
        func_name = f"get_{module_name}_custom_fields"

        if hasattr(module, func_name):
            func = getattr(module, func_name)
            custom_fields = func()
            print(f"Custom fields from {py_file}:")
            for doctype, fields in custom_fields.items():
                for df in fields:
                    create_custom_field(doctype, df, ignore_validate=True)
                    frappe.db.commit()
        else:
            print(f"Function {func_name} not found in {py_file}")
    
