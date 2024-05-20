import frappe
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from erpnext.buying.utils import update_last_purchase_rate

class CustomPurchaseInvoice(PurchaseInvoice):
    def on_submit(self):
        print('\n\n\n\n>>>> on submit')
        if not frappe.db.get_single_value("Buying Settings", "disable_last_purchase_rate"):
            print('>> update last purchase rate')
            update_last_purchase_rate(self, is_submit=1)
