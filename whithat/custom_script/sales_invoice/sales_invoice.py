import frappe
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.controllers.print_settings import set_print_templates_for_item_table, set_print_templates_for_taxes
from frappe.utils import flt


class CustomSalesInvoice(SalesInvoice):
    def validate(self):
        super(CustomSalesInvoice, self).validate()
        if self.is_new():
            customer = frappe.get_doc('Customer', self.customer)
            if customer.sales_team:
                for i in customer.sales_team:
                    allocated_amount = float((self.amount_eligible_for_commission * i.allocated_percentage) / 100.0) if i.allocated_percentage else 0.00
                    incentives = float((allocated_amount * float(i.commission_rate)) / 100.0) if i.commission_rate and allocated_amount else 0.00
                    self.append("sales_team", {
                        "sales_person": i.sales_person,
                        "allocated_percentage": i.allocated_percentage,
                        "commission_rate": i.commission_rate,
                        "allocated_amount": allocated_amount,
                        "incentives": incentives
                    })

        if not self.custom_subscription:
            for i in self.items:
                if i.custom_subscription:
                    self.custom_subscription = i.custom_subscription
                    
    def on_submit(self):
        super(CustomSalesInvoice, self).on_submit()
        if self.is_return and self.custom_subscription:
            SDoc = frappe.get_doc('Subscription', self.custom_subscription)
            print('sdoc', SDoc)
            SDoc.append('custom_credit_notes', {
                'againts_sales_invoice': self.return_against,
                'credit_note': self.name
            })
            SDoc.save()
            SDoc.reload()


    def before_print(self, settings=None):
        print('\n >>>>>>>>>>>>>>>>>>>>>>>> before_print >>> \n')

        if self.get("group_same_items"):
            self.group_similar_items()
        if self.get("custom_group_same_subscription_plan"):
            self.group_similar_production_plan()

        df = self.meta.get_field("discount_amount")
        if self.get("discount_amount") and hasattr(self, "taxes") and not len(self.taxes):
            df.set("print_hide", 0)
            self.discount_amount = -self.discount_amount
        else:
            df.set("print_hide", 1)

        set_print_templates_for_item_table(self, settings)
        set_print_templates_for_taxes(self, settings)

    def group_similar_production_plan(self):
        group_item_qty = {}
        group_item_amount = {}
        # to update serial number in print
        count = 0

        for item in self.items:
            group_item_qty[item.custom_subscription_plan] = group_item_qty.get(item.custom_subscription_plan, 0) + item.qty
            group_item_amount[item.custom_subscription_plan] = group_item_amount.get(item.custom_subscription_plan, 0) + item.amount

        duplicate_list = []
        for item in self.items:
            if item.custom_subscription_plan in group_item_qty:
                count += 1
                item.qty = group_item_qty[item.custom_subscription_plan]
                item.amount = group_item_amount[item.custom_subscription_plan]

                if item.qty:
                    item.rate = flt(flt(item.amount) / flt(item.qty), item.precision("rate"))
                else:
                    item.rate = 0

                item.idx = count
                del group_item_qty[item.custom_subscription_plan]
            else:
                duplicate_list.append(item)
        for item in duplicate_list:
            self.remove(item)

