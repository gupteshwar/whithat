import frappe
from erpnext.accounts.doctype.subscription.subscription import Subscription
from erpnext.accounts.doctype.subscription.subscription import get_prorata_factor
from frappe import _
import json
from erpnext.accounts.party import get_party_account_currency
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe.utils.data import (
	add_days,
	cint,
)
from erpnext.utilities.product import get_price
from frappe.utils import date_diff, flt, get_first_day, get_last_day, getdate
from dateutil import relativedelta
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return
from datetime import date
from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate


@frappe.whitelist()
def upgrade_plan(doc):
    subDoc = frappe.get_doc("Subscription",doc)
    doctype = "Sales Invoice" if subDoc.party_type == "Customer" else "Purchase Invoice"
    invoice = Subscription.get_current_invoice(subDoc)
    prorate = frappe.db.get_single_value("Subscription Settings", "prorate")
    si_doc = frappe.get_doc('Sales Invoice',invoice)
    # if (subDoc.custom_is_auto_renewal == 1) and ((date.today() < subDoc.end_date)
    #       and (date_diff(subDoc.end_date,date.today()) == int(subDoc.custom_generate_invoice_before_days))):
    #         print('date diff -----///-----------', date_diff(subDoc.end_date, date.today()))
    #         is_renewal = True
    #         new_invoice = create_invoices(subDoc, prorate, date.today(), subDoc.plans, is_renewal)
    #         if new_invoice:
    #             subDoc.append("invoices", {"document_type": doctype, "invoice": new_invoice.name})
    #             subDoc.save()
    if si_doc:
        for i in subDoc.plans:

            if not i.custom_is_active:
                plan_doc = frappe.get_doc("Subscription Plan", i.plan)
                for s in si_doc.items:
                    plans = []
                    if invoice.custom_is_custom != 1 and (s.item_code == plan_doc.item and i.qty == s.qty and i.custom_amount == s.amount):
                        i.custom_is_active = 1
                        subDoc.save()
                        # continue
                    elif (i.custom_amount >= s.amount):

                        start_date = i.custom_subscription_start_date
                        rate = get_plan_rates(subDoc.current_invoice_start,s.amount,i.custom_amount,i.qty,i.plan,start_date, subDoc.current_invoice_end),
                        plans.append(i)
                        new_invoice = create_invoices(subDoc,prorate,start_date,plans,rate)
                        if new_invoice:
                            i.custom_is_active = 1
                            subDoc.append("invoices", {"document_type": doctype, "invoice": new_invoice.name})
                            subDoc.save()
                    else:
                        start_date = i.custom_subscription_start_date
                        rate = get_plan_rates(subDoc.current_invoice_start, s.amount, i.custom_amount, i.qty, i.plan,
                                             start_date, subDoc.current_invoice_end),
                        plans.append(i)
                        is_return = True
                        new_invoice = create_invoices(subDoc, prorate, start_date, plans, rate,is_return,invoice)
                        if new_invoice:
                            i.custom_is_active = 1
                            subDoc.append("invoices", {"document_type": doctype, "invoice": new_invoice.name})
                            subDoc.save()




@frappe.whitelist()
def create_invoices(doc, prorate,start_date,plans,rate,is_return=None):
    subDoc = frappe.get_doc("Subscription",doc)
    """
    Creates a `Invoice`, submits it and returns it
    """
    doctype = "Sales Invoice" if subDoc.party_type == "Customer" else "Purchase Invoice"

    invoice = frappe.new_doc(doctype)
    # For backward compatibility
    # Earlier subscription didn't had any company field
    company = subDoc.get("company") or Subscription.get_default_company()
    if not company:
        frappe.throw(
            _("Company is mandatory was generating invoice. Please set default company in Global Defaults")
        )

    invoice.company = company
    invoice.set_posting_time = 1
    invoice.posting_date = (
        start_date
    )

    invoice.cost_center = subDoc.cost_center

    if doctype == "Sales Invoice":
        invoice.customer = subDoc.party
    else:
        invoice.supplier = subDoc.party
        if frappe.db.get_value("Supplier", subDoc.party, "tax_withholding_category"):
            invoice.apply_tds = 1

    ### Add party currency to invoice
    invoice.currency = get_party_account_currency(subDoc.party_type, subDoc.party, subDoc.company)

    ## Add dimensions in invoice for subscription:
    accounting_dimensions = get_accounting_dimensions()

    for dimension in accounting_dimensions:
        if subDoc.get(dimension):
            invoice.update({dimension: subDoc.get(dimension)})

    # Subscription is better suited for service items. I won't update `update_stock`
    # for that reason
    items_list = get_items_from_plans(subDoc,plans, prorate,rate[0])
    for item in items_list:
        if is_return:
            item["rate"] = str(abs(item["rate"]))
        item["cost_center"] = subDoc.cost_center
        invoice.append("items", item)
        print('item--------',item)
    # Taxes
    tax_template = ""

    if doctype == "Sales Invoice" and subDoc.sales_tax_template:
        tax_template = subDoc.sales_tax_template
    if doctype == "Purchase Invoice" and subDoc.purchase_tax_template:
        tax_template = subDoc.purchase_tax_template

    # if tax_template:
    #     invoice.taxes_and_charges = tax_template
    #     invoice.set_taxes()

    # Due date
    # if subDoc.days_until_due:
    #     invoice.append(
    #         "payment_schedule",
    #         {
    #             "due_date": add_days(invoice.posting_date, cint(subDoc.days_until_due)),
    #             "invoice_portion": 100,
    #         },
    #     )

    # Discounts
    # if subDoc.is_trialling():
    #     invoice.additional_discount_percentage = 100
    # else:
    #     if subDoc.additional_discount_percentage:
    #         invoice.additional_discount_percentage = subDoc.additional_discount_percentage
    #
    #     if subDoc.additional_discount_amount:
    #         invoice.discount_amount = subDoc.additional_discount_amount
    #
    #     if subDoc.additional_discount_percentage or subDoc.additional_discount_amount:
    #         discount_on = subDoc.apply_additional_discount
    #         invoice.apply_discount_on = discount_on if discount_on else "Grand Total"

    # Subscription period
    invoice.from_date = start_date
    invoice.to_date = subDoc.current_invoice_end

    invoice.flags.ignore_mandatory = True
    invoice.custom_is_custom = 1
    invoice.set_missing_values()
    invoice.save()

    if subDoc.submit_invoice:
        invoice.submit()
    invoice.custom_is_custom = 1
    if is_return:
        new_invoice = make_sales_return(invoice)
        new_invoice.save()
        new_invoice.submit()
        return new_invoice
    return invoice

@frappe.whitelist()
def get_items_from_plans(self, plans, prorate=0,rate=0,is_renewal=None):
    """
    Returns the `Item`s linked to `Subscription Plan`
    """
    if prorate:
        prorate_factor = get_prorata_factor(
            self.current_invoice_end, self.current_invoice_start, self.generate_invoice_at_period_start
        )

    items = []
    party = self.party

    for plan in plans:
        # if is_renewal:
        #
        #     rate = get_plan_rate(plan.plan, plan.qty, party, self.current_invoice_start, self.current_invoice_end)
        #     print('rate~~~~~~~~~~~~~~',rate)
        plan_doc = frappe.get_doc("Subscription Plan", plan.plan)
        item_code = plan_doc.item

        if self.party == "Customer":
            deferred_field = "enable_deferred_revenue"
        else:
            deferred_field = "enable_deferred_expense"

        deferred = frappe.db.get_value("Item", item_code, deferred_field)

        if not prorate:
            item = {
                "item_code": item_code,
                "qty": plan.qty,
                "rate":rate,
                "cost_center": plan_doc.cost_center,
            }
        else:
            item = {
                "item_code": item_code,
                "qty": plan.qty,
                "rate": rate,
                "cost_center": plan_doc.cost_center,
            }

        if deferred:
            item.update(
                {
                    deferred_field: deferred,
                    "service_start_date": plan.custom_subscription_srart_date,
                    "service_end_date": self.current_invoice_end,
                }
            )

        accounting_dimensions = get_accounting_dimensions()

        for dimension in accounting_dimensions:
            if plan_doc.get(dimension):
                item.update({dimension: plan_doc.get(dimension)})

        items.append(item)

    return items


@frappe.whitelist()
def get_plan_rates(s_start_date,s_amount,p_amount,p_qty,plan,start_date=None, end_date=None):
    plan = frappe.get_doc("Subscription Plan", plan)

    if plan.price_determination == "Fixed Rate":
        s_no_of_months = relativedelta.relativedelta(end_date, s_start_date).months + 1
        cp_no_of_months = relativedelta.relativedelta(end_date, start_date).months + 1
        s_current_amount = (s_amount / s_no_of_months)*cp_no_of_months
        p_current_amount = (p_amount / s_no_of_months)*cp_no_of_months
        print('s-------------------------p-------------------',s_no_of_months,cp_no_of_months,s_current_amount,p_current_amount)
        rate = (p_current_amount - s_current_amount)/p_qty
        return rate