frappe.ui.form.on('Item Price', {
    refresh: function(frm){
        console.log('on refresh ---!')
        if(!frm.is_new()){
            frm.add_custom_button(__('Update Subscription'),function() {
                frappe.call({
                    method: 'whithat.custom_script.subscription.subscription.price_alteration',
                    args: {
                        doc: frm.doc.name,
                        new_price : frm.doc.price_list_rate,
                        valid_from_date : frm.doc.valid_from,
                    },
                    callback: function(r){
                        console.log(r.message)
                    }
                });
            });
		}
    },
});