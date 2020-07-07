# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import operator
from datetime import datetime, timedelta

import requests
from dateutil import parser

from addons.google_calendar.models.google_calendar import NothingToDo, SyncEvent, Create, Update, Exclude, Delete, \
    status_response
from odoo import api, fields, models, _, tools
from odoo.tools import exception_to_unicode

_logger = logging.getLogger(__name__)


class GoogleCalendar(models.AbstractModel):
    STR_SERVICE = 'calendar'
    _inherit = 'google.%s' % STR_SERVICE

    def get_event_synchro_dict(self, lastSync=False, token=False, nextPageToken=False):
        google_events_dict = {}
        return google_events_dict

    @api.model
    def set_all_tokens(self, authorization_code):
        super(GoogleCalendar, self).set_all_tokens(authorization_code)
        self.env['google.calendar'].synchronize_events(lastSync=True)

    # def update_to_google(self, oe_event, google_event):
    #     # find user list
    #     users = []
    #     for e in oe_event.attendee_ids:
    #         user_ids = e.partner_id.user_ids
    #         for user in user_ids:
    #             users.append(user)
    #     # update calendar event for each user
    #     for user in users:
    #         url = "/calendar/v3/calendars/%s/events/%s?fields=%s&access_token=%s" % (
    #             'primary', google_event['id'], 'id,updated', self.get_token_by_user(user))
    #         headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    #         data = self.generate_data(oe_event)
    #
    #         data['sequence'] = google_event.get('sequence', 0)
    #         data_json = json.dumps(data)
    #         status, content, ask_time = self.env['google.service']._do_request(url, data_json, headers, type='PATCH')
    #
    #         update_date = datetime.strptime(content['updated'], "%Y-%m-%dT%H:%M:%S.%fz")
    #         oe_event.write({'oe_update_date': update_date})
    #
    #         if self.env.context.get('curr_attendee'):
    #             self.env['calendar.attendee'].browse(self.env.context['curr_attendee']).write(
    #                 {'oe_synchro_date': update_date})
    #
    # def get_token_by_user(self, current_user):
    #     if not current_user.google_calendar_token_validity or \
    #             current_user.google_calendar_token_validity < (datetime.now() + timedelta(minutes=1)):
    #         self.do_refresh_user_token(current_user)
    #         current_user.refresh()
    #     return current_user.google_calendar_token
    #
    # def do_refresh_user_token(self, current_user):
    #     all_token = self.env['google.service']._refresh_google_token_json(current_user.google_calendar_rtoken,
    #                                                                       self.STR_SERVICE)
    #     vals = {}
    #     vals['google_%s_token_validity' % self.STR_SERVICE] = datetime.now() + timedelta(
    #         seconds=all_token.get('expires_in'))
    #     vals['google_%s_token' % self.STR_SERVICE] = all_token.get('access_token')
    #     self.env['res.users'].browse(current_user.id).sudo().write(vals)

    @api.model
    def synchronize_users_events(self, user_ids):
        if user_ids and len(user_ids) > 0:
            users = self.env['res.users'].search(
                [('google_calendar_last_sync_date', '!=', False), ('id', 'in', user_ids)])
            for user_id in users.ids:
                try:
                    resp = self.sudo(user_id).synchronize_events(lastSync=True)
                except Exception as e:
                    _logger.error("[%s] Calendar Synchro - Exception : %s !", user_id, exception_to_unicode(e))

    # ignore all leaves
    def update_events(self, lastSync=False):
        """ Synchronze events with google calendar : fetching, creating, updating, deleting, ... """
        CalendarEvent = self.env['calendar.event']
        CalendarAttendee = self.env['calendar.attendee']
        my_partner_id = self.env.user.partner_id.id
        context_novirtual = self.get_context_no_virtual()

        if lastSync:
            try:
                all_event_from_google = self.get_event_synchro_dict(lastSync=lastSync)
            except requests.HTTPError as e:
                if e.response.status_code == 410:  # GONE, Google is lost.
                    # we need to force the rollback from this cursor, because it locks my res_users but I need to write in this tuple before to raise.
                    self.env.cr.rollback()
                    self.env.user.write({'google_calendar_last_sync_date': False})
                    self.env.cr.commit()
                error_key = e.response.json()
                error_key = error_key.get('error', {}).get('message', 'nc')
                error_msg = _("Google is lost... the next synchro will be a full synchro. \n\n %s") % error_key
                raise self.env['res.config.settings'].get_config_warning(error_msg)

            my_google_attendees = CalendarAttendee.with_context(context_novirtual).search([
                ('partner_id', '=', my_partner_id),
                ('google_internal_event_id', 'in', list(all_event_from_google))
            ])
            my_google_att_ids = my_google_attendees.ids

            my_odoo_attendees = CalendarAttendee.with_context(context_novirtual).search([
                ('partner_id', '=', my_partner_id),
                ('event_id.oe_update_date', '>',
                 lastSync and fields.Datetime.to_string(lastSync) or self.get_minTime().fields.Datetime.to_string()),
                ('google_internal_event_id', '!=', False),
            ])

            my_odoo_googleinternal_records = my_odoo_attendees.read(['google_internal_event_id', 'event_id'])

            if self.get_print_log():
                _logger.info(
                    "Calendar Synchro -  \n\nUPDATE IN GOOGLE\n%s\n\nRETRIEVE FROM OE\n%s\n\nUPDATE IN OE\n%s\n\nRETRIEVE FROM GG\n%s\n\n",
                    all_event_from_google, my_google_att_ids, my_odoo_attendees.ids, my_odoo_googleinternal_records)

            for gi_record in my_odoo_googleinternal_records:
                active = True  # if not sure, we request google
                if gi_record.get('event_id'):
                    active = CalendarEvent.with_context(context_novirtual).browse(
                        int(gi_record.get('event_id')[0])).active

                if gi_record.get('google_internal_event_id') and not all_event_from_google.get(
                        gi_record.get('google_internal_event_id')) and active:
                    one_event = self.get_one_event_synchro(gi_record.get('google_internal_event_id'))
                    if one_event:
                        all_event_from_google[one_event['id']] = one_event

            my_attendees = (my_google_attendees | my_odoo_attendees)

        else:
            domain = [
                ('partner_id', '=', my_partner_id),
                ('google_internal_event_id', '!=', False),
                '|',
                ('event_id.stop', '>', fields.Datetime.to_string(self.get_minTime())),
                ('event_id.final_date', '>', fields.Datetime.to_string(self.get_minTime())),
            ]

            # Select all events from Odoo which have been already synchronized in gmail
            my_attendees = CalendarAttendee.with_context(context_novirtual).search(domain)
            all_event_from_google = self.get_event_synchro_dict(lastSync=False)

        event_to_synchronize = {}
        for att in my_attendees:
            event = att.event_id
            if 'leave' not in event.name:
                base_event_id = att.google_internal_event_id.rsplit('_', 1)[0]

                if base_event_id not in event_to_synchronize:
                    event_to_synchronize[base_event_id] = {}

                if att.google_internal_event_id not in event_to_synchronize[base_event_id]:
                    event_to_synchronize[base_event_id][att.google_internal_event_id] = SyncEvent()

                ev_to_sync = event_to_synchronize[base_event_id][att.google_internal_event_id]

                ev_to_sync.OE.attendee_id = att.id
                ev_to_sync.OE.event = event
                ev_to_sync.OE.found = True
                ev_to_sync.OE.event_id = event.id
                ev_to_sync.OE.isRecurrence = event.recurrency
                ev_to_sync.OE.isInstance = bool(event.recurrent_id and event.recurrent_id > 0)
                ev_to_sync.OE.update = event.oe_update_date
                ev_to_sync.OE.status = event.active
                ev_to_sync.OE.synchro = att.oe_synchro_date

        for event in all_event_from_google.values():
            event_id = event.get('id')
            base_event_id = event_id.rsplit('_', 1)[0]

            if base_event_id not in event_to_synchronize:
                event_to_synchronize[base_event_id] = {}

            if event_id not in event_to_synchronize[base_event_id]:
                event_to_synchronize[base_event_id][event_id] = SyncEvent()

            ev_to_sync = event_to_synchronize[base_event_id][event_id]
            ev_to_sync.GG.event = event
            ev_to_sync.GG.found = True
            ev_to_sync.GG.isRecurrence = bool(event.get('recurrence', ''))
            ev_to_sync.GG.isInstance = bool(event.get('recurringEventId', 0))
            ev_to_sync.GG.update = event.get('updated') and parser.parse(
                event['updated']) or None  # if deleted, no date without browse event
            if ev_to_sync.GG.update:
                ev_to_sync.GG.update = ev_to_sync.GG.update.replace(tzinfo=None)
            ev_to_sync.GG.status = (event.get('status') != 'cancelled')

        ######################
        #   PRE-PROCESSING   #
        ######################
        for base_event in event_to_synchronize:
            for current_event in event_to_synchronize[base_event]:
                event_to_synchronize[base_event][current_event].compute_OP(modeFull=not lastSync)
            if self.get_print_log():
                if not isinstance(event_to_synchronize[base_event][current_event].OP, NothingToDo):
                    _logger.info(event_to_synchronize[base_event])

        ######################
        #      DO ACTION     #
        ######################
        for base_event in event_to_synchronize:
            event_to_synchronize[base_event] = sorted(event_to_synchronize[base_event].items(),
                                                      key=operator.itemgetter(0))
            for current_event in event_to_synchronize[base_event]:
                self.env.cr.commit()
                event = current_event[1]  # event is an Sync Event !
                actToDo = event.OP
                actSrc = event.OP.src

                # To avoid redefining 'self', all method below should use 'recs' instead of 'self'
                recs = self.with_context(curr_attendee=event.OE.attendee_id)

                if isinstance(actToDo, NothingToDo):
                    continue
                elif isinstance(actToDo, Create):
                    if actSrc == 'GG':
                        self.create_from_google(event, my_partner_id)
                    elif actSrc == 'OE':
                        raise AssertionError("Should be never here, creation for OE is done before update !")
                    # TODO Add to batch
                elif isinstance(actToDo, Update):
                    if actSrc == 'GG':
                        recs.update_from_google(event.OE.event, event.GG.event, 'write')
                    elif actSrc == 'OE':
                        recs.update_to_google(event.OE.event, event.GG.event)
                elif isinstance(actToDo, Exclude):
                    if actSrc == 'OE':
                        recs.delete_an_event(current_event[0])
                    elif actSrc == 'GG':
                        new_google_event_id = event.GG.event['id'].rsplit('_', 1)[1]
                        if 'T' in new_google_event_id:
                            new_google_event_id = new_google_event_id.replace('T', '')[:-1]
                        else:
                            new_google_event_id = new_google_event_id + "000000"

                        if event.GG.status:
                            parent_event = {}
                            if not event_to_synchronize[base_event][0][1].OE.event_id:
                                main_ev = CalendarAttendee.with_context(context_novirtual).search(
                                    [('google_internal_event_id', '=', event.GG.event['id'].rsplit('_', 1)[0])],
                                    limit=1)
                                event_to_synchronize[base_event][0][1].OE.event_id = main_ev.event_id.id

                            if event_to_synchronize[base_event][0][1].OE.event_id:
                                parent_event['id'] = "%s-%s" % (
                                    event_to_synchronize[base_event][0][1].OE.event_id, new_google_event_id)
                                res = recs.update_from_google(parent_event, event.GG.event, "copy")
                            else:
                                recs.create_from_google(event, my_partner_id)
                        else:
                            parent_oe_id = event_to_synchronize[base_event][0][1].OE.event_id
                            if parent_oe_id:
                                CalendarEvent.browse("%s-%s" % (parent_oe_id, new_google_event_id)).with_context(
                                    curr_attendee=event.OE.attendee_id).unlink(can_be_deleted=True)

                elif isinstance(actToDo, Delete):
                    if actSrc == 'GG':
                        try:
                            # if already deleted from gmail or never created
                            recs.delete_an_event(current_event[0])
                        except requests.exceptions.HTTPError as e:
                            if e.response.status_code in (401, 410,):
                                pass
                            else:
                                raise e
                    elif actSrc == 'OE':
                        try:
                            # CalendarEvent.browse(event.OE.event_id).unlink(can_be_deleted=False)
                            CalendarEvent.browse(event.OE.event_id).unlink(can_be_deleted=True)
                        except:
                            try:
                                CalendarEvent.browse(event.OE.event_id).unlink(can_be_deleted=True)
                            except:
                                a = 0
        return True

    # ignore leaves
    def create_new_events(self):
        new_ids = []
        my_partner_id = self.env.user.partner_id.id
        my_attendees = self.env['calendar.attendee'].with_context(virtual_id=False).search(
            [('partner_id', '=', my_partner_id),
             ('google_internal_event_id', '=', False),
             '|',
             ('event_id.stop', '>', fields.Datetime.to_string(self.get_minTime())),
             ('event_id.final_date', '>', fields.Datetime.to_string(self.get_minTime())),
             ])
        for att in my_attendees:
            if 'leave' not in att.event_id.name:
                other_google_ids = [other_att.google_internal_event_id for other_att in att.event_id.attendee_ids if
                                    other_att.google_internal_event_id and other_att.id != att.id and not other_att.google_internal_event_id.startswith(
                                        '_')]
                for other_google_id in other_google_ids:
                    if self.get_one_event_synchro(other_google_id):
                        att.write({'google_internal_event_id': other_google_id})
                        break
                else:
                    if not att.event_id.recurrent_id or att.event_id.recurrent_id == 0:
                        status, response, ask_time = self.create_an_event(att.event_id)
                        if status_response(status):
                            update_date = datetime.strptime(response['updated'], "%Y-%m-%dT%H:%M:%S.%fz")
                            att.event_id.write({'oe_update_date': update_date})
                            new_ids.append(response['id'])
                            att.write({'google_internal_event_id': response['id'], 'oe_synchro_date': update_date})
                            self.env.cr.commit()
                        else:
                            _logger.warning("Impossible to create event %s. [%s] Enable DEBUG for response detail.",
                                            att.event_id.id, status)
                            _logger.debug("Response : %s", response)
        return new_ids

    def generate_data(self, event, isCreating=False):
        if event.allday:
            start_date = fields.Date.to_string(event.start_date)
            final_date = fields.Date.to_string(event.stop_date + timedelta(days=1))
            type = 'date'
            vstype = 'dateTime'
        else:
            start_date = fields.Datetime.context_timestamp(self, event.start).isoformat('T')
            final_date = fields.Datetime.context_timestamp(self, event.stop).isoformat('T')
            type = 'dateTime'
            vstype = 'date'
        attendee_list = []
        for attendee in event.attendee_ids:
            email = tools.email_split(attendee.email)
            email = email[0] if email else 'NoEmail@mail.com'
            attendee_list.append({
                'email': email,
                'displayName': attendee.partner_id.name,
                'responseStatus': attendee.state or 'needsAction',
            })

        reminders = []
        for alarm in event.alarm_ids:
            reminders.append({
                "method": "email" if alarm.alarm_type == "email" else "popup",
                "minutes": alarm.duration_minutes
            })
        data = {
            "summary": event.name or '',
            "description": event.str_description or '',
            "start": {
                type: start_date,
                vstype: None,
                'timeZone': self.env.context.get('tz') or 'UTC',
            },
            "end": {
                type: final_date,
                vstype: None,
                'timeZone': self.env.context.get('tz') or 'UTC',
            },
            "attendees": attendee_list,
            "reminders": {
                "overrides": reminders,
                "useDefault": "false"
            },
            "location": event.location or '',
            "visibility": event['privacy'] or 'public',
        }
        if event.recurrency and event.rrule:
            data["recurrence"] = ["RRULE:" + event.rrule]

        if not event.active:
            data["state"] = "cancelled"

        if not self.get_need_synchro_attendee():
            data.pop("attendees")
        if isCreating:
            other_google_ids = [other_att.google_internal_event_id for other_att in event.attendee_ids
                                if other_att.google_internal_event_id and not other_att.google_internal_event_id.startswith('_')]
            if other_google_ids:
                data["id"] = other_google_ids[0]
        return data