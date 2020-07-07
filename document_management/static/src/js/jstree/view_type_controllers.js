odoo.define('document.Controller', function (require) {
    "use strict";

    var AbstractController = require('web.AbstractController');
    var dialogs = require('web.view_dialogs');
    var core = require('web.core');
    var time = require('web.time');
    var Dialog = require('web.Dialog');

    var _t = core._t;

    var DocumentController = AbstractController.extend({
        custom_events: _.extend({}, AbstractController.prototype.custom_events, {}),

        /**
         * @constructor
         * @override
         */
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);

        },
        // start: function () {
        //     return $.when(
        //         this._super.apply(this, arguments),
        //         this.renderer.appendTo(this.$el)
        //     );
        // },
        //  update: function (params, options) {
        //     var res = this._super.apply(this, arguments);
        //     if (_.isEmpty(params)){
        //         return res;
        //     }
        //     var defaults = _.defaults({}, options, {
        //         adjust_window: true
        //     });
        //     var self = this;
        //     var domains = params.domain;
        //     var contexts = params.context;
        //     var group_bys = params.groupBy;
        //     this.last_domains = domains;
        //     this.last_contexts = contexts;
        //     // select the group by
        //     var n_group_bys = [];
        //     if (this.renderer.arch.attrs.default_group_by) {
        //         n_group_bys = this.renderer.arch.attrs.default_group_by.split(',');
        //     }
        //     if (group_bys.length) {
        //         n_group_bys = group_bys;
        //     }
        //     this.renderer.last_group_bys = n_group_bys;
        //     this.renderer.last_domains = domains;
        //
        //     var fields = this.renderer.fieldNames;
        //     fields = _.uniq(fields.concat(n_group_bys));
        //     return $.when(
        //         res,
        //         self._rpc({
        //             model: self.model.modelName,
        //             method: 'search_read',
        //             kwargs: {
        //                 fields: fields,
        //                 domain: domains,
        //             },
        //             context: self.getSession().user_context,
        //         }).then(function (data) {
        //             return self.renderer.on_data_loaded(data, n_group_bys, defaults.adjust_window);
        //         })
        //     );
        // },

    });

    return DocumentController;
});