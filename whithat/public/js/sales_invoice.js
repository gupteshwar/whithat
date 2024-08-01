frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm){
        if (!frm.doc.custom_subscription){
            console.log('>> Not Subscription')
        }else{
            if(frappe.session.user != 'Administrator'){
                if (frm.doc.is_return !== 1){
                    frm.set_df_property('items','cannot_delete_rows',true)
                }
            }
//            frm.set_df_property('items','cannot_add_rows',true)
        }
    }
});