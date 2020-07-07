from odoo import models, api


class Attendee(models.Model):
    _inherit = 'calendar.attendee'

    # @api.multi
    # def do_accept(self):
    #     user_ids = []
    #     for rec in self:
    #         attendee_ids = rec.event_id.attendee_ids
    #         for attendee_id in attendee_ids:
    #             partner_user_ids = attendee_id.partner_id.user_ids
    #             if partner_user_ids and len(partner_user_ids.ids) > 0:
    #                 user_ids += partner_user_ids.ids
    #     result = super(Attendee, self).do_accept()
    #     try:
    #         self.env['google.calendar'].synchronize_users_events(user_ids)
    #     except Exception as ex:
    #         a = 0
    #     return result

    # @api.multi
    # def do_decline(self):
    #     user_ids = []
    #     for rec in self:
    #         attendee_ids = rec.event_id.attendee_ids
    #         for attendee_id in attendee_ids:
    #             partner_user_ids = attendee_id.partner_id.user_ids
    #             if partner_user_ids and len(partner_user_ids.ids) > 0:
    #                 user_ids += partner_user_ids.ids
    #     result = super(Attendee, self).do_decline()
    #     try:
    #         self.env['google.calendar'].synchronize_users_events(user_ids)
    #     except Exception as ex:
    #         a = 0
    #     return result

    # @api.multi
    # def unlink(self):
    #     user_ids = []
    #     for rec in self:
    #         attendee_ids = rec.event_id.attendee_ids
    #         for attendee_id in attendee_ids:
    #             partner_user_ids = attendee_id.partner_id.user_ids
    #             if partner_user_ids and len(partner_user_ids.ids) > 0:
    #                 user_ids += partner_user_ids.ids
    #     result = super(Attendee, self).unlink()
    #     try:
    #         self.env['google.calendar'].synchronize_users_events(user_ids)
    #     except Exception as ex:
    #         a = 0
    #     return result
