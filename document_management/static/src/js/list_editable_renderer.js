odoo.define('document_management.list_editable_renderer_inherit', function (require) {
    "use strict";
    var core = require('web.core');
    var list_editable_renderer_inherit = require('web.ListRenderer');
    var _t = core._t;
    list_editable_renderer_inherit.include({
        init: function (parent, state, params) {
            var self = this;
            this._super.apply(this, arguments);
            // logan
            try {
                if (state['model'] == 'res.users' || state['model'] == 'res.groups' ||  state['model'] == 'document.general.part') {
                    if (parent['model'] && (parent['model'].includes('document') == true || parent['model'].includes('mass') == true ) && parent['mode'] == 'edit') {
                        params.arch.attrs.create = true;
                        params.arch.attrs.delete = true;
                        params.addCreateLine = true;
                        params.addTrashIcon = true;
                    }
                }
            } catch (e) {
                console.log(e)
            }
            // end logan

            // if addCreateLine is true, the renderer will add a 'Add a line' link
            // at the bottom of the list view
            this.addCreateLine = params.addCreateLine;

            // Controls allow overriding "add a line" by custom controls.

            // Each <control> (only one is actually needed) is a container for (multiple) <create>.
            // Each <create> will be a "add a line" button with custom text and context.

            // The following code will browse the arch to find
            // all the <create> that are inside <control>
            if (this.addCreateLine) {
                this.creates = [];

                _.each(this.arch.children, function (child) {
                    if (child.tag !== 'control') {
                        return;
                    }

                    _.each(child.children, function (child) {
                        if (child.tag !== 'create' || child.attrs.invisible) {
                            return;
                        }

                        self.creates.push({
                            context: child.attrs.context,
                            string: child.attrs.string,
                        });
                    });
                });

                // Add the default button if we didn't find any custom button.
                if (this.creates.length === 0) {
                    this.creates.push({
                        string: _t("Add a line"),
                    });
                }
            }

            // if addTrashIcon is true, there will be a small trash icon at the end
            // of each line, so the user can delete a record.
            this.addTrashIcon = params.addTrashIcon;

            // replace the trash icon by X in case of many2many relations
            // so that it means 'unlink' instead of 'remove'
            this.isMany2Many = params.isMany2Many;

            this.currentRow = null;
            this.currentFieldIndex = null;
        },
    });
    return list_editable_renderer_inherit;
});