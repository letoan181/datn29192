from odoo import models, fields, api


class ResUsersForceUpdateGoogleEmail(models.Model):
    _name = 'res.users.force_update.google.email'

    def _default_res_users(self):
        if self._context.get('active_ids'):
            return self.env['res.users'].browse(self._context.get('active_ids'))

    res_users = fields.Many2many('res.users', string="Record", required=True, default=_default_res_users)

    def force_update_google_email_by_login(self):
        if self.user_has_groups('base.group_system'):
            self.env.cr.execute("""update res_users set google_email = login where id in %s""",
                                (tuple(self.res_users.ids),))
        # return {'type': 'ir.actions.client', 'tag': 'reload'}
