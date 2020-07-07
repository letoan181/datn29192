odoo.define('magenest.import_button_access', function (require) {
    "use strict";
    var KanbanController = require('web.KanbanController');
    var ListController = require('web.ListController');
    KanbanController.include({
        renderButtons: function ($node) {
            var self = this;
            this._super.apply(this, arguments);
            this.getSession().user_has_group('magenest_attendance.group_advanced_import').then(function (has_group) {
                if (has_group == false) {
                    if (self.modelName == 'hr.employee' || self.modelName == 'manager.attendance') {
                        if (self.$buttons) {
                            self.$buttons.find('.o_button_import').remove();
                        }
                    }
                }
                if (self.modelName == 'manager.attendance'){
                        if (self.$buttons) {
                            self.$buttons.find('.o_button_import').remove();
                        }
                    }
            });

        },
    });
    ListController.include({
        renderButtons: function ($node) {
            var self = this;
            this._super.apply(this, arguments);
            this.getSession().user_has_group('magenest_attendance.group_advanced_import').then(function (has_group) {
                if (has_group == false) {
                    if (self.modelName == 'hr.employee') {
                        if (self.$buttons) {
                            self.$buttons.find('.o_button_import').remove();
                        }
                    }
                }
                if (self.modelName == 'manager.attendance') {
                        if (self.$buttons) {
                            self.$buttons.find('.o_button_import').remove();
                        }
                    }
            });

        },
    });
});