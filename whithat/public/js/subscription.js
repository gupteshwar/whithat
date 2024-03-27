frappe.ui.form.on('Subscription', {
    refresh: function(frm){
        if (frm.doc.custom_is_combination_plans == 1){
            frm.remove_custom_button('Fetch Subscription Updates');
        }
        if(!frm.is_new()){
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
    },
});

frappe.ui.form.on("Subscription Plan Detail", {
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
        if (row.plan != ""){
            frappe.call({
                method: 'whithat.custom_script.subscription.subscription.get_price_list',
                args: {
                    plan : row.plan,
                    customer : frm.doc.party
                },
                callback: function(r){
                    console.log(r.message)
                    row.custom_cost = r.message;
                    frm.refresh_field('plans');
                }
            });
        }
    }
});
