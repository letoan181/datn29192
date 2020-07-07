odoo.define('magenest.disable_past_datepicker', function (require) {
    "use strict";
    var DateWidget = require('web.datepicker').DateWidget;
    DateWidget.include({
        start: function (parent, options) {
            this._super.apply(this, arguments);
            var self = this;
            if (this.options.disable_past_date) {
                var date = moment(new Date());
                this.$el.datetimepicker('minDate', date || null);
            }
        },
    });

});
// Define new widget
odoo.define('employee.worktime.info', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var field_utils = require('web.field_utils');

var QWeb = core.qweb;
var _t = core._t;

var ShowEmployeeWorkInfoWidget = AbstractField.extend({
    events: _.extend({
    }, AbstractField.prototype.events),
    supportedFieldTypes: ['char'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {boolean}
     */
    isSet: function() {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _render: function() {
        var self = this;
        var info = JSON.parse(this.value);
        if (!info) {
            this.$el.html('');
            return;
        }
        _.each(info.content, function (k, v){
            k.index = v;
            k.amount = field_utils.format.float(k.amount, {digits: k.digits});
            if (k.date){
                k.date = field_utils.format.date(field_utils.parse.date(k.date, {}, {isUTC: true}));
            }
        });
        this.$el.html(QWeb.render('ShowEmployeeWorkInfo', {
        }));
        _.each(this.$('.js_employee_info'), function (k, v){
            var isRTL = _t.database.parameters.direction === "rtl";
            var content = info.content[v];
            var options = {
                content: function () {
                    var $content = $(QWeb.render('EmployeeWorkInfo', {
                        type: content.type,
                        worktime: content.work_time
                    }));
                    return $content;
                },
                html: true,
                placement: isRTL ? 'bottom' : 'right',
                title: 'Work-Time Information',
                trigger: 'focus',
                delay: { "show": 0, "hide": 100 },
                container: $(k).parent(), // FIXME Ugly, should use the default body container but system & tests to adapt to properly destroy the popover
            };
            $(k).popover(options);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
});

field_registry.add('worktime', ShowEmployeeWorkInfoWidget);

return {
    ShowEmployeeWorkInfoWidget: ShowEmployeeWorkInfoWidget
};

});
