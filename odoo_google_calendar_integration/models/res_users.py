from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_integration_google_calendar = fields.Boolean('Integration with Google Calendar',
                                                    compute='_compute_is_integration_google_calendar', store=False)

    def _compute_is_integration_google_calendar(self):
        self.ensure_one()
        if self.google_calendar_token and self.google_calendar_cal_id:
            self.is_integration_google_calendar = True
        else:
            self.is_integration_google_calendar = False
