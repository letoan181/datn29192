from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..utils.google_drive_helper import GoogleDriveHelper

GOOGLE_DRIVE_URL = 'https://drive.google.com/drive/folders/'


class DocumentDriveAccount(models.Model):
    _name = "document.google.account"
    _description = "Manage document google main account "

    name = fields.Char('Google account')
    is_use = fields.Boolean(default=False)
    general_folder_base = fields.Char()
    project_folder_base = fields.Char()
    author_code = fields.Char('Authorization Code')
    refresh_token = fields.Char('Token')
    google_drive_uri = fields.Char(compute='_compute_drive_uri', string='URI',
                                   help="The URL to generate the authorization code from Google")

    def disable_account(self):
        for record in self:
            record.sudo().write({'is_use': False})

    def active_account(self):
        for record in self:
            if not self.refresh_token:
                raise UserError(_("Can not use when not have permission.Please get token to access to account drive !"))
            google_drive_helper = GoogleDriveHelper()
            if not record.general_folder_base:
                google_drive_new_folder_general = google_drive_helper.create_file(folder_name='Document General')
                record.general_folder_base = GOOGLE_DRIVE_URL + google_drive_new_folder_general['id']
            if not record.project_folder_base:
                google_drive_new_folder_project = google_drive_helper.create_file(folder_name='Document Project')
                record.project_folder_base = GOOGLE_DRIVE_URL + google_drive_new_folder_project['id']
            self.env['document.google.account'].sudo().search([('id', '!=', record.id)]).write({'is_use': False})
            record.sudo().write({'is_use': True})

    @api.depends('author_code')
    def _compute_drive_uri(self):
        google_drive_uri = self.env['google.service']._get_google_token_uri('drive', scope=self.env[
            'google.drive.config'].get_google_scope())
        for config in self:
            config.google_drive_uri = google_drive_uri

    def confirm_setup_token(self):
        params = self.env['ir.config_parameter'].sudo()
        authorization_code_before = params.get_param('google_drive_authorization_code')
        authorization_code = self.author_code
        if authorization_code != authorization_code_before:
            refresh_token = (
                self.env['google.service'].generate_refresh_token('drive', authorization_code)
                if authorization_code else False
            )
            params.set_param('google_drive_refresh_token', refresh_token)
            self.sudo().write({'refresh_token': refresh_token})
