from odoo import models, fields, api


class DocumentFilePermissionJustClearPermission(models.Model):
    _name = 'document.file.permission.just.clear.permission'

    def _default_document_file_permissions(self):
        if self._context.get('active_ids'):
            return self.env['document.file.permission'].browse(self._context.get('active_ids'))

    document_file_permission = fields.Many2many('document.file.permission', 'document_file_permission_just_clear_rel',
                                                'document_file_just_clear_id', 'document_file_id', string="Record",
                                                required=True,
                                                default=_default_document_file_permissions)

    def force_clear_permission_to_update_again(self):
        if self.user_has_groups('base.group_system'):
            self.env.cr.execute(
                """update document_file_permission set google_drive_permission_id = null where id in %s""",
                (tuple(self.document_file_permission.ids),))
        # return {'type': 'ir.actions.client', 'tag': 'reload'}
