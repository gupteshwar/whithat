frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm){
        if (frm.doc.custom_subscription != ''){
            console.log('>> From Subscription')
            frm.set_df_property('items','cannot_delete_rows',true)
        }
    }
});