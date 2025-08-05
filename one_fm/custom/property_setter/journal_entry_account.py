def get_journal_entry_account_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Journal Entry Account",
            "property": "options",
            "property_type": "Text",
            "field_name": "reference_type",
            "value": "\nSales Invoice\nPurchase Invoice\nJournal Entry\nSales Order\nPurchase Order\nExpense Claim\nAsset\nLoan\nPayroll Entry\nEmployee Advance\nExchange Rate Revaluation\nInvoice Discounting\nRecruitment Trip Request"
        }
    ]
