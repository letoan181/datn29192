odoo.define('magenest.import_button_disable', function (require) {
    "use strict";
    var KanbanController = require('web.KanbanController');
    var ListController = require('web.ListController');
    var core = require('web.core');
    var WebClient = require('web.WebClient');
    var session = require('web.session');
    var _t = core._t;
    var Sidebar = require('web.Sidebar');
    KanbanController.include({
        renderButtons: function ($node) {
            var self = this;
            this._super.apply(this, arguments);
            if (self.modelName.includes('document') && this.$buttons) {
                this.$buttons.find('.o_button_import').remove();
            }

        },


    });
    ListController.include({
        renderButtons: function ($node) {
            var self = this;
            this._super.apply(this, arguments);
            if (self.modelName.includes('document') && this.$buttons) {
                self.$buttons.find('.o_button_import').remove();
                self.$buttons.find('.o_list_export_xlsx').remove();
            }
        },
        renderSidebar: function ($node) {
            var model = this.modelName;
            var self = this;
            if (this.hasSidebar && model.includes('document')) {
                var other = [];
                if (this) {
                    other.push({
                        label: _t("Delete"),
                        callback: this._onDeleteSelectedRecords.bind(this)
                    });
                }
                this.sidebar = new Sidebar(this, {
                    editable: this.is_action_enabled('edit'),
                    env: {
                        context: this.model.get(this.handle, {raw: true}).getContext(),
                        activeIds: this.getSelectedIds(),
                        model: this.modelName,
                    },
                    actions: _.extend(this.toolbarActions, {other: other}),
                });
                return this.sidebar.appendTo($node).then(function () {
                    self._toggleSidebar();
                });

            }
            else {
                this._super.apply(this, arguments);
            }


        }
    });
    // Update Real Time On Same Session Tree View
    // WebClient.include({
    //     init: function (parent, client_options) {
    //         this._super.apply(this, arguments);
    //         this.bus_channels = {};
    //     },
    //     start: function () {
    //         var self = this;
    //         self._reload = _.throttle(self._reload, 1000);
    //         return $.when(this._super.apply(this, arguments));
    //     },
    //     bus_declare_channel: function (channel, method) {
    //         if (!(channel in this.bus_channels)) {
    //             this.bus_channels[channel] = method;
    //             this.call('bus_service', 'addChannel', channel);
    //         }
    //     },
    //     bus_delete_channel: function (channel) {
    //         this.call('bus_service', 'deleteChannel', channel);
    //         this.bus_channels = _.omit(this.bus_channels, channel);
    //     },
    //     bus_notification: function (notifications) {
    //         _.each(notifications, function (notification, index) {
    //             var channel = notification[0];
    //             var message = notification[1];
    //             if (channel in this.bus_channels) {
    //                 this.bus_channels[channel](message);
    //             }
    //         }, this);
    //     },
    //     destroy: function () {
    //         _.each(this.bus_channels, function (method, channel) {
    //             this.bus_delete_channel(channel);
    //         }, this);
    //         this.call('bus_service', 'stopPolling');
    //         this._super.apply(this, arguments);
    //     },
    //     show_application: function () {
    //         this.call('bus_service', 'onNotification', this, this.bus_notification);
    //         this.call('bus_service', 'startPolling');
    //         this.bus_declare_channel('refresh', this.refresh.bind(this));
    //         return this._super.apply(this, arguments);
    //     },
    //     refresh: function (message) {
    //         var action = this.action_manager.getCurrentAction();
    //         var controller = this.action_manager.getCurrentController();
    //         if (session.uid == message.uid && controller.widget.viewType === "folder") {
    //            this._reload(message, controller);
    //         }
    //     },
    //     _reload: function (message, controller) {
    //         if (controller && controller.widget) {
    //             controller.widget.reload();
    //         }
    //     },
    // });
});