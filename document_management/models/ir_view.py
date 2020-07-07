from odoo import fields, models

NEW_VIEW = ('folder', 'Folder')


class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[NEW_VIEW])


class IrActionsActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[NEW_VIEW])
