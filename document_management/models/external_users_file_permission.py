from odoo import models, fields, api
from ..utils.google_drive_helper import GoogleDriveHelper


class ExternalPermissionGeneralFile(models.Model):
    _name = 'external.users.permission'

    name = fields.Char(string='User Name', required=True)
    user_email = fields.Char(string="Google Email", required=True)
    project_file_id = fields.Many2one('document.project.file', readonly=True, string='Project File', ondelete='cascade')
    quotation_file_id = fields.Many2one('document.quotation.file', readonly=True, string='Quotation File',
                                        ondelete='cascade')
    crm_file_id = fields.Many2one('document.crm.file', readonly=True, string='CRM File', ondelete='cascade')
    file_id = fields.Char(readonly=True)
    google_drive_permission_id = fields.Char(string="Google Drive ID", readonly=True)
    type = fields.Selection([('read', 'Read'), ('write', 'Write')], required=True, default='read')
    error_google_id = fields.Char('Error Permission ID')

    def write(self, value):
        google_drive_helper = GoogleDriveHelper()
        vals = value
        # Tracking change external users
        old_name = self.name
        old_email = self.user_email
        old_type = self.type
        active = None
        if self.project_file_id:
            active = self.project_file_id
        if self.quotation_file_id:
            active = self.quotation_file_id
        if self.crm_file_id:
            active = self.crm_file_id
        result = super(ExternalPermissionGeneralFile, self).write(value)
        if 'name' in vals:
            body = "<p>Change External User Name: </p><p>" + 'From : ' + old_name + "</p><p>" + 'To : ' + self.name + '</p>'
            active.message_post(body=body)
        if 'user_email' in vals:
            body = "<p>Change External User Email: </p><p>" + 'From : ' + old_email + "</p><p>" + 'To : ' + self.user_email + '</p>'
            active.message_post(body=body)
        if 'type' in vals:
            body = "<p>Change External User Access: </p><p>" + 'From : ' + old_type + "</p><p>" + 'To : ' + self.type + '</p>'
            active.message_post(body=body)
        if self.file_id:
            if 'user_email' in vals or 'type' in vals:
                # drop old permission
                if self.google_drive_permission_id:
                    try:
                        google_drive_helper.drop_file_permission(self.file_id,
                                                                 self.google_drive_permission_id)
                        self.env.cr.execute(
                            """update external_users_permission set google_drive_permission_id = %s WHERE id=%s""",
                            (None, self.id))
                    except Exception as e:
                        """Need handle when drop error"""
                        self.env.cr.execute(
                            """update external_users_permission set error_google_id = %s WHERE id=%s""",
                            (self.google_drive_permission_id, self.id))
                # create new permission
                if self.type == 'read':
                    try:
                        new_permission = google_drive_helper.create_file_read_permission(self.file_id,
                                                                                         self.user_email)
                        # update gg drive ID
                        self.env.cr.execute(
                            """update external_users_permission set google_drive_permission_id = %s WHERE id=%s""",
                            (new_permission, self.id))
                    except Exception as e:
                        """print(e)"""
                if self.type == 'write':
                    try:
                        new_permission = google_drive_helper.create_file_write_permission(self.file_id,
                                                                                          self.user_email)
                        # update gg drive ID
                        self.env.cr.execute(
                            """update external_users_permission set google_drive_permission_id = %s WHERE id=%s""",
                            (new_permission, self.id))
                    except Exception as e:
                        """print(e)"""
        return result

    def unlink(self):
        google_drive_helper = GoogleDriveHelper()
        active = None
        for rec in self:
            if rec.project_file_id:
                active = rec.project_file_id
            if rec.quotation_file_id:
                active = rec.quotation_file_id
            if rec.crm_file_id:
                active = rec.crm_file_id
            body = "<p>Remove External User : </p><p>" + 'Name: ' + rec.name + "</p><p>" + 'Email: ' + rec.user_email + '</p>'
            active.message_post(body=body)
            if rec.google_drive_permission_id:
                try:
                    google_drive_helper.drop_file_permission(rec.file_id,
                                                             rec.google_drive_permission_id)
                except Exception as e:
                    """Need handle when drop error"""
                    drop_error = []
                    drop_error.append({
                        'name': rec.name,
                        'user_email': rec.user_email,
                        'project_file_id': rec.project_file_id,
                        'file_id': rec.file_id,
                        'quotation_file_id': rec.quotation_file_id,
                        'google_drive_permission_id': None,
                        'type': rec.type,
                        'error_google_id': rec.google_drive_permission_id,
                    })
                    # Create queue record for drop
                    self.env['external.users.permission'].sudo().create(drop_error)
        return super(ExternalPermissionGeneralFile, self).unlink()

    def _process_sync_external_permission_queue(self, row):
        google_drive_helper = GoogleDriveHelper()
        external = self.env['external.users.permission'].sudo()
        # for rec in self:
        # queue for file
        update_users = []
        users_need_update = external.search([('google_drive_permission_id', '=', False)], limit=row)
        if len(users_need_update) > 0:
            google_drive_helper.set_context_env(self)
            for record in users_need_update:
                if record.project_file_id:
                    if not record.file_id:
                        record.update(
                            {'file_id': record.project_file_id.file_id})
                    # update permission
                    if len(record.project_file_id.external_users) > 0:
                        update_users = [user.id for user in record.project_file_id.external_users]
                if record.quotation_file_id:
                    if not record.file_id:
                        record.update(
                            {'file_id': record.quotation_file_id.file_id})
                    # update permission
                    if len(record.quotation_file_id.external_users) > 0:
                        update_users = [user.id for user in record.quotation_file_id.external_users]
                if record.crm_file_id:
                    if not record.file_id:
                        record.update(
                            {'file_id': record.crm_file_id.file_id})
                    # update permission
                    if len(record.crm_file_id.external_users) > 0:
                        update_users = [user.id for user in record.crm_file_id.external_users]
                if record.error_google_id is not None:
                    try:
                        google_drive_helper.drop_file_permission(record.file_id,
                                                                 record.error_google_id)
                        record.write({'google_drive_permission_id': None})
                        if record.id not in update_users:
                            record.unlink()
                    except Exception as e:
                        'Sh@dowWalker'
                # create new permission
                if not record.google_drive_permission_id and record.id in update_users:
                    if record.type == 'read':
                        try:
                            new_permission = google_drive_helper.create_file_read_permission(record.file_id,
                                                                                             record.user_email)
                            # print(new_permission)
                            record.write(
                                {'google_drive_permission_id': new_permission})
                        except Exception as e:
                            'Sh@dowWalker'
                    if record.type == 'write':
                        try:
                            new_permission = google_drive_helper.create_file_write_permission(record.file_id,
                                                                                              record.user_email)
                            record.write(
                                {'google_drive_permission_id': new_permission})
                        except Exception as e:
                            'Sh@dowWalker'


class DocumentProjectFileInherit(models.Model):
    _inherit = 'document.project.file'

    external_users = fields.One2many('external.users.permission', 'project_file_id', string='External Users')

    def action_fetch_project_file_permission_external_user(self):
        google_drive_helper = GoogleDriveHelper()
        external = self.env['external.users.permission'].sudo()
        for rec in self:
            external_users = external.search([('project_file_id', '=', self.id)])
            # update file_id for external users
            external_users.update(
                {'file_id': self.file_id})
            # update permission
            if len(rec.external_users) > 0:
                update_users = [user.id for user in rec.external_users]
            else:
                update_users = []
            for user in external_users:
                # drop user not permission anymore or error
                if user.error_google_id is not None:
                    try:
                        google_drive_helper.drop_file_permission(user.file_id,
                                                                 user.error_google_id)
                        user.write({'google_drive_permission_id': None})
                        if user.id not in update_users:
                            user.unlink()
                    except Exception as e:
                        'Sh@dowWalker'
                # create new permission
                if not user.google_drive_permission_id and user.id in update_users:
                    if user.type == 'read':
                        try:
                            new_permission = google_drive_helper.create_file_read_permission(user.file_id,
                                                                                             user.user_email)
                            user.write(
                                {'google_drive_permission_id': new_permission})
                        except Exception as e:
                            print('Sh@dowWalker')
                    if user.type == 'write':
                        try:
                            new_permission = google_drive_helper.create_file_write_permission(user.file_id,
                                                                                              user.user_email)
                            user.write(
                                {'google_drive_permission_id': new_permission})
                        except Exception as e:
                            'Sh@dowWalker'


class DocumentQuotationFileInherit(models.Model):
    _inherit = 'document.quotation.file'

    external_users = fields.One2many('external.users.permission', 'quotation_file_id', string='External Users')

    def action_fetch_quotation_file_permission_external_user(self):
        google_drive_helper = GoogleDriveHelper()
        external = self.env['external.users.permission'].sudo()
        for rec in self:
            external_users = external.search([('quotation_file_id', '=', self.id)])
            # update file_id for external users
            external_users.update(
                {'file_id': self.file_id})
            # update permission
            if len(rec.external_users) > 0:
                update_users = [user.id for user in rec.external_users]
            else:
                update_users = []
            for user in external_users:
                # drop user not permission anymore or error
                if user.error_google_id is not None:
                    try:
                        google_drive_helper.drop_file_permission(user.file_id,
                                                                 user.error_google_id)
                        user.write({'google_drive_permission_id': None})
                        if user.id not in update_users:
                            user.unlink()
                    except Exception as e:
                        'Sh@dowWalker'
                # create new permission
                if not user.google_drive_permission_id and user.id in update_users:
                    if user.type == 'read':
                        try:
                            new_permission = google_drive_helper.create_file_read_permission(user.file_id,
                                                                                             user.user_email)
                            user.write(
                                {'google_drive_permission_id': new_permission})
                        except Exception as e:
                            """print(e)"""
                    if user.type == 'write':
                        try:
                            new_permission = google_drive_helper.create_file_write_permission(user.file_id,
                                                                                              user.user_email)
                            user.write(
                                {'google_drive_permission_id': new_permission})
                        except Exception as e:
                            """print(e)"""


class DocumentCrmFileInherit(models.Model):
    _inherit = 'document.crm.file'

    external_users = fields.One2many('external.users.permission', 'crm_file_id', string='External Users')

    def action_fetch_crm_file_permission_external_user(self):
        google_drive_helper = GoogleDriveHelper()
        external = self.env['external.users.permission'].sudo()
        for rec in self:
            external_users = external.search([('crm_file_id', '=', self.id)])
            # update file_id for external users
            external_users.update(
                {'file_id': self.file_id})
            # update permission
            if len(rec.external_users) > 0:
                update_users = [user.id for user in rec.external_users]
            else:
                update_users = []
            for user in external_users:
                # drop user not permission anymore or error
                if user.error_google_id is not None:
                    try:
                        google_drive_helper.drop_file_permission(user.file_id,
                                                                 user.error_google_id)
                        user.write({'google_drive_permission_id': None})
                        if user.id not in update_users:
                            user.unlink()
                    except Exception as e:
                        'Sh@dowWalker'
                # create new permission
                if not user.google_drive_permission_id and user.id in update_users:
                    if user.type == 'read':
                        try:
                            new_permission = google_drive_helper.create_file_read_permission(user.file_id,
                                                                                             user.user_email)
                            user.write(
                                {'google_drive_permission_id': new_permission})
                        except Exception as e:
                            """print(e)"""
                    if user.type == 'write':
                        try:
                            new_permission = google_drive_helper.create_file_write_permission(user.file_id,
                                                                                              user.user_email)
                            user.write(
                                {'google_drive_permission_id': new_permission})
                        except Exception as e:
                            """print(e)"""
