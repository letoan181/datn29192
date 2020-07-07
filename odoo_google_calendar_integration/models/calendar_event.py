from odoo import models, api, fields


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    str_description = fields.Char(compute='get_description', store=False)

    def get_description(self):
        for rec in self:
            rec.ensure_one()
            des_list = []
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if len(rec.tasks) > 0:
                for e in rec.tasks:
                    if e.host:
                        des_list.extend((e.host, ' '))
                    if e.task:
                        des_list.extend((e.task, ' '))
                    if e.deadline:
                        des_list.extend((e.deadline, ' '))
                    if e.plan:
                        des_list.extend((e.plan, ' '))
                    des_list.append('\n')
            rec.str_description = ''.join(des_list) + base_url + "/web#id=" + str(
                rec.id) + "&model=calendar.event&view_type=form&menu_id=" + str(
                rec.env.ref('calendar.mail_menu_calendar').id)

    # @api.model
    # def create(self, vals):
    #     res = super(CalendarEvent, self).create(vals)
    #     # try update on google calendar
    #     try:
    #         if 'oe_update_date' not in vals:
    #             user_ids = []
    #             attendee_ids = res.attendee_ids
    #             for attendee_id in attendee_ids:
    #                 partner_user_ids = attendee_id.partner_id.user_ids
    #                 if partner_user_ids and len(partner_user_ids.ids) > 0:
    #                     user_ids += partner_user_ids.ids
    #             self.env['google.calendar'].synchronize_users_events(user_ids)
    #     except Exception as ex:
    #        print(ex)
    #     return res

    # @api.multi
    # def write(self, vals):
    #     old_vals = copy.copy(vals)
    #     user_ids = []
    #     for rec in self:
    #         attendee_ids = rec.attendee_ids
    #         for attendee_id in attendee_ids:
    #             partner_user_ids = attendee_id.partner_id.user_ids
    #             if partner_user_ids and len(partner_user_ids.ids) > 0:
    #                 user_ids += partner_user_ids.ids
    #     res = super(CalendarEvent, self).write(vals)
    #     for rec in self.env['calendar.event'].browse(self.ids):
    #         attendee_ids = rec.attendee_ids
    #         for attendee_id in attendee_ids:
    #             partner_user_ids = attendee_id.partner_id.user_ids
    #             if partner_user_ids and len(partner_user_ids.ids) > 0:
    #                 user_ids += partner_user_ids.ids
    #     # try update on google calendar
    #     try:
    #         if 'oe_update_date' not in old_vals:
    #             self.env['google.calendar'].synchronize_users_events(user_ids)
    #     except Exception as ex:
    #         a = 0
    #     return res

    # @api.multi
    def unlink(self):
        # user_ids = []
        # for rec in self:
        #     attendee_ids = rec.attendee_ids
        #     for attendee_id in attendee_ids:
        #         partner_user_ids = attendee_id.partner_id.user_ids
        #         if partner_user_ids and len(partner_user_ids.ids) > 0:
        #             user_ids += partner_user_ids.ids
        for rec in self:
            attendee_ids = rec.attendee_ids
            for attendee_id in attendee_ids:
                try:
                    self.env['google.calendar'].delete_an_event(event_id=attendee_id.google_internal_event_id)
                except Exception as ex:
                    a = 0
        # result = super(CalendarEvent, self).unlink(can_be_deleted=True)
        # try:
        #     self.env['google.calendar'].synchronize_users_events(user_ids)
        # except Exception as ex:
        #     a = 0
        # return result
        return super(CalendarEvent, self).unlink(can_be_deleted=True)