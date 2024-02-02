frappe.ui.form.on('Item Price', {
    validate: function(frm){
        console.log('on validate ---!')
        if(!frm.is_new()){
            frappe.call({
                method: 'whithat.custom_script.subscription.subscription.price_alteration',
                args: {
                    doc: frm.doc.name,
                    new_price : frm.doc.price_list_rate,
                },
                callback: function(r){
                    console.log(r.message)
                }
            });
		}
    },
});