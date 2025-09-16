<general_rules>
This is a Frappe/ERPNext custom application for One Facility Management (one_fm). Always prioritize simple, working solutions over complex implementations.

NAMING CONVENTIONS:
- DocTypes: Title Case, singular form, spaces between words (e.g., "Sales Order", "Purchase Receipt")
- Child tables: Parent DocType + relation (e.g., "Sales Order Item")
- Field labels: Title Case
- Field names: snake_case version of labels ("First Name" → first_name)
- Link fields: Match linked DocType in snake_case (Employee → employee)
- Document variables: snake_case of DocType (sales_order = frappe.get_doc("Sales Order", "SO-0001"))

CODE STYLE:
- Always use double quotes for strings in Python and JavaScript
- Use tabs for indentation (Frappe legacy standard)
- Prefer frappe.qb (Query Builder) over raw SQL
- Wrap all user-facing strings in _("") for Python, __("") for JavaScript
- Import frappe modules at top of files: import frappe
- Use frappe.throw() for error handling with proper titles
- Follow Python PEP 8 for general code style (except indentation)

FUNCTION CREATION RULES:
- Before creating new utility functions, always first search in the one_fm/api/ directory to see if one exists
- If no existing function found, search in one_fm/utils.py for similar functionality
- Create new utility functions in one_fm/utils.py or create new files in one_fm/api/ for whitelisted endpoints
- Place business logic in DocType controllers (.py files) rather than utilities when specific to a DocType
- Use existing Frappe framework functions where possible before creating custom ones

DEVELOPMENT PATTERNS:
- Always check existing functions before creating new ones
- Use frappe.get_doc() for single document operations
- Use frappe.get_all() or frappe.db.sql() for bulk operations
- Keep client scripts (.js files) minimal - focus on form interactions only
- Use proper permission checking with frappe.has_permission()
- Follow the validate() → before_save() → after_insert() → on_submit() lifecycle
- Create fixtures for reference data in one_fm/fixtures/
- Use print statements for debugging with console output
- Read error messages carefully - Frappe errors are usually descriptive
</general_rules>

<repository_structure>
ONE FM is a Frappe/ERPNext custom application with the following structure:

one_fm/
├── one_fm/                     # Main application module
│   ├── hooks.py                # App configuration, event hooks, scheduled tasks
│   ├── modules.txt             # Module definitions (14 modules: One Fm, GRD, Operations, etc.)
│   ├── patches.txt             # Database migration scripts
│   ├── api/                    # Whitelisted API endpoints (@frappe.whitelist())
│   ├── utils.py                # Common utility functions
│   ├── accommodation/          # Accommodation management module
│   ├── developer/             # Development tools and debugging utilities
│   ├── fleet_management/      # Vehicle and fleet management
│   ├── grd/                   # Guard and security operations
│   ├── gsd/                   # General services department
│   ├── hiring/                # HR and recruitment processes
│   ├── legal/                 # Legal document management
│   ├── operations/            # Core operations management
│   ├── paci/                  # PACI integration and processes
│   ├── purchase/              # Procurement and purchasing
│   ├── subcontract/           # Subcontractor management
│   ├── uniform_management/    # Uniform distribution and tracking
│   ├── public/                # Static assets (CSS, JS, images)
│   ├── templates/             # Jinja2 templates
│   ├── fixtures/              # Default data and configurations
│   ├── patches/               # Version-specific database patches
│   └── tests/                 # Main test suite
├── job_applicant_magic_link/   # Vue.js frontend app for job applications
│   ├── src/                   # Vue.js source files
│   ├── package.json           # Node.js dependencies and build scripts
│   ├── vite.config.js         # Vite build configuration
│   └── tailwind.config.js     # Tailwind CSS configuration
├── setup.py                   # App installation and metadata
├── requirements.txt           # Python dependencies
├── hooks.py → one_fm/hooks.py # App hooks configuration
└── .github/workflows/         # CI/CD pipelines for different branches

KEY MODULES:
- One Fm: Core application functionality
- Operations: Daily operations and scheduling
- GRD: Guard duty and security management
- Hiring: Recruitment and employee onboarding
- Fleet Management: Vehicle tracking and maintenance
- Uniform Management: Employee uniform distribution
- Developer: Internal development tools and utilities

ARCHITECTURE PATTERNS:
- Each DocType has three files: .py (controller), .json (metadata), .js (client scripts)
- Business logic resides in DocType controllers
- API endpoints are whitelisted functions in api/ directory
- Client scripts handle form interactions only
- Custom reports and dashboards in individual module directories
- Patches handle database migrations between versions
</repository_structure>

<dependencies_and_installation>
SYSTEM REQUIREMENTS:
- Frappe Framework v15 (version-15 branch)
- ERPNext v15 (compatible version)
- Python 3.8+ (3.11 recommended)
- Node.js 16+ for frontend building
- MariaDB 10.6+ database
- Redis for caching and background jobs

PYTHON DEPENDENCIES (requirements.txt):
- Core: frappe, erpnext
- External APIs: twilio, firebase-admin, google-cloud-* packages
- Data Processing: pandas, datefinder, html2text
- AI/ML: llama_index, openai
- Security: bleach, paramiko
- Utilities: qrcode, gspread, deep-translator

INSTALLATION COMMANDS:
```bash
# Install app in development mode
bench get-app one_fm https://github.com/ONE-F-M/one_fm
bench --site [site-name] install-app one_fm

# Install Python dependencies
bench setup requirements

# Build frontend assets (for job_applicant_magic_link Vue app)
cd job_applicant_magic_link && npm install && npm run build

# Run database migrations
bench --site [site-name] migrate

# Start development server
bench start
```

DEVELOPMENT SETUP:
```bash
# Enable developer mode
bench --site [site-name] set-config developer_mode 1

# Clear cache after changes
bench --site [site-name] clear-cache

# Build specific app assets
bench build --app one_fm
```

FRONTEND DEVELOPMENT (job_applicant_magic_link):
```bash
cd job_applicant_magic_link
npm install          # Install Vue.js dependencies
npm run dev          # Start development server
npm run build        # Build for production
```

BUILD SCRIPTS:
- No specific linting scripts configured in main app
- Vue.js app uses Prettier with configuration in .prettierrc.json
- Standard Frappe framework commands for building and testing
- CI/CD pipelines handle automated building and deployment
</dependencies_and_installation>

<testing_instructions>
TESTING FRAMEWORK:
- Python unittest for backend testing
- Tests located in individual DocType folders as test_[doctype_name].py
- Main test suite in one_fm/tests/ directory
- Core test files include: test_user.py, test_shift_assignment.py, test_purchase_order.py

RUNNING TESTS:
```bash
# Run all tests for the app
bench --site [site-name] run-tests --app one_fm

# Run specific test module
bench --site [site-name] run-tests --app one_fm --module test_user

# Run tests with coverage
bench --site [site-name] run-tests --app one_fm --coverage
```

TEST STRUCTURE REQUIREMENTS:
```python
import frappe
import unittest

class TestYourDocType(unittest.TestCase):
    def setUp(self):
        # Create test data - use ignore_permissions=True for setup
        pass
    
    def test_validation_logic(self):
        # Test DocType validation and business rules
        doc = frappe.get_doc({
            "doctype": "Your DocType",
            # Test data
        })
        doc.insert(ignore_permissions=True)
        self.assertTrue(doc.name)
    
    def tearDown(self):
        # CRITICAL: Always clean up test data
        frappe.db.rollback()
```

TESTING FOCUS AREAS:
1. DocType Controllers:
   - Validation logic in validate() method
   - Business rules in before_save(), on_submit()
   - Field calculations and auto-population
   - Error handling with frappe.throw()

2. API Endpoints:
   - Permission validation with frappe.has_permission()
   - Input sanitization and validation
   - Proper return data structure
   - Error responses with meaningful messages

3. Module-Specific Logic:
   - Operations: Shift assignments and scheduling
   - GRD: Security operations and reporting
   - Hiring: Recruitment workflow validation
   - Fleet Management: Vehicle tracking accuracy
   - Uniform Management: Distribution tracking

4. Integration Testing:
   - External API integrations (Twilio, Firebase, Google Cloud)
   - Database query performance
   - Background job execution
   - Multi-module workflow validation

PRE-COMMIT CHECKLIST:
- All tests pass: bench --site [site-name] run-tests --app one_fm
- No JavaScript console errors
- Python code follows PEP 8 (except tabs for indentation)
- All user-facing strings are translatable
- Proper error handling in place
- Database migrations tested if schema changes made

DEBUGGING TECHNIQUES:
- Use bench --site [site-name] console for interactive debugging
- Enable developer mode for detailed error traces
- Monitor bench start output for real-time logs
- Use print() statements in controllers for debugging
- Check browser console for JavaScript errors
- Verify permissions and user roles for access issues
</testing_instructions>

<pull_request_formatting>
Pull requests must follow the template structure defined in pull_request_template.md:

REQUIRED SECTIONS:
- **Type Classification**: Mark as Feature, Chore, or Bug with checkboxes
- **Clear Description**: Concise explanation of the change
- **Solution Description**: Detailed code changes for reviewers
- **Business Logic**: Indicate if DocType business logic is involved
- **Areas Affected**: List all areas impacted by changes
- **Testing Verification**: Confirm testing with existing and new data
- **Browser Testing**: Specify which browsers were tested (Chrome, Safari, Firefox)

SPECIAL CONSIDERATIONS:
- **Child Table Creation**: If child tables created, confirm attachment testing
- **Custom Field Deletion**: If custom fields deleted, confirm delete patch written
- **Patch Requirements**: If database patches required, confirm patch testing
- **Behavior Changes**: Explicitly state if existing feature behavior changes
- **Screenshots**: Include UI screenshots for frontend changes

TITLE FORMAT:
Use descriptive titles that clearly indicate the change type and affected area:
- Feature: "Add employee shift scheduling automation"
- Bug: "Fix salary calculation error in payroll processing" 
- Chore: "Update dependencies for security patches"

CHECKLIST REQUIREMENTS:
All applicable checkboxes in the template must be marked before approval. Reviewers will verify:
- Proper testing coverage
- Documentation updates if needed
- No breaking changes to existing functionality
- Performance impact assessment
- Security considerations addressed
</pull_request_formatting>