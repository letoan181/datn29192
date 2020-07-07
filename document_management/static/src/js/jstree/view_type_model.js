odoo.define('document.Model', function (require) {
    "use strict";

    var AbstractModel = require('web.AbstractModel');

    var DocumentModel = AbstractModel.extend({

        /**
         * @constructor
         */
        init: function () {
            this._super.apply(this, arguments);
        },
        //  load: function (params) {
        //     var self = this;
        //     // console.log('toan')
        //     this.modelName = params.modelName;
        //     this.fieldNames = params.fieldNames;
        //     if (!this.preload_def) {
        //         this.preload_def = $.Deferred();
        //         $.when(
        //             this._rpc({model: this.modelName, method: 'check_access_rights', args: ["write", false]}),
        //             this._rpc({model: this.modelName, method: 'check_access_rights', args: ["unlink", false]}),
        //             this._rpc({model: this.modelName, method: 'check_access_rights', args: ["create", false]}))
        //         .then(function (write, unlink, create) {
        //             self.write_right = write;
        //             self.unlink_right = unlink;
        //             self.create_right = create;
        //             self.preload_def.resolve();
        //         });
        //     }
        //
        //     this.data = {
        //         domain: params.domain,
        //         context: params.context,
        //     };
        //
        //     return true
        // },

    });

    return DocumentModel;
});
