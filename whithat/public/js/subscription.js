frappe.ui.form.on('Subscription', {
    refresh: function(frm){
        if (frm.doc.custom_is_combination_plans == 1){
            frm.remove_custom_button('Fetch Subscription Updates');
        }

        frm.set_df_property('invoices','cannot_delete_rows',true)
        frm.set_df_property('invoices','cannot_add_rows',true)

        frm.set_df_property('custom_sales_orders','cannot_delete_rows',true)
        frm.set_df_property('custom_sales_orders','cannot_add_rows',true)
        
        if(!frm.is_new()){
			if(frm.doc.status !== 'Cancelled'){
                frm.add_custom_button(__('Update'),function() {
                    frappe.call({
                        method: 'whithat.custom_script.subscription.subscription.upgrade_plan',
                        args: {
                            doc: frm.doc,
                        },
                        callback: function(r){
                            console.log(r.message)
                            cur_frm.refresh();
                        }
                    });
                });
                frm.add_custom_button(__('Due Date Alert'),function() {
                    frappe.call({
                        method: 'whithat.custom_script.subscription.subscription.due_date_alert',
                        args: {
                            sub: frm.doc.name,
                        },
                        callback: function(r){
                            console.log(r.message)
                            frm.refresh();
                        }
                    });
                });
            }
		}
    },
});

frappe.ui.form.on("Subscription Plan Detail", {
    before_plans_remove: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        console.log('row',row)
         if (row.custom_is_active === 1) {
            var dialog = new frappe.ui.Dialog({
                title: 'Warning',
                fields: [
                    {
                        fieldname: 'message',
                        fieldtype: 'HTML',
                        options: '<p>Cannot delete active subscription plan details.</p>'
                    }
                ],
                primary_action_label: 'OK',
                primary_action: function() {
                    dialog.hide();
                    cur_frm.reload_doc();
                }
            });
            dialog.show();
            return false;
        }
        return true;
    },
    qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.custom_cost != ""){
            row.custom_amount = (row.custom_cost)*(row.qty);
        }
        frm.refresh_field('plans');
    },
    plan: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        console.log("in price based on ---!")
        console.log(row.plan)
        if (row.plan != "" && frm.doc.party){
            frappe.call({
                method: 'whithat.custom_script.subscription.subscription.get_price_list',
                args: {
                    plan : row.plan,
                    customer : frm.doc.party
                },
                callback: function(r){
                    console.log(r.message)
                    row.custom_cost = r.message[0];
                    row.custom_last_purchase_rate = r.message[1];
                    frm.refresh_field('plans');
                }
            });
        }else{
            frappe.msgprint('Please select party !')
        }
    }
});


