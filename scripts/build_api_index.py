import os
import ast
import json
import yaml
import argparse
from pathlib import Path

# --- Configuration ---
CORE_APPS = ["frappe", "erpnext", "hrms"]

# List of applications to scan for modules, DocTypes, and hooks.
# 'custom_app' must be included for POC testing.
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
    def get_signature(self, node: ast.FunctionDef) -> str:
            params = []
            for arg in node.args.args:
                if getattr(arg, "annotation", None):
                    try:
                        param_type = ast.unparse(arg.annotation)
                    except Exception:
                        param_type = "any"
                    params.append(f"{arg.arg}: {param_type}")
                else:
                    params.append(arg.arg)
            return f"def {node.name}({', '.join(params)})"
    def __init__(self, bench_path: str):
        self.bench_path = Path(bench_path)
        if not self.bench_path.exists() or not self.bench_path.is_dir():
            raise ValueError(f"Bench path '{self.bench_path}' does not exist or is not a directory.")
        apps_dir = self.bench_path / "apps"
        if not apps_dir.exists() or not apps_dir.is_dir():
            raise ValueError(f"Bench path '{self.bench_path}' does not contain an 'apps' directory.")
        self.index = {
            "version": self.get_version(),
            "modules": {},
            "doctypes": {},
            "hooks": {}
        }

    def get_version(self):
        # Read VERSION file for each app in APPS_TO_INDEX
        versions = []
        for app in APPS_TO_INDEX:
            version_file = self.bench_path / "apps" / app / "VERSION"
            if version_file.exists():
                with open(version_file, "r", encoding="utf-8") as f:
                    version = f.read().strip()
                versions.append(f"{app}-{version}")
            else:
                versions.append(f"{app}-unknown")
        return "-".join(versions)

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

        import traceback
        for py_file in app_base_path.rglob("*.py"):
            if "tests" in py_file.parts:
                continue

            module_path = self.get_module_path(py_file, self.bench_path / "apps")

            try:
                with open(py_file, encoding='utf-8') as f:
                    source = f.read()
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError) as e:
                print(f"[index_app_modules] {type(e).__name__} in {py_file}: {e}")
                continue
            except Exception as e:
                print(f"[index_app_modules] Unexpected error in {py_file}: {e}")
                traceback.print_exc()
                continue

            functions = self.extract_functions(tree)
            classes = self.extract_classes(tree)

            self.index["modules"][module_path] = {
                "functions": functions,
                "classes": classes,
                "whitelisted": any(f.get("whitelisted") for f in functions)
            }

    def extract_functions(self, tree) -> list:
        """Extract function signatures from AST tree"""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                parameters = []
                for arg in node.args.args:
                    if getattr(arg, "annotation", None):
                        try:
                            param_type = ast.unparse(arg.annotation)
                        except Exception:
                            param_type = "any"
                    else:
                        param_type = "any"
                    parameters.append({
                        "name": arg.arg,
                        "type": param_type
                    })
                functions.append({
                    "name": node.name,
                    "signature": self.get_signature(node),
                    "docstring": ast.get_docstring(node) or "",
                    "whitelisted": self.is_whitelisted(node),
                    "parameters": parameters,
                    "line_number": node.lineno
                })
        return functions

    def extract_classes(self, tree) -> list:
        """Extract class definitions and their methods from AST tree."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_methods = []
                for n in node.body:
                    if isinstance(n, ast.FunctionDef):
                        parameters = []
                        for arg in n.args.args:
                            if getattr(arg, "annotation", None):
                                try:
                                    param_type = ast.unparse(arg.annotation)
                                except Exception:
                                    param_type = "any"
                            else:
                                param_type = "any"
                            parameters.append({
                                "name": arg.arg,
                                "type": param_type
                            })
                        class_methods.append({
                            "name": n.name,
                            "signature": self.get_signature(n),
                            "docstring": ast.get_docstring(n) or "",
                            "whitelisted": self.is_whitelisted(n),
                            "parameters": parameters,
                            "line_number": n.lineno
                        })
                classes.append({
                    "name": node.name,
                    "docstring": ast.get_docstring(node) or "",
                    "methods": class_methods
                })
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
        return str(py_file.relative_to(base_path)).replace(os.sep, ".")[:-3]

    def index_doctypes(self):
        """Index DocType schemas from all apps."""
        for app in APPS_TO_INDEX:
            # Only scan apps/app_name/app_name for doctypes, matching module scan logic
            app_path = self.bench_path / "apps" / app / app
            if not app_path.exists():
                continue
            for json_file in app_path.rglob("*.json"):
                try:
                    with open(json_file, encoding='utf-8') as f:
                        try:
                            schema = json.load(f)
                        except Exception:
                            f.seek(0)
                            try:
                                schema = yaml.safe_load(f)
                            except Exception as e_yaml:
                                print(f"[index_doctypes] Error parsing {json_file} as JSON or YAML: {e_yaml}")
                                continue
                    # Only index if the schema has a "doctype" or "istable" key (common in DocType schemas)
                    if not (isinstance(schema, dict) and ("doctype" in schema or "istable" in schema)):
                        continue
                    doctype_name = schema.get("name")
                    controller_path = Path(str(json_file).replace(".json", ".py"))
                    # Determine access level for the TypeScript schema
                    access_level = 'core' if app in CORE_APPS else 'application'
                    self.index["doctypes"][doctype_name] = {
                        "app": app,
                        "schema": {**schema, "accessLevel": access_level}, # merging accessLevel into schema
                        "controller": str(controller_path),
                        "hooks": []  # Intentionally left empty; reserved for future hook extraction logic.
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

    # Validate bench path
    bench_path = Path(args.bench)
    if not bench_path.is_dir():
        print(f"Error: Provided bench path '{bench_path}' does not exist or is not a directory.")
        exit(1)
    # Optionally, check for a file that should exist in a bench, e.g., apps.txt
    if not (bench_path / "sites" / "apps.txt").exists():
        print(f"Warning: '{bench_path}/sites/apps.txt' not found. Are you sure this is a Frappe/ERPNext bench directory?")

    builder = FrappeAPIIndexBuilder(str(bench_path))
    index = builder.build()
    
    print(f"Completed Scan: Found {len(index['modules'])} modules and {len(index['doctypes'])} DocTypes.")
    
    # Save output file
    builder.save(args.output)
    print(f"Index built successfully for {len(APPS_TO_INDEX)} apps.")

if __name__ == "__main__":
    main()