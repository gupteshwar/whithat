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
    data = frappe.parse_json(doc)
    subDoc = frappe.get_doc("Subscription", data['name'])
    doctype = "Sales Invoice" if subDoc.party_type == "Customer" else "Purchase Invoice"
    invoice = Subscription.get_current_invoice(subDoc)
    prorate = frappe.db.get_single_value("Subscription Settings", "prorate")
    si_doc = False
    if invoice:
        si_doc = frappe.get_doc('Sales Invoice', invoice.name)
    # Check if auto-renewal is enabled and it's time to generate the invoice
    if subDoc.custom_is_auto_renewal == 1 and date.today() < subDoc.end_date \
            and date_diff(subDoc.end_date, date.today()) == int(subDoc.custom_generate_invoice_before_days) and invoice.custom_is_renewal !=1:
        print('date diff-----------', date_diff(subDoc.end_date, date.today()))
        is_renewal = True
        new_invoice = create_invoices(subDoc, prorate, date.today(), subDoc.plans, 0, False, is_renewal)

        if new_invoice:
            subDoc.append("invoices", {"document_type": "Sales Invoice", "invoice": new_invoice.name})
            subDoc.save()
            send_email(subDoc, new_invoice)
    elif si_doc:
        for i in subDoc.plans:
            if not i.custom_is_active:
                plan_doc = frappe.get_doc("Subscription Plan", i.plan)
                for s in si_doc.items:
                    plans = []
                    is_return = False
                    start_date = i.custom_subscription_start_date
                    if i.custom_subscription_end_date:
                        end_date = i.custom_subscription_end_date
                    else:
                        i.custom_subscription_end_date = subDoc.current_invoice_end
                        end_date = subDoc.current_invoice_end

                    if invoice.custom_is_custom != 1 and (s.item_code == plan_doc.item and i.qty == s.qty and i.custom_amount == s.amount) and invoice.posting_date == start_date :
                        i.custom_is_active = 1
                        i.custom_subscription_end_date = subDoc.current_invoice_end
                        subDoc.save()
                        break
                    else:
                        rate = get_plan_rates(subDoc, subDoc.current_invoice_start,subDoc.current_invoice_end, i.custom_billing_based_on, s.amount, i.custom_amount, i.qty, i.plan, start_date, end_date)
                        plans.append(i)
                        if i.custom_billing_based_on == "Downgrade with Fix Rate" or i.custom_billing_based_on == "Downgrade with Prorate":
                            is_return = True
                        new_invoice = create_invoices(subDoc, prorate, start_date, end_date, plans, rate, is_return)
                        if new_invoice:
                            i.custom_is_active = 1
                            subDoc.append("invoices", {"document_type": doctype, "invoice": new_invoice.name})
                            subDoc.current_invoice_start = new_invoice.from_date
                            subDoc.current_invoice_end = new_invoice.to_date
                            subDoc.save()
    else:
        new_invoice = create_invoices(subDoc, prorate, subDoc.current_invoice_start, subDoc.current_invoice_end, subDoc.plans, 0, False, False, True)
        if new_invoice:
            subDoc.append("invoices", {"document_type": "Sales Invoice", "invoice": new_invoice.name})
            subDoc.save()



@frappe.whitelist()
def create_invoices(doc, prorate, start_date, end_date, plans, rate, is_return=None, is_renewal=None, is_new=None):
    print('doc--------------------', doc.name)
    subDoc = frappe.get_doc("Subscription", doc.name)
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
    items_list = get_items_from_plans(subDoc, plans, prorate, rate, is_renewal, is_new)
    for item in items_list:
        if is_return:
            item["rate"] = str(abs(item["rate"]))
        item["cost_center"] = subDoc.cost_center
        invoice.append("items", item)
        print('item--------', item)
    # Taxes
    tax_template = ""

    if doctype == "Sales Invoice" and subDoc.sales_tax_template:
        tax_template = subDoc.sales_tax_template
    if doctype == "Purchase Invoice" and subDoc.purchase_tax_template:
        tax_template = subDoc.purchase_tax_template

    if tax_template:
        invoice.taxes_and_charges = tax_template
        invoice.set_taxes()
    # Due date
    if subDoc.days_until_due:
        invoice.append(
            "payment_schedule",
            {
                "due_date": add_days(invoice.posting_date, cint(subDoc.days_until_due)),
                "invoice_portion": 100,
            },
        )

    # Discounts
    if subDoc.is_trialling():
        invoice.additional_discount_percentage = 100
    else:
        if subDoc.additional_discount_percentage:
            invoice.additional_discount_percentage = subDoc.additional_discount_percentage

        if subDoc.additional_discount_amount:
            invoice.discount_amount = subDoc.additional_discount_amount

        if subDoc.additional_discount_percentage or subDoc.additional_discount_amount:
            discount_on = subDoc.apply_additional_discount
            invoice.apply_discount_on = discount_on if discount_on else "Grand Total"

    # Subscription period
    invoice.from_date = start_date
    invoice.to_date = end_date

    if is_renewal:
        invoice.custom_is_renewal = 1

    invoice.flags.ignore_mandatory = True
    invoice.custom_is_custom = 1
    invoice.set_missing_values()
    invoice.save()

    if subDoc.submit_invoice:
        invoice.submit()

    if is_return:
        if not subDoc.submit_invoice:
            invoice.submit()
        print('invoice return -----', invoice.name, type(invoice))
        new_invoice = make_sales_return(invoice.name)
        new_invoice.from_date = start_date
        new_invoice.to_date = end_date
        new_invoice.save()
        return new_invoice
    return invoice

@frappe.whitelist()
def get_items_from_plans(self, plans, prorate=0, rate=0, is_renewal=None, is_new=None):
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
        if is_renewal or is_new:
            rate = get_plan_rate(plan.plan, plan.qty, party, self.current_invoice_start, self.current_invoice_end)
            print('rate~~~~~~~~~~~~~~', rate)
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
                "rate": rate,
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
def get_plan_rates(subDoc, s_start_date, sp_end_date, billing_based_on, s_amount, p_amount, p_qty, plan, start_date=None, end_date=None):
    print('plan -------------', plan)
    plan = frappe.get_doc("Subscription Plan", plan)
    if billing_based_on == "Fixed Rate":
        rate = p_amount / p_qty
        return rate

    elif billing_based_on == "Prorate":
        _current_invoice_start = Subscription.get_current_invoice_start(subDoc, start_date)
        _current_invoice_end = Subscription.get_current_invoice_end(subDoc, _current_invoice_start)
        s_no_of_day = date_diff(_current_invoice_end, _current_invoice_start)
        cp_no_of_day = date_diff(end_date, start_date)

        p_current_amount = (p_amount / s_no_of_day)*cp_no_of_day
        print('s-------------------------p-------------------', s_no_of_day, cp_no_of_day, p_current_amount)
        rate = p_current_amount / p_qty
        return rate

    elif billing_based_on == "Upgrade with Prorate" or billing_based_on == "Downgrade with Prorate":
        s_no_of_day = date_diff(sp_end_date, s_start_date)
        cp_no_of_day = date_diff(end_date, start_date)
        s_current_amount = (s_amount / s_no_of_day) * cp_no_of_day
        p_current_amount = (p_amount / s_no_of_day) * cp_no_of_day
        print('s-------------------------p-------------------', s_no_of_day, cp_no_of_day, s_current_amount,
              p_current_amount)
        rate = (p_current_amount - s_current_amount) / p_qty
        return rate
    elif billing_based_on == "Upgrade with Fix Rate" or billing_based_on == "Downgrade with Fix Rate":
        s_no_of_day = date_diff(sp_end_date, s_start_date)
        cp_no_of_day = date_diff(end_date, start_date)
        s_current_amount = (s_amount / s_no_of_day) * cp_no_of_day
        print('s-------------------------p-------------------', s_no_of_day, cp_no_of_day, s_current_amount,
              p_amount)
        rate = (p_amount - s_current_amount) / p_qty
        return rate


@frappe.whitelist()
def get_price_list(plan, customer=None):
    plan = frappe.get_doc("Subscription Plan", plan)
    if plan.price_determination == "Fixed Rate":
        return plan.cost
    if plan.price_determination == "Based On Price List":
        ItemPrice = frappe.get_all('Item Price', filters={'item_code': plan.item, 'price_list': plan.price_list})
        price = ItemPrice[0]
        priceDoc = frappe.get_doc('Item Price', price['name'])
        return priceDoc.price_list_rate

@frappe.whitelist()
def send_email(subdoc, invoive):
    print('subdoc & invoice -------', subdoc, invoive, type(subdoc), type(invoive))
    try:
        # Email subject
        subject = f"Sales Invoice { invoive.name } due date is near"

        # Email body
        body = f"Dear {subdoc.party},<br><br>"
        body += f"We would like to notify you that a sales Invoice has been generated in the ERP system. Kindly find the details below:<br>"
        body += f"<b>Sales Invoice Details:</b><br><br>"
        body += f"Sales Invoice No: {invoive.name}<br>"
        body += f"Date: {invoive.posting_date}<br>"
        body += f"Grand Total: {invoive.grand_total}<br>"
        body += f"Outstanding Amount: {invoive.outstanding_amount}<br><br>"
        body += f"Review the information in this Sales Invoice to ensure its accuracy.<br>"
        body += f"Should you have any inquiries or require further clarification, Thank you for your prompt attention to this matter.<br><br>"
        body += f"Best regards:<br>"
        body += f"Accounts Department<br>"

        # Send the email
        frappe.sendmail(
            recipients=subdoc.custom_party_email,
            subject=subject,
            message=body
        )
        frappe.msgprint("Email sent Successfully!")
        return True
    except Exception as e:
        print("Error sending email:", e)
        raise e
@frappe.whitelist()
def price_alteration(doc, new_price):
    ItemPrice = frappe.get_doc('Item Price', doc)
    print('price_list_rate ------', ItemPrice.price_list_rate, new_price)
    is_return = False

    Sub_Plan = frappe.get_all(
        'Subscription Plan',
         filters={'item': ItemPrice.item_code, 'price_list': ItemPrice.price_list},
         fields=['name', 'item']
    )
    for plan in Sub_Plan:
        subscription = frappe.get_all('Subscription Plan Detail',
                                      filters={'plan': plan['name']},
                                      fields=['parent', 'plan', 'custom_cost', 'qty', 'custom_amount', 'custom_subscription_start_date',
                                              'custom_subscription_end_date',],
                                      )
        print('sub-len ---', len(subscription))
        if subscription:
            for sub in subscription:
                subDoc = frappe.get_doc('Subscription', sub['parent'])
                print('sub-doc ---------', subDoc)
                invoice = Subscription.get_current_invoice(subDoc)
                prorate = frappe.db.get_single_value("Subscription Settings", "prorate")
                si_doc = frappe.get_doc('Sales Invoice', invoice.name)
                if si_doc:
                    print('sidoc -----', si_doc)
                    for s in si_doc.items:
                        plans = []
                        if s.item_code == plan['item'] and sub['custom_subscription_start_date'] == si_doc.posting_date:
                            new_amount = float(new_price) * float(sub['qty'])
                            print('new amount ------------', new_amount)
                            if s.amount < float(new_amount) and s.amount != float(new_amount):
                                custom_billing_based_on = 'Upgrade with Prorate'
                            if s.amount > float(new_amount) and s.amount != float(new_amount):
                                custom_billing_based_on = 'Downgrade with Prorate'
                                is_return = True


                            rate = get_plan_rates(subDoc, subDoc.current_invoice_start, subDoc.current_invoice_end,
                                                  custom_billing_based_on, s.amount, float(new_amount), sub['qty'],
                                                  sub['plan'], date.today(), sub['custom_subscription_end_date'])
                            plans.append(sub)
                            end_date = sub['custom_subscription_end_date']
                            new_invoice = create_invoices(subDoc, prorate, date.today(), end_date, plans, rate,
                                                          is_return)
                            if new_invoice:
                                subDoc.append("invoices", {"document_type": 'Sales Invoice', "invoice": new_invoice.name})
                                subDoc.current_invoice_start = new_invoice.from_date
                                subDoc.current_invoice_end = new_invoice.to_date
                                subDoc.save()





