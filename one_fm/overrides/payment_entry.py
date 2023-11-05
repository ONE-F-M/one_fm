import frappe,erpnext



def get_valid_reference_doctypes_(self):
		if self.party_type == "Customer":
			return ("Sales Order", "Sales Invoice", "Journal Entry", "Dunning")
		elif self.party_type == "Supplier":
			return ("Purchase Order", "Purchase Invoice", "Journal Entry")
		elif self.party_type == "Shareholder":
			return ("Journal Entry",)
		elif self.party_type == "Employee":
			return ("Expense Claim", "Journal Entry", "Employee Advance", "Gratuity")

def add_party_gl_entries_(self, gl_entries):
    if self.party_account:
        if self.payment_type == "Receive":
            against_account = self.paid_to
        else:
            against_account = self.paid_from

        party_gl_dict = self.get_gl_dict(
            {
                "account": self.party_account,
                "party_type": self.party_type,
                "party": self.party,
                "against": against_account,
                "account_currency": self.party_account_currency,
                "cost_center": self.cost_center,
            },
            item=self,
        )

        dr_or_cr = (
            "credit" if erpnext.get_party_account_type(self.party_type) == "Receivable" else "debit"
        )

        for d in self.get("references"):
            cost_center = self.cost_center
            if d.reference_doctype == "Sales Invoice" and not cost_center:
                cost_center = frappe.db.get_value(d.reference_doctype, d.reference_name, "cost_center")
            gle = party_gl_dict.copy()
            gle.update(
                {
                    "against_voucher_type": d.reference_doctype,
                    "against_voucher": d.reference_name,
                    "cost_center": cost_center,
                }
            )

            allocated_amount_in_company_currency = self.calculate_base_allocated_amount_for_reference(d)

            gle.update(
                {   
                    
                    dr_or_cr + "_in_account_currency": d.allocated_amount,
                    dr_or_cr: allocated_amount_in_company_currency,
                }
            )

            gl_entries.append(gle)

        if self.unallocated_amount:
            try:
                customer_advance_account=frappe.get_value('Accounts Additional Settings',None,'customer_advance_account')                    
            except:
                frappe.log_error("Error while fetching advance account",frappe.get_traceback())
                frappe.throw("An Error occured while fetching advance account, Please review the error logs")
            exchange_rate = self.get_exchange_rate()
            base_unallocated_amount = self.unallocated_amount * exchange_rate

            gle = party_gl_dict.copy()
            if customer_advance_account:
                gle.update(
                    {   
                        "account": customer_advance_account,
                        "party_type": self.party_type,
                        "party": self.party,
                        "against": against_account,
                        "account_currency": self.party_account_currency,
                        "cost_center": self.cost_center,
                        dr_or_cr + "_in_account_currency": self.unallocated_amount,
                        dr_or_cr: base_unallocated_amount,
                    }
                )
            else:
                gle.update(
                    {   
                        
                        dr_or_cr + "_in_account_currency": self.unallocated_amount,
                        dr_or_cr: base_unallocated_amount,
                    }
                )
                

            gl_entries.append(gle)