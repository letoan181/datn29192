from odoo import models, fields, api
from odoo.exceptions import UserError
from ..utils.google_drive_helper import GoogleDriveHelper


class DocumentFilePermission(models.Model):
    _name = "document.file.permission"
    _description = "Store all pair user file permission"

    res_user_id = fields.Integer()
    file_id = fields.Char('File Id', required=True)
    google_drive_permission_id = fields.Char()
    type = fields.Selection([('read', 'Read'), ('write', 'Write')], required=True, default='read')
    status = fields.Char('Current Status')
    error_message = fields.Char('Error Message')

    def unlink(self):
        if len(self.ids) > 0:
            self.env.cr.execute(
                """select file_id,google_drive_permission_id,res_user_id from document_file_permission where id in %s""",
                (tuple(self.ids),))
            all_permission = self.env.cr.fetchall()
            if all_permission is not None and len(all_permission) > 0:
                need_drop_permission = []
                for e in all_permission:
                    if e[1] is not None and len(e[1]) > 0:
                        need_drop_permission.append({
                            'file_id': e[0],
                            'google_drive_permission_id': e[1],
                            'res_user_id': e[2],
                            'status': 'drop error',
                        })
                self.env['document.file.permission.error'].sudo().create(need_drop_permission)
            return super(DocumentFilePermission, self).unlink()

    def _process_sync_user_write_permission_queue(self, row_count):
        try:
            # check if error queue then stop
            file_error = self.env['document.file.permission.error'].sudo().search([('error_message', '=', None)])
            # print(not (len(file_error) > 0))
            if not (len(file_error) > 0):
                self.env.cr.execute("""select document_file_permission.id as id, file_id, google_email
            from document_file_permission left join res_users on res_users.id = document_file_permission.res_user_id
            where document_file_permission.google_drive_permission_id is null and document_file_permission.status is null and type like 'write' and res_users.active is true and res_users.google_email is not null 
            and document_file_permission.status is null """)
                need_sync_data = self.env.cr.fetchmany(row_count)
                if need_sync_data:
                    google_drive_helper = GoogleDriveHelper()
                    google_drive_helper.set_context_env(self)
                    for e in need_sync_data:
                        # mark in process for this record
                        self.env.cr.execute(
                            """update document_file_permission set status = 'in_process' WHERE id=%s""", (e[0],))
                        self.env.cr.commit()
                        try:
                            new_permission = google_drive_helper.create_file_write_permission(e[1], e[2])
                            self.env['document.file.permission'].sudo().search([('id', '=', e[0])]).write(
                                {'google_drive_permission_id': new_permission,
                                 'status': False})
                        except Exception as ex:
                            self.env['document.file.permission'].sudo().search([('id', '=', e[0])]).write(
                                {'status': 'error',
                                 'error_message': str(ex)})
                            # raise UserError(_("Something went wrong, please try again later"))
                            e = 0
        except Exception as ex:
            e = 0

    def _process_sync_user_read_permission_queue(self, row_count):
        try:
            # check if error queue then stop
            file_error = self.env['document.file.permission.error'].sudo().search([('error_message', '=', None)])
            if not (len(file_error) > 0):
                self.env.cr.execute("""select document_file_permission.id as id, file_id, google_email
            from document_file_permission left join res_users on res_users.id = document_file_permission.res_user_id
            where document_file_permission.google_drive_permission_id is null and document_file_permission.status is null and type like 'read' and res_users.active is true and res_users.google_email is not null 
            and document_file_permission.status is null """)
                need_sync_data = self.env.cr.fetchmany(row_count)
                if need_sync_data:
                    google_drive_helper = GoogleDriveHelper()
                    google_drive_helper.set_context_env(self)
                    for e in need_sync_data:
                        # mark in process for this record
                        self.env.cr.execute(
                            """update document_file_permission set status = 'in_process' WHERE id=%s""", (e[0],))
                        self.env.cr.commit()
                        try:
                            new_permission = google_drive_helper.create_file_read_permission(e[1], e[2])
                            self.env['document.file.permission'].sudo().search([('id', '=', e[0])]).write(
                                {'google_drive_permission_id': new_permission,
                                 'status': False})
                        except Exception as ex:
                            self.env['document.file.permission'].sudo().search([('id', '=', e[0])]).write(
                                {'status': 'error',
                                 'error_message': str(ex)})
                            # raise UserError(_("Something went wrong, please try again later"))
                            e = 0
        except Exception as ex:
            e = 0

    def action_fetch_document_file_permission(self):
        google_drive_helper = GoogleDriveHelper()
        for rec in self:
            rec = self.env['document.file.permission'].sudo().browse(rec.id)
            if rec.google_drive_permission_id is None or rec.google_drive_permission_id is False:
                current_user = self.env['res.users'].sudo().browse(rec.res_user_id)
                try:
                    if rec.type == 'write':
                        new_permission = google_drive_helper.create_file_write_permission(rec.file_id,
                                                                                          current_user.google_email)
                        rec.write({'google_drive_permission_id': new_permission})
                    elif rec.type == 'read':
                        new_permission = google_drive_helper.create_file_read_permission(rec.file_id,
                                                                                         current_user.google_email)
                        rec.write({'google_drive_permission_id': new_permission})
                except Exception as ex:
                    a = 0

    def action_drop_document_file_permission(self):
        google_drive_helper = GoogleDriveHelper()
        for rec in self:
            rec = self.env['document.file.permission'].sudo().browse(rec.id)
            if rec.google_drive_permission_id is not None:
                try:
                    google_drive_helper.drop_file_permission(rec.file_id,
                                                             rec.google_drive_permission_id)
                    rec.write({'google_drive_permission_id': None})
                except Exception as ex:
                    a = 0

    def action_list_permission(self):
        self.ensure_one()
        google_drive_helper = GoogleDriveHelper()
        current_record = self.env['document.file.permission'].sudo().browse(self.id)
        permissions = google_drive_helper.list_permission(current_record.file_id)
        raise UserError(str(permissions))

    def action_detail_permission(self):
        self.ensure_one()
        google_drive_helper = GoogleDriveHelper()
        current_record = self.env['document.file.permission'].sudo().browse(self.id)
        permission = google_drive_helper.detail_permission(current_record.file_id,
                                                           current_record.google_drive_permission_id)
        raise UserError(str(permission))


class DocumentFilePermissionError(models.Model):
    _name = "document.file.permission.error"
    _description = "Store all pair user file permission error"

    res_user_id = fields.Integer()
    file_id = fields.Char('File Id')
    google_drive_permission_id = fields.Char()
    type = fields.Selection([('read', 'Read'), ('write', 'Write')], default='read')
    status = fields.Char('Current Status')
    error_message = fields.Char('Error Message')

    def action_drop_document_file_permission(self):
        google_drive_helper = GoogleDriveHelper()
        for rec in self:
            rec = self.env['document.file.permission.error'].sudo().browse(rec.id)
            if rec.google_drive_permission_id is not None:
                try:
                    google_drive_helper.drop_file_permission(rec.file_id,
                                                             rec.google_drive_permission_id)
                    rec.write({'google_drive_permission_id': None})
                    # sh@dowalker
                    #rec.unlink()
                except Exception as ex:
                    a = 0

    def action_list_permission(self):
        self.ensure_one()
        google_drive_helper = GoogleDriveHelper()
        current_record = self.env['document.file.permission.error'].sudo().browse(self.id)
        permissions = google_drive_helper.list_permission(current_record.file_id)
        raise UserError(str(permissions))

    def action_detail_permission(self):
        self.ensure_one()
        google_drive_helper = GoogleDriveHelper()
        current_record = self.env['document.file.permission.error'].sudo().browse(self.id)
        permission = google_drive_helper.detail_permission(current_record.file_id,
                                                           current_record.google_drive_permission_id)
        raise UserError(str(permission))

    def _process_sync_drop_permission_queue(self, row_count):
        google_drive_helper = GoogleDriveHelper()
        google_drive_helper.set_context_env(self)
        records = self.env['document.file.permission.error'].search([('error_message', '=', None)], limit=row_count)
        for e in records:
            try:
                google_drive_helper.drop_file_permission(e.file_id, e.google_drive_permission_id)
                e.unlink()
            except Exception as ex:
                print(ex)
                #e.unlink()
