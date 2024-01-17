frappe.ui.form.on('Subscription', {
    refresh: function(frm){
        if(!frm.is_new()){
            frm.add_custom_button(__('Update'),function() {
             frappe.call({
                method: 'whithat.custom_script.subscription.subscription.upgrade_plan',
                args: {
                    doc: frm.doc,
                },
                callback: function(r){
                    console.log(r.message)
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
    }
});