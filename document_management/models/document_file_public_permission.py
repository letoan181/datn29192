from odoo import models, fields, api
from ..utils.google_drive_helper import GoogleDriveHelper


class DocumentFilePublicPermission(models.Model):
    _name = "document.file.public.permission"
    _description = "Store all public file permission"

    file_id = fields.Char('File Id', required=True)
    google_drive_permission_id = fields.Char()
    type = fields.Selection([('read', 'Read'), ('write', 'Write'), ('comment', 'Comment')], required=True, default='read')
    model = fields.Selection(
        [('project', 'Project'), ('quotation', 'Quotation'), ('crm', 'CRM')])
    error_permission_id = fields.Char('Error Permission')

    @api.model
    def create(self, values):
        new_permission = None
        google_drive_helper = GoogleDriveHelper()
        result = super(DocumentFilePublicPermission, self).create(values)
        try:
            if result.type == 'read':
                new_permission = google_drive_helper.create__public_file_read_permission(result.file_id)
            if result.type == 'write':
                new_permission = google_drive_helper.create_public_file_write_permission(result.file_id)
            if result.type == 'comment':
                new_permission = google_drive_helper.create_public_file_comment_permission(result.file_id)
            # update gg drive ID
            if new_permission is not None:
                result.google_drive_permission_id = new_permission
        except Exception as e:
            """print(e)"""
        return result

    def unlink(self):
        google_drive_helper = GoogleDriveHelper()
        for rec in self:
            try:
                google_drive_helper.drop_public_file_permission(file_id=rec.file_id,
                                                                permission_id=rec.google_drive_permission_id)
            except Exception as ex:
                rec.create({
                    'file_id': rec.file_id,
                    'type': rec.type,
                    'google_drive_permission_id': rec.google_drive_permission_id,
                    'model': rec.model,
                    'error_permission_id': rec.file_id
                })
        return super(DocumentFilePublicPermission, self).unlink()

    def _process_sync_permission_queue(self, row):
        # update public permission
        try:
            permissions_need_sync = self.env['document.file.public.permission'].sudo().search(
                [('google_drive_permission_id', '=', False)], limit=row)
            if permissions_need_sync:
                google_drive_helper = GoogleDriveHelper()
                google_drive_helper.set_context_env(self)
                new_permission = None
                for e in permissions_need_sync:
                    try:
                        if e.type == 'read':
                            new_permission = google_drive_helper.create__public_file_read_permission(e.file_id)
                        if e.type == 'write':
                            new_permission = google_drive_helper.create_public_file_write_permission(e.file_id)
                        if e.type == 'comment':
                            new_permission = google_drive_helper.create_public_file_comment_permission(e.file_id)
                        # update gg drive ID
                        if new_permission is not None:
                            e.google_drive_permission_id = new_permission
                    except Exception as e:
                        """print(e)"""
            permissions_need_delete = self.env['document.file.public.permission'].sudo().search(
                [('error_permission_id', '!=', False)], limit=row)
            if permissions_need_delete:
                for p in permissions_need_delete:
                    p.unlink()
        except Exception as ex:
            e = 0
