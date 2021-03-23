import frappe
from frappe import _
from one_fm.api.doc_methods.payroll_entry import get_basic_salary
from one_fm.api.notification import create_notification_log


def salary_slip_before_submit(doc, method):
	basic_salary = get_basic_salary(doc.employee)
	
	# As per Kuwaiti law, 90% of WP salary has to be paid to an employee after factoring in deductions
	minimum_payable_salary = 0.9 * basic_salary

	if doc.net_pay < minimum_payable_salary:
		notify_payroll(doc)
		frappe.throw(_("Total deduction amount exceeds the permissible limit in Salary Slip for {}".format(doc.employee+":"+doc.employee_name)))
	# total_deduction_amount = 0.00
	# for deduction in doc.deductions:
	# 	if not deduction.do_not_include_in_total:
	# 		total_deduction_amount += deduction.amount
	
	# total_deduction_amount += doc.total_loan_repayment


def notify_payroll(doc):
	email = frappe.get_value("HR Settings", "HR Settings", "payroll_notifications_email")
	subject = _("Urgent Attention Needed: Issues with maximum deduction in Payroll")
	message = _("Total deduction amount exceeds the permissible limit in Salary Slip for {}".format(doc.employee+":"+doc.employee_name))
	create_notification_log(subject,message,[email], doc)