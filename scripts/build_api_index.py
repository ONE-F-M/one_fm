import os
import ast
import json
import argparse
from pathlib import Path

# --- Configuration ---
# List of applications to scan for modules, DocTypes, and hooks.
# 'custom_app' must be included for POC testing.
#
# NOTE: This script is intended to be run INSIDE the Frappe Bench environment (Producer).
# After generation, you MUST copy/move the resulting frappe-api-index.json to the Open SWE agent environment (Consumer),
# e.g., using a CI/CD step or manual copy:
#   cp /home/frappe/frappe-bench/frappe-api-index.json /path/to/open-swe/frappe-api-index.json
# Or upload to cloud storage and download in the agent container.
APPS_TO_INDEX = [
    # "frappe",
    # "erpnext",
    # "hrms",
    # "helpdesk",
    # "lending",
    # "lms",
    # "mobile_app_ionic",
    "one_fm",
    # "one_fm_google_integration",
    # "one_fm_password_management",
    # "onefm_mcp",
    # "onefm_sso",
    # "ONEFM_Landing_page",
    # "frappe_mcp_server",
    # "payments",
    # "tools_helper",
    # "twilio_integration",
    # "wiki",
] 

class FrappeAPIIndexBuilder:
    def __init__(self, bench_path: str):
        self.bench_path = Path(bench_path)
        self.index = {
            "version": self.get_version(),
            "modules": {},
            "doctypes": {},
            "hooks": {}
        }

    def get_version(self):
        # In a real setup, this would read frappe/VERSION file or similar.
        return "frappe-15-erpnext-15"

    def build(self):
        """Build complete API index by iterating over all configured apps."""
        print("Starting API Index Build...")
        
        for app_name in APPS_TO_INDEX:
            self.index_app_modules(app_name)
        
        self.index_doctypes()
        self.index_hook_types()
        
        return self.index

    def index_app_modules(self, app_name: str):
        """Index all Python modules (functions and classes) within a given app."""
        # Standard Frappe path structure is apps/app_name/app_name
        app_base_path = self.bench_path / "apps" / app_name / app_name
        
        if not app_base_path.exists():
            print(f"Warning: Module path not found for app '{app_name}'. Skipping.")
            return

        for py_file in app_base_path.rglob("*.py"):
            if "tests" in str(py_file):
                continue
                
            # The module path should be relative to the bench apps folder 
            # (e.g., 'frappe.utils.html_utils' or 'custom_app.api.my_methods')
            module_path = str(py_file.relative_to(self.bench_path / "apps")).replace(os.sep, ".")[:-3]

            functions = self.extract_functions(py_file)
            classes = self.extract_classes(py_file)
            
            self.index["modules"][module_path] = {
                "functions": functions,
                "classes": classes,
                "whitelisted": any(f.get("whitelisted") for f in functions)
            }

    def extract_functions(self, file_path: Path) -> list:
        """Extract function signatures using AST with error handling"""
        functions = []
        try:
            with open(file_path, encoding='utf-8') as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # We only extract parameters as basic names here for simplicity
                    params = [arg.arg for arg in node.args.args]
                    
                    functions.append({
                        "name": node.name,
                        # Use ast.unparse for a clean signature string
                        "signature": ast.unparse(node), 
                        "docstring": ast.get_docstring(node) or "",
                        "whitelisted": self.is_whitelisted(node),
                        "parameters": [{"name": p, "type": "any"} for p in params], # Simplified Parameter structure
                        "line_number": node.lineno
                    })
        except Exception as e:
            print(f"[extract_functions] Error in {file_path}: {e}")
        return functions

    def extract_classes(self, file_path: Path) -> list:
        """Extract class definitions and their methods."""
        classes = []
        try:
            with open(file_path, encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            # Extract all functions first to reference them as methods later
            all_functions = self.extract_functions(file_path)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Find functions that belong to this class
                    class_methods = [
                        f for f in all_functions 
                        if f["name"] in [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    ]
                    
                    classes.append({
                        "name": node.name,
                        "docstring": ast.get_docstring(node) or "",
                        "methods": class_methods
                    })
        except Exception as e:
            print(f"[extract_classes] Error in {file_path}: {e}")
        return classes

    def is_whitelisted(self, node: ast.FunctionDef) -> bool:
        """Checks if a function has a @frappe.whitelist decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                func = decorator.func
                # Handles @frappe.whitelist()
                if (isinstance(func, ast.Attribute) and func.attr == 'whitelist'):
                    return True
                # Handles @whitelist() (if imported directly)
                elif (isinstance(func, ast.Name) and func.id == 'whitelist'):
                    return True
            # Handles @frappe.whitelist or @whitelist (no call)
            elif isinstance(decorator, ast.Attribute) and decorator.attr == 'whitelist':
                return True
            elif isinstance(decorator, ast.Name) and decorator.id == 'whitelist':
                return True
        return False

    def extract_params(self, node: ast.FunctionDef) -> list:
        # Returns basic argument names for simplicity
        return [arg.arg for arg in node.args.args]

    def get_module_path(self, py_file: Path, base_path: Path) -> str:
        # NOTE: This method is no longer used due to the refactor in index_app_modules
        return str(py_file.relative_to(base_path)).replace(os.sep, ".")[:-3]

    def index_doctypes(self):
        """Index DocType schemas from all apps."""
        for app in APPS_TO_INDEX:
            # Only scan apps/app_name/app_name for doctypes, matching module scan logic
            app_path = self.bench_path / "apps" / app / app / app
            if not app_path.exists():
                continue
            for json_file in app_path.rglob("*.json"):
                # Check for doctype structure (e.g., app/doctype/doctype_name/doctype_name.json)
                if "doctype" not in str(json_file):
                    continue
                try:
                    with open(json_file, encoding='utf-8') as f:
                        schema = json.load(f)
                    doctype_name = schema.get("name")
                    controller_path = Path(str(json_file).replace(".json", ".py"))
                    # Determine access level for the TypeScript schema
                    access_level = 'core' if app in ["frappe", "hrms"] else 'application'
                    self.index["doctypes"][doctype_name] = {
                        "app": app,
                        "schema": {**schema, "accessLevel": access_level}, # Merging accessLevel into schema
                        "controller": str(controller_path),
                        "hooks": []
                    }
                except Exception as e:
                    print(f"[index_doctypes] Error in {json_file}: {e}")

    def index_hook_types(self):
        """Define the standard hook types the agent needs to reference."""
        # This is a hardcoded index of hook patterns expected by the agent.
        self.index["hooks"] = {
            "doc_events": {
                "signature": "{DocType: {event: method_path}}",
                "description": "Hooks triggered by document lifecycle events (on_submit, before_save, etc.).",
                "examples": [
                    'doc_events = { "Sales Invoice": { "on_submit": "custom_app.api.on_invoice_submit" } }'
                ]
            },
            "override_doctype_class": {
                "signature": "{DocType: [mixin_class_paths]}",
                "description": "Allows extending a DocType controller with mixin classes.",
                "examples": [
                    'override_doctype_class = { "Customer Asset": ["custom_app.overrides.CustomerAssetMixin"] }'
                ]
            }
        }

    def save(self, output_path: str):
        """Save the index dictionary to the specified JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2)
            print(f"Success: Index saved to {output_path}")
        except Exception as e:
            print(f"[save] Error saving index to {output_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Build Frappe/ERPNext API index.")
    # Set default bench path to the expected environment path for production
    parser.add_argument('--bench', type=str, default=str(Path(__file__).resolve().parents[3]), help="Path to Frappe/ERPNext bench directory")
    parser.add_argument('--output', type=str, default=str(Path(__file__).parent / "frappe-api-index.json"), help="Output JSON file path (default: same directory as this script)")
    args = parser.parse_args()

    builder = FrappeAPIIndexBuilder(args.bench)
    index = builder.build()
    
    print(f"Completed Scan: Found {len(index['modules'])} modules and {len(index['doctypes'])} DocTypes.")
    
    # Save output file
    builder.save(args.output)
    print(f"Index built successfully for {len(APPS_TO_INDEX)} apps.")

if __name__ == "__main__":
    main()