from erpnext.controllers.accounts_controller import AccountsController
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder
from erpnext.controllers.print_settings import set_print_templates_for_item_table, set_print_templates_for_taxes
from frappe.utils import flt


class CustomSalesOrder(SalesOrder):

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
