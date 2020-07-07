import calendar
import json
import logging
from datetime import date, datetime, timedelta

import pytz
from odoo.addons.resource.models.resource import float_to_time
from pytz import timezone

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError
from odoo.fields import Datetime
from odoo.tools import date_utils

_logger = logging.getLogger(__name__)


class ManagerAttendance(models.Model):
    _name = 'manager.attendance'
    _inherit = 'mail.thread', 'mail.activity.mixin'

    @api.model
    def get_hr_employee(self):
        group_id = self.env.ref('magenest_attendance.group_advanced_import', raise_if_not_found=False)
        user = []
        if group_id and len(group_id) > 0:
            for g_id in group_id:
                for user_id in g_id.users:
                    user.append(user_id.id, )
        return [('id', 'in', user)]

    name = fields.Char(default='TimeKeeping')
    check_in_date = fields.Datetime(string='Check In From', required=True)
    check_out_date = fields.Datetime(string='To Check Out', required=True)
    user = fields.Many2one('res.users', string='Assign To', domain=lambda self: self.get_hr_employee(), required=True)
    date = fields.Datetime(string='Working at', readonly=True)
    number_of_workday = fields.Integer('Workday Amount', required=True)
    time_zone = fields.Selection('_tz_get', string='Timezone', required=True,
                                 default=lambda self: self.env.user.tz or 'UTC')
    hour_am_from = fields.Float(string='Start Morning', required=True, index=True, default=8.0)
    hour_am_to = fields.Float(string='Work from', required=True, index=True, default=12.0)
    hour_pm_from = fields.Float(string='Start Afternoon', required=True, default=13.0)
    hour_pm_to = fields.Float(string='Work to', required=True, default=17.0)
    state = fields.Selection([
        ('outgoing', 'Outgoing'),
        ('sent', 'Sent'),
        ('cancel', 'Lock'),
    ], 'Status', readonly=True, copy=False, default='outgoing', track_visibility='onchange')

    @api.onchange('check_in_date', 'check_out_date', 'time_zone')
    def check_valid_date(self):
        if self.check_in_date and self.check_out_date and self.time_zone:
            # time onchange
            time_in = self.check_in_date.astimezone(timezone(self.time_zone))
            time_out = self.check_out_date.astimezone(timezone(self.time_zone))
            # chenh lech so gio so voi UTC
            diff_hours_tz = int(self.check_in_date.astimezone(timezone(self.time_zone)).strftime("%z")) / 100
            # if int(time_in.strftime("%H")) < diff_hours_tz:
            #     self.check_in_date = datetime(time_in.year, time_in.month, time_in.day, 00, 2, 00)
            # if int(time_out.strftime("%H")) < diff_hours_tz:
            #     self.check_out_date = datetime(time_out.year, time_out.month, time_out.day, 16, 30, 00)
            # force time when onchange datetime
            force_time_in = 7 - diff_hours_tz
            force_time_out = 23 - diff_hours_tz
            if int(time_in.strftime("%H")) != 7:
                self.check_in_date = datetime(time_in.year, time_in.month, time_in.day, int(force_time_in), 2, 00)
            if int(time_out.strftime("%H")) != 23:
                self.check_out_date = datetime(time_out.year, time_out.month, time_out.day, int(force_time_out), 30, 00)
            if self.check_in_date.astimezone(timezone(self.time_zone)).strftime("%m") != self.check_out_date.astimezone(
                    timezone(self.time_zone)).strftime("%m") or self.check_in_date.astimezone(
                timezone(self.time_zone)) > self.check_out_date.astimezone(
                timezone(self.time_zone)):
                # get the last day of month
                day = calendar.monthrange(time_in.year, time_in.month)[1]
                self.check_out_date = datetime(time_in.year, time_in.month, day, 20, 00, 00)
                warning_mess = {
                    'title': _('Warning!'),
                    'message': 'Your Time Checkout Should Be During %s or Greater Than Check In.If You Want To Continue, Just Pass This Message!.' % time_in.strftime(
                        "%m/%Y")
                }
                return {'warning': warning_mess}

    @api.model
    def _tz_get(self):
        return [(x, x) for x in pytz.all_timezones]

    @api.model
    def create(self, vals_list):
        duplicated_check_in = self.env['manager.attendance'].search(
            [('check_in_date', '<', vals_list.get('check_in_date')), (
                'check_out_date', '>', vals_list.get('check_in_date'))])
        if len(duplicated_check_in.ids) > 0:
            raise UserError(
                _('Duplicated Time Interval'))
        duplicated_check_out = self.env['manager.attendance'].search(
            [('check_in_date', '<', vals_list.get('check_out_date')), (
                'check_out_date', '>', vals_list.get('check_out_date'))])
        if len(duplicated_check_out.ids) > 0:
            raise UserError(
                _('Duplicated Time Interval'))
        return super(ManagerAttendance, self).create(vals_list)

    def write(self, vals):
        if not vals.get('state'):
            for rec in self:
                if rec.state == 'sent':
                    raise UserError(
                        _('Can Not Update Sent Time Keeping'))
        return super(ManagerAttendance, self).write(vals)

    def mark_outgoing(self):
        _logger.info("Executed")
        my_attendance_record = self.env['my.attendance'].sudo().search(
            [('check_in_date', '=', self.check_in_date), ('check_out_date', '=', self.check_out_date)])
        if my_attendance_record:
            for record in my_attendance_record:
                payslip = self.env['hr.payslip'].sudo().search([('timekeeping_id', '=', record.id)])
                if payslip.state not in ['done', 'cancel']:
                    payslip.unlink()
                    record.unlink()
        return self.write({'state': 'outgoing'})

    def mark_cancel(self):
        my_attendance_record = self.env['my.attendance'].sudo().search(
            [('check_in_date', '=', self.check_in_date), ('check_out_date', '=', self.check_out_date)])
        if my_attendance_record:
            for record in my_attendance_record:
                payslip = self.env['hr.payslip'].sudo().search([('timekeeping_id', '=', record.id)])
                if payslip:
                    payslip.write({'state': 'cancel'})
                record.write({'state': 'lock'})
        return self.write({'state': 'cancel'})

    def unlink(self):
        for rec in self:
            my_attendance_record = rec.env['my.attendance'].sudo().search(
                [('check_in_date', '=', rec.check_in_date), ('check_out_date', '=', rec.check_out_date)])
            if my_attendance_record:
                for record in my_attendance_record:
                    payslip = rec.env['hr.payslip'].sudo().search([('timekeeping_id', '=', record.id)])
                    if payslip.state not in ['done', 'cancel']:
                        payslip.unlink()
                    record.unlink()
        return super(ManagerAttendance, self).unlink()

    def get_timezone(self):
        # get timezone
        user_time_zone = pytz.UTC
        if self.time_zone:
            # change the timezone to the timezone of the user
            user_time_zone = pytz.timezone(self.time_zone)
        return user_time_zone.zone

    def get_contract_word_hour(self, employee_id, weekday, period):
        employee = self.env['hr.employee'].sudo().search([('id', '=', employee_id)])
        if employee.resource_calendar_id:
            work_hours_week = employee.resource_calendar_id
        else:
            work_hours_week = employee.user_id.company_id.resource_calendar_id if employee.user_id else None
        assign = False
        time_from = None
        if work_hours_week:
            for day in work_hours_week.attendance_ids:
                if day.dayofweek == str(weekday) and day.day_period == period:
                    assign = True
                    time_from = float_to_time(day.hour_from)
        return assign, time_from

    def get_contract_type(self, employee_id):
        employee_type = 'parttime'
        employee = self.env['hr.employee'].sudo().search([('id', '=', employee_id)])
        if employee.contract_id:
            employee_type = employee.contract_id.type
        return employee_type

    def get_overtime_assign(self, employee_id, date):
        over_time_assign = self.env['employee.overtime'].sudo().search(
            [('employee_id', '=', employee_id), ('check_in_date', '=', date)], limit=1)
        return over_time_assign

    def get_emp_leave(self, employee_id, date_in, date_out=None):
        leaves = self.env['hr.leave'].sudo().search(
            [('employee_id', '=', employee_id), ('state', '=', 'validate'), ('request_date_from', '=', date_in.date())])
        number_of_hours_leave_unpaid = 0.0
        number_of_hours_leave_paid = 0.0
        note = ''
        leave_paid_outside = False
        if len(leaves) > 0:
            for leave in leaves:
                if leave.holiday_status_id.unpaid and leave.leave_type_request_unit == 'hour' and not (
                        leave.id == self.env.ref('magenest_attendance.late_apply_submit_leave_type').id):
                    # calendar = leave.employee_id.resource_calendar_id or self.env.user.company_id.resource_calendar_id
                    if date_out is not None and leave.request_unit_hours:
                        hour_from = float_to_time(
                            abs(float(leave.request_hour_from)) - 0.5 if float(leave.request_hour_from) < 0 else float(
                                leave.request_hour_from))
                        hour_to = float_to_time(
                            abs(float(leave.request_hour_to)) - 0.5 if float(leave.request_hour_to) < 0 else float(
                                leave.request_hour_to))
                        if datetime.combine(date_in.date(), date_in.time()) < datetime.combine(date_in.date(),
                                                                                               hour_from):
                            if datetime.combine(date_out.date(), hour_to) < datetime.combine(date_out.date(),
                                                                                             date_out.time()):
                                # number_of_hours_leave_unpaid += float(leave.number_of_hours_display)
                                number_of_hours_leave_unpaid += (
                                        float(leave.request_hour_to) - float(leave.request_hour_from))
                                if len(note) > 0:
                                    note += '\nLeave from: ' + dict(leave._fields['request_hour_from'].selection).get(
                                        leave.request_hour_from) + ' to: ' + dict(
                                        leave._fields['request_hour_to'].selection).get(leave.request_hour_to)
                                else:
                                    note += 'Leave from: ' + dict(leave._fields['request_hour_from'].selection).get(
                                        leave.request_hour_from) + ' to: ' + dict(
                                        leave._fields['request_hour_to'].selection).get(leave.request_hour_to)
                            else:
                                a = 0
                        else:
                            a = 0
                            if len(note) > 0:
                                note += '\nLeave from: ' + dict(leave._fields['request_hour_from'].selection).get(
                                    leave.request_hour_from) + ' to: ' + dict(
                                    leave._fields['request_hour_to'].selection).get(leave.request_hour_to)
                            else:
                                note += 'Leave from: ' + dict(leave._fields['request_hour_from'].selection).get(
                                    leave.request_hour_from) + ' to: ' + dict(
                                    leave._fields['request_hour_to'].selection).get(leave.request_hour_to)
                        #     if datetime.combine(date_out.date(), hour_to) > datetime.combine(date_out.date(),
                        #                                                                      date_out.time()):
                        #         number_of_hours_leave += (datetime.combine(date_out.date(),
                        #                                                    date_out.time()) - datetime.combine(
                        #             date_in.date(), hour_from)).total_seconds() / 3600.0
                        # elif datetime.combine(date_in.date(), date_in.time()) > datetime.combine(date_in.date(),
                        #                                                                          hour_from):
                        #     if datetime.combine(date_out.date(), hour_to) < datetime.combine(date_out.date(),
                        #                                                                      date_out.time()):
                        #         number_of_hours_leave += (datetime.combine(date_in.date(), hour_to) - datetime.combine(
                        #             date_out.date(), date_in.time())).total_seconds() / 3600.0
                        #     else:
                        #         number_of_hours_leave += float(leave.number_of_hours_display)
                        # elif datetime.combine(date_in.date(), date_out.time()) < datetime.combine(date_in.date(),
                        #                                                                           hour_from):
                        #     number_of_hours_leave += 0
                    else:
                        number_of_hours_leave_unpaid += (float(leave.request_hour_to) - float(leave.request_hour_from))
                        if len(note) > 0:
                            note += '\nLeave from: ' + leave.date_from.astimezone(timezone(self.time_zone)).strftime(
                                "%Y-%m-%d %H:%M:%S") + ' to: ' + leave.date_to.astimezone(
                                timezone(self.time_zone)).strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            note += 'Leave from: ' + leave.date_from.astimezone(timezone(self.time_zone)).strftime(
                                "%Y-%m-%d %H:%M:%S") + ' to: ' + leave.date_to.astimezone(
                                timezone(self.time_zone)).strftime("%Y-%m-%d %H:%M:%S")
                if not leave.holiday_status_id.unpaid and leave.leave_type_request_unit == 'hour':
                    number_of_hours_leave_paid += (float(leave.request_hour_to) - float(leave.request_hour_from))
                    # check leave paid ngoai gio check out
                    # leave theo hours va nam ngoai gio checkout
                    if date_out is not None and leave.request_unit_hours:
                        hour_from = float_to_time(
                            abs(float(
                                leave.request_hour_from)) - 0.5 if float(leave.request_hour_from) < 0 else float(
                                leave.request_hour_from))
                        hour_to = float_to_time(
                            abs(float(leave.request_hour_to)) - 0.5 if float(leave.request_hour_to) < 0 else float(
                                leave.request_hour_to))
                        if datetime.combine(date_out.date(), date_out.time()) < datetime.combine(date_out.date(),
                                                                                                 hour_from):
                            leave_paid_outside = True
                        if datetime.combine(date_out.date(), hour_from) < datetime.combine(date_out.date(),
                                                                                           date_out.time()) < datetime.combine(
                            date_out.date(), hour_to):
                            leave_paid_outside = True
                    # leave theo nua ngay/ngay , neu checkout truoc 5h
                    if date_out is not None and not leave.request_unit_hours:
                        if datetime.combine(date_out.date(), date_out.time()) < datetime.combine(date_out.date(),
                                                                                                 float_to_time(
                                                                                                     self.hour_pm_to)):
                            leave_paid_outside = True
                    if date_out is None:
                        leave_paid_outside = True
        return number_of_hours_leave_unpaid, number_of_hours_leave_paid, leave_paid_outside, note

    def check_leave_apply(self, employee_id, date_in):
        # check co leave_from < check in < leave to ma da dc approve
        leaves = self.env['hr.leave'].sudo().search(
            [('employee_id', '=', employee_id), ('state', '=', 'validate'), ('request_date_from', '=', date_in.date())])
        check = False
        if len(leaves) > 0:
            for leave in leaves:
                if not leave.holiday_status_id.unpaid:
                    if leave.request_unit_hours:
                        hour_from = float_to_time(
                            abs(float(
                                leave.request_hour_from)) - 0.5 if float(leave.request_hour_from) < 0 else float(
                                leave.request_hour_from))
                        hour_to = float_to_time(
                            abs(float(leave.request_hour_to)) - 0.5 if float(leave.request_hour_to) < 0 else float(
                                leave.request_hour_to))
                        # if datetime.combine(date_in.date(), hour_from) < datetime.combine(date_in.date(),
                        #                                                                   date_in.time()) < datetime.combine(
                        #     date_in.date(), hour_to):
                        #     check = True
                        #     break
                        if datetime.combine(date_in.date(), hour_from) < datetime.combine(date_in.date(),
                                                                                          date_in.time()):
                            check = True
                            break
                    else:
                        check = True
                        break
        return check

    def get_leave_late_apply(self, employee_id, date_in):
        leaves = self.env['hr.leave'].sudo().search(
            [('employee_id', '=', employee_id), ('state', '=', 'validate'), ('request_date_from', '=', date_in.date())])
        check = False
        if len(leaves) > 0:
            for leave in leaves:
                if leave.holiday_status_id.unpaid and leave.leave_type_request_unit == 'hour':
                    if leave.id == self.env.ref('magenest_attendance.late_apply_submit_leave_type').id:
                        check = True
                        break
        return check

    def get_date_off(self, date_from, date_to):
        date_off = None
        try:
            date_off = []
            date_work_in_months = self.env['attendance.day.off'].sudo().search(
                [('set_day', '>=', date_from), ('set_day', '<=', date_to)])
            if date_work_in_months and len(date_work_in_months) > 0:
                for date in date_work_in_months:
                    date_off.append(date.set_day.strftime("%d/%m/%Y"))
            # Sunday consider date off
            day_count = (date_to - date_from).days + 1
            for single_date in [d for d in (date_from + timedelta(n) for n in range(day_count)) if
                                d <= date_to]:
                if single_date.strftime("%a") == 'Sun':
                    date_off.append(single_date.strftime("%d/%m/%Y"))
            return date_off
        except Exception as e:
            return date_off

    def get_work_hours(self, date_in, date_out):
        work_hours = 0
        if date_in < datetime.combine(date_in.date(), float_to_time(self.hour_pm_to)):
            # Ca sang
            if date_in <= datetime.combine(date_in.date(), float_to_time(self.hour_am_to)):
                # check out trong thoi gian nghi trua thi coi nhu checkout luc het h lam viec sang
                if datetime.combine(date_out.date(), float_to_time(self.hour_am_to)) <= date_out <= datetime.combine(
                        date_out.date(), float_to_time(self.hour_pm_from)):
                    date_out = datetime.combine(date_out.date(), float_to_time(self.hour_am_to))
                # Đi sớm về sớm
                if date_in <= datetime.combine(date_in.date(),
                                               float_to_time(self.hour_am_from)) and date_out <= datetime.combine(
                    date_out.date(), float_to_time(self.hour_pm_to)):
                    work_hours = (date_out - datetime.combine(date_in.date(),
                                                              float_to_time(
                                                                  self.hour_am_from))).total_seconds() / 3600.0
                # Đi muộn về sớm
                if date_in > datetime.combine(date_in.date(),
                                              float_to_time(self.hour_am_from)) and date_out <= datetime.combine(
                    date_out.date(), float_to_time(self.hour_pm_to)):
                    work_hours = (date_out - date_in).total_seconds() / 3600.0
                # Đi sớm về muộn (chăm chỉ)
                if date_in <= datetime.combine(date_in.date(),
                                               float_to_time(self.hour_am_from)) and date_out > datetime.combine(
                    date_out.date(), float_to_time(self.hour_pm_to)):
                    # work_hours = 9.25
                    work_hours = (datetime.combine(date_in.date(), float_to_time(self.hour_pm_to)) - datetime.combine(
                        date_in.date(), float_to_time(self.hour_am_from))).total_seconds() / 3600.0
                # Đi muộn về muộn (try hard)
                if date_in > datetime.combine(date_in.date(),
                                              float_to_time(self.hour_am_from)) and date_out > datetime.combine(
                    date_out.date(), float_to_time(self.hour_pm_to)):
                    work_hours = (datetime.combine(date_in.date(),
                                                   float_to_time(self.hour_pm_to)) - date_in).total_seconds() / 3600.0
            else:
                # Ca chieu
                # Đi sớm về sớm
                if date_in <= datetime.combine(date_in.date(),
                                               float_to_time(self.hour_pm_from)) and date_out <= datetime.combine(
                    date_out.date(), float_to_time(self.hour_pm_to)):
                    work_hours = (date_out - datetime.combine(date_in.date(),
                                                              float_to_time(
                                                                  self.hour_pm_from))).total_seconds() / 3600.0
                # Đi muộn về sớm
                if date_in > datetime.combine(date_in.date(),
                                              float_to_time(self.hour_pm_from)) and date_out <= datetime.combine(
                    date_out.date(), float_to_time(self.hour_pm_to)):
                    work_hours = (date_out - date_in).total_seconds() / 3600.0
                # Đi sớm về muộn (chăm chỉ)
                if date_in <= datetime.combine(date_in.date(),
                                               float_to_time(self.hour_pm_from)) and date_out > datetime.combine(
                    date_out.date(), float_to_time(self.hour_pm_to)):
                    # work_hours = 4.0
                    work_hours = (datetime.combine(date_in.date(), float_to_time(self.hour_pm_to)) - datetime.combine(
                        date_in.date(), float_to_time(self.hour_pm_from))).total_seconds() / 3600.0
                # Đi muộn về muộn (try hard)
                if date_in > datetime.combine(date_in.date(),
                                              float_to_time(self.hour_pm_from)) and date_out > datetime.combine(
                    date_out.date(), float_to_time(self.hour_pm_to)):
                    work_hours = (datetime.combine(date_in.date(),
                                                   float_to_time(self.hour_pm_to)) - date_in).total_seconds() / 3600.0
            if work_hours < 0:
                work_hours = 0
        return work_hours

    def get_timesheet(self, employee_id, date=None, start_dt=None, stop_dt=None):
        get_this_month_timesheet = 0
        get_today_timesheet = 0
        if start_dt and stop_dt:
            start = start_dt.date()
            end = stop_dt.date()
            self._cr.execute(
                'SELECT SUM(unit_amount) FROM account_analytic_line WHERE employee_id = %s AND %s <= date AND date <= %s',
                (employee_id, start, end))
            get_this_month_timesheets = self.env.cr.fetchall()
            for a in get_this_month_timesheets:
                get_this_month_timesheet = a[0]
        if date:
            today = date.date()
            self._cr.execute('SELECT SUM(unit_amount) FROM account_analytic_line WHERE employee_id = %s AND date = %s',
                             (employee_id, today))
            get_today_timesheets = self.env.cr.fetchall()
            for b in get_today_timesheets:
                get_today_timesheet = b[0]
        return get_today_timesheet, get_this_month_timesheet

    def _get_attendance_employee(self, check_in=None, check_out=None, employee_id=None):
        # standard data
        count = 0
        attendance = []
        work_days = 0
        # Get time sheet month
        get_this_month_timesheet = self.get_timesheet(employee_id=employee_id, start_dt=check_in, stop_dt=check_out)[1]
        if not get_this_month_timesheet:
            get_this_month_timesheet = 0
        # attent = self.env['hr.attendance'].sudo().search([('employee_id', '=', employee_id)])
        attendances = self.env['hr.attendance'].sudo().search(
            [('employee_id', '=', employee_id), ('check_in', '>=', check_in), ('check_in', '<=', check_out)],
            order='check_in')
        date_off = self.get_date_off(date_from=check_in.date(), date_to=check_out.date())
        for a in attendances:
            if a.check_in.strftime("%m") == check_in.strftime("%m") and (
                    a.check_in.strftime("%d/%m/%Y") not in date_off if date_off else True):
                attendance.append(a)
        for e in attendance:
            if e.check_in:
                if not e.check_out:
                    count += 1
        values = []
        late_total = 0
        late_count = 0
        late_time = 0
        all_earn = 0
        date_work = []
        over_time = 0
        over_time_holiday = 0
        over_time_assign_total = 0
        over_time_holiday_total = 0
        leave_total_up = 0
        leave_total_p = 0
        leave_count = 0
        work_hour_total = 0
        note = ''
        # work_days = len(attendance)
        work_days = self.number_of_workday
        # attendance = self.env['hr.attendance'].sudo().search(
        #     [('employee_id', '=', employee_id), ('check_in', '>=', check_in), ('check_out', '<=', check_out)])
        if len(attendance) > 0:
            for work in attendance:
                date_work.append(work.check_in.astimezone(timezone(self.get_timezone())).strftime("%d/%m/%Y"))
            day_count = (check_out - check_in).days + 1
            for single_date in [d for d in (check_in + timedelta(n) for n in range(day_count)) if
                                d <= check_out]:
                note = ''
                over_time = 0
                over_time_holiday = 0
                leave_p = ''
                work_hours_off = 0
                # truong hop ngay nghi khong nam trong ngay lam viec (VD 30/4, 1/5)
                if single_date.strftime("%d/%m/%Y") not in date_work:
                    if single_date.strftime("%a") == 'Sat':
                        color = ['#005973', '#fff']
                    elif single_date.strftime("%a") == 'Sun':
                        color = ['#293960', '#fff']
                    else:
                        color = ['', '']
                    over_time_assign_day_off = self.get_overtime_assign(employee_id, single_date.date())
                    leave_hour_day_off = self.get_emp_leave(employee_id, single_date, date_out=None)
                    get_dayoff_timesheet = self.get_timesheet(employee_id, single_date)[0]
                    if not get_dayoff_timesheet:
                        get_dayoff_timesheet = ''
                    # for assign in over_time_assign_day_off:
                    # if single_date.strftime("%d/%m/%Y") == assign.check_in_date.strftime("%d/%m/%Y"):
                    if over_time_assign_day_off:
                        if over_time_assign_day_off.type not in ['holiday']:
                            over_time = over_time_assign_day_off.duration
                            note += 'OT DayOff'
                            over_time_assign_total += over_time_assign_day_off.duration
                        else:
                            over_time_holiday = over_time_assign_day_off.duration
                            note += 'OT Holiday'
                            over_time_holiday_total += over_time_assign_day_off.duration
                    # Neu roi vao ngay le thi tinh full 8 tieng:
                    day_off_has_salary = self.env['attendance.day.off'].sudo().search([('set_day', '=', single_date.date()), ('paid_holidays', '=', True)])
                    if day_off_has_salary:
                        work_hours_off += 8
                        work_hour_total += 8
                        all_earn += 1
                    else:
                        if leave_hour_day_off[1] > 0:
                            leave_total_p += leave_hour_day_off[1]
                            leave_p = leave_hour_day_off[1]
                            if leave_hour_day_off[2]:
                                if leave_p > 8:
                                    leave_p = 8.0
                                work_hours_off += leave_p
                                work_hour_total += leave_p
                            note += 'L(paid)'
                    values.append({
                        'date': single_date.strftime("%d/%m/%Y"),
                        'day': single_date.strftime("%a"),
                        'check_in_time': '',
                        'check_out_time': '',
                        'late': '',
                        'earn': '',
                        'work_hour': work_hours_off,
                        'time_sheet': get_dayoff_timesheet,
                        'active': color,
                        'over_time': over_time,
                        'over_time_holiday': over_time_holiday,
                        'leave_up': '',
                        'leave_p': leave_p,
                        'note': note
                    })
            for a in attendance:
                # check timezone
                over_time = 0
                over_time_holiday = 0
                late = 0
                late_time = 0
                real_work_hour = 0
                leave_up = ''
                leave_p = ''
                get_day_timesheet = self.get_timesheet(employee_id, a.check_in)[0]
                if not get_day_timesheet:
                    get_day_timesheet = 0
                if a.check_out:
                    note1 = ''
                    check_in = a.check_in.astimezone(timezone(self.get_timezone()))
                    check_out = a.check_out.astimezone(timezone(self.get_timezone()))
                    # Format check in , check out
                    check_in = datetime.combine(check_in.date(), check_in.time())
                    check_out = datetime.combine(check_out.date(), check_out.time())
                    # compute work hours
                    work_hours = self.get_work_hours(date_in=check_in, date_out=check_out)
                    # Just check late when employee has assign working in this day.
                    if check_in < datetime.combine(check_in.date(), float_to_time(self.hour_am_to)) and \
                            self.get_contract_word_hour(employee_id, check_in.weekday(), 'morning')[
                                0] and not self.get_leave_late_apply(employee_id,
                                                                     check_in) and not self.check_leave_apply(
                        employee_id, check_in):
                        # Compute late base on time assign in Working Hours assign
                        hour_from = self.get_contract_word_hour(employee_id, check_in.weekday(), 'morning')[1]
                        late = datetime.combine(check_in.date(), check_in.time()) - datetime.combine(check_in.date(),
                                                                                                     hour_from)
                        # if late > 120 , late = 0
                        if round(late.total_seconds() / 60, 2) > 120:
                            late = 0
                            note1 = 'Late > 120p,'
                    else:
                        if self.get_contract_word_hour(employee_id, check_in.weekday(), 'afternoon')[
                            0] and not self.get_leave_late_apply(employee_id, check_in) and not self.check_leave_apply(
                            employee_id, check_in):
                            hour_from = self.get_contract_word_hour(employee_id, check_in.weekday(), 'afternoon')[1]
                            late = datetime.combine(check_in.date(), check_in.time()) - datetime.combine(
                                check_in.date(), hour_from)
                            # if late > 120 , late = 0
                            if round(late.total_seconds() / 60, 2) > 120:
                                late = 0
                                note1 = 'Late > 120p,'
                    over_time_assign = self.get_overtime_assign(a.employee_id.id, check_in.date())
                    if over_time_assign:
                        if over_time_assign.type not in ['holiday']:
                            over_time = over_time_assign.duration
                            note1 = 'OT Working-Day,'
                            over_time_assign_total += over_time_assign.duration
                        else:
                            over_time_holiday = over_time_assign.duration
                            note1 = 'OT Holiday,'
                            over_time_holiday_total += over_time_assign.duration

                    note = note1
                    if late != 0:
                        if late.days >= 0:
                            late_time = round(late.total_seconds() / 60, 2) // 1
                            late_total += late_time
                            late_count += 1
                        else:
                            late_time = 0
                    if check_in <= datetime.combine(check_in.date(),
                                                    float_to_time(
                                                        self.hour_pm_from)) <= check_out and check_in < datetime.combine(
                        check_in.date(), float_to_time(self.hour_am_to)):
                        # tru h nghi trua ra
                        # work_hours -= 1.25
                        work_hours -= (datetime.combine(check_in.date(),
                                                        float_to_time(self.hour_pm_from)) - datetime.combine(
                            check_in.date(), float_to_time(self.hour_am_to))).total_seconds() / 3600.0
                    # earn = round(round(work_hours, 2) / 8, 2)
                    real_work_hour = work_hours
                    if real_work_hour > 8:
                        real_work_hour = 8.0
                    leave_hour = self.get_emp_leave(a.employee_id.id, check_in, check_out)
                    if leave_hour[0] > 0:
                        leave_total_up += leave_hour[0]
                        leave_count += 1
                        leave_up = leave_hour[0]
                        # real_work_hour -= leave_hour
                        # if real_work_hour < 0:
                        #     real_work_hour = 0
                        note += ' L(Unpaid) - \n' + leave_hour[3]
                    if leave_hour[1] > 0:
                        leave_total_p += leave_hour[1]
                        # leave_count += 1
                        leave_p = leave_hour[1]
                        if leave_hour[2]:
                            # work_hours += leave_p
                            # if work_hours > 8:
                            #     work_hours = 8.0
                            note += 'WHELP\n' + leave_hour[3]
                        # real_work_hour -= leave_hour
                        # if real_work_hour < 0:
                        #     real_work_hour = 0
                        else:
                            note += ' L(Paid)\n' + leave_hour[3]
                        # note += ' ,L(Paid)'
                    # work_hour_total += real_work_hour
                    # earn = real_work_hour / 8
                    work_hour_total += round(work_hours, 2)
                    earn = work_hours / 8
                    if earn > 1:
                        earn = 1.0
                    earn = round(earn, 2)
                    all_earn += earn
                    all_earn = round(all_earn, 2)
                    if a.check_in.strftime("%a") == 'Sat':
                        color1 = ['#005973', '#fff']
                    elif a.check_in.strftime("%a") == 'Sun':
                        color1 = ['#293960', '#fff']
                    else:
                        color1 = ['', '']
                    values.append({
                        'date': check_in.strftime("%d/%m/%Y"),
                        'day': check_in.strftime("%a"),
                        'check_in_time': check_in.strftime("%H:%M"),
                        'check_out_time': check_out.strftime("%H:%M"),
                        'late': late_time,
                        'earn': earn,
                        'work_hour': round(work_hours, 2),
                        'time_sheet': get_day_timesheet,
                        'active': color1,
                        'over_time': over_time,
                        'over_time_holiday': over_time_holiday,
                        'leave_up': leave_up,
                        'leave_p': leave_p,
                        'note': note
                    })
                # Quên Check Out
                else:
                    check_in = a.check_in.astimezone(timezone(self.get_timezone()))
                    check_in = datetime.combine(check_in.date(), check_in.time())
                    if check_in < datetime.combine(check_in.date(), float_to_time(self.hour_am_to)) and \
                            self.get_contract_word_hour(employee_id, check_in.weekday(), 'morning')[
                                0] and not self.get_leave_late_apply(employee_id, check_in):
                        hour_from = self.get_contract_word_hour(employee_id, check_in.weekday(), 'morning')[1]
                        late = datetime.combine(check_in.date(), check_in.time()) - datetime.combine(check_in.date(),
                                                                                                     hour_from)
                        # if late > 120 , late = 0
                        if round(late.total_seconds() / 60, 2) > 120:
                            late = 0
                            note = 'Late > 120p,'
                    else:
                        if self.get_contract_word_hour(employee_id, check_in.weekday(), 'afternoon')[
                            0] and not self.get_leave_late_apply(employee_id, check_in):
                            hour_from = self.get_contract_word_hour(employee_id, check_in.weekday(), 'afternoon')[1]
                            late = datetime.combine(check_in.date(), check_in.time()) - datetime.combine(
                                check_in.date(), hour_from)
                            # if late > 120 , late = 0
                            if round(late.total_seconds() / 60, 2) > 120:
                                late = 0
                                note = 'Late > 120p,'
                    if late != 0:
                        if late.days >= 0:
                            late_time = round(late.total_seconds() / 60, 2) // 1
                            late_total += late_time
                            late_count += 1
                        else:
                            late_time = 0
                    work_type = self.get_contract_type(a.employee_id.id)
                    # employee full-time must work at least 12 session per week
                    earn = 0
                    work_hours = 0
                    if work_type == 'fulltime':
                        earn = 0.5
                        work_hours = 4
                        # work_hour_total += 4.0
                        note = 'Full-Time Policy'
                    if work_type == 'parttime':
                        earn = 0.25
                        work_hours = 2
                        # work_hour_total += 2.0
                        note = 'Part-Time Policy'
                    leave_hour = self.get_emp_leave(a.employee_id.id, check_in)
                    if leave_hour[0] > 0:
                        leave_total_up += leave_hour[0]
                        leave_count += 1
                        leave_up = leave_hour[0]
                        note += ' ,L(Unpaid)\n' + leave_hour[3]
                    if leave_hour[1] > 0:
                        leave_total_p += leave_hour[1]
                        # leave_count += 1
                        leave_p = leave_hour[1]
                        if leave_hour[2]:
                            # work_hours += leave_p
                            # if work_hours > 8:
                            #     work_hours = 8.0
                            note += ',WHELP\n' + leave_hour[3]
                        else:
                            note += ' ,L(Paid)\n' + leave_hour[3]
                        # note += ' ,L(Paid)'
                    all_earn += earn
                    work_hour_total += work_hours
                    if a.check_in.strftime("%a") == 'Sat':
                        color1 = ['#005973', '#fff']
                    elif a.check_in.strftime("%a") == 'Sun':
                        color1 = ['#293960', '#fff']
                    else:
                        color1 = ['', '']
                    over_time_assign = self.get_overtime_assign(a.employee_id.id, check_in.date())
                    if over_time_assign:
                        if over_time_assign.type not in ['holiday']:
                            over_time = over_time_assign.duration
                            note += ',OT'
                            over_time_assign_total += over_time_assign.duration
                        else:
                            over_time_holiday = over_time_assign.duration
                            note += ',OT Holiday'
                            over_time_holiday_total += over_time_assign.duration
                    values.append({
                        'date': a.check_in.strftime("%d/%m/%Y"),
                        'day': a.check_in.strftime("%a"),
                        # 'check_in_time': check_in.strftime("%H:%M:%S"),
                        'check_in_time': check_in.strftime("%H:%M"),
                        'check_out_time': '',
                        'late': late_time,
                        'earn': earn,
                        'work_hour': work_hours,
                        'time_sheet': get_day_timesheet,
                        'active': color1,
                        'over_time': over_time,
                        'over_time_holiday': over_time_holiday,
                        'leave_up': leave_up,
                        'leave_p': leave_p,
                        'note': note
                    })
            values.append({
                'lose_checkout': count,
                'late_hour': round(late_total / 60, 2),
                'all_earn': round(all_earn, 2),
                'late_total': round(late_total, 2),
                'late_amount': round(late_count, 2),
                'over_time_assign': over_time_assign_total,
                'over_time_holiday': over_time_holiday_total,
                'leave_total_up': leave_total_up,
                'leave_total_p': leave_total_p,
                'leave_count': leave_count,
                'work_hour_total': round(work_hour_total, 2),
                'work_days': work_days,
                'time_sheet_total': get_this_month_timesheet,
            })
        return values

    def takeSecond(self, elem):
        return elem['date']

    def handle_single_attandance(self, employees=None):
        data = {}
        count = 0
        My_attendance = self.env['my.attendance'].sudo()
        if employees:
            for user in employees:
                # if user.user_id:
                template = None
                if user:
                    values = self._get_attendance_employee(self.check_in_date, self.check_out_date, user.id)
                    # values = self._get_attendance_employee(self.check_in_date, self.check_out_date, 56)
                    if len(values) > 0:
                        count += 1
                        data.update({
                            'name': user.name,
                            'department': user.department_id.name,
                            'em_id': user.device_id,
                            'month': self.check_in_date.month,
                            'year': self.check_in_date.year,
                            'late_amount': values[len(values) - 1]['late_amount'],
                            'late_total': values[len(values) - 1]['late_total'],
                            'late_hour': values[len(values) - 1]['late_hour'],
                            'all_earn': values[len(values) - 1]['all_earn'],
                            'lose_checkout': values[len(values) - 1]['lose_checkout'],
                            'over_time_assign': values[len(values) - 1]['over_time_assign'],
                            'over_time_holiday': values[len(values) - 1]['over_time_holiday'],
                            'leave_total_up': values[len(values) - 1]['leave_total_up'],
                            'leave_total_p': values[len(values) - 1]['leave_total_p'],
                            'leave_count': values[len(values) - 1]['leave_count'],
                            'work_hour_total': values[len(values) - 1]['work_hour_total'],
                            'work_days': values[len(values) - 1]['work_days'],
                            'time_sheet_total': values[len(values) - 1]['time_sheet_total'],
                        })
                        values.pop(len(values) - 1)
                        values.sort(key=self.takeSecond)
                        template = self.env.ref('magenest_attendance.email_timekeeping').render({
                            'body': values,
                            'data': data
                        }, engine='ir.qweb', minimal_qcontext=True)
                        # Mail = self.env['mail.mail'].sudo()
                        # mail = Mail.create({
                        #     'author_id': self.user.partner_id.id,
                        #     'subject': 'Magenest Timekeeping' + str(self.check_in_date.month) + '/' + str(self.check_in_date.year),
                        #     'email_to': user.user_id.login,
                        #     'body_html': template
                        # })
                        # if mail:
                        #     #mail.send(auto_commit=False, raise_exception=False)
                        #     'ir.Cron'
                    if count > 0:
                        att = My_attendance.create({
                            'name': 'Timekeeping' + '-' + str(self.check_in_date.month) + '/' + str(
                                self.check_in_date.year) + '-' + user.name,
                            'check_in_date': self.check_in_date,
                            'check_out_date': self.check_out_date,
                            'user_create': self.user.id,
                            'employee_id': user.id,
                            'view': template
                        })
                        # Send messages to notify users
                        if user.user_id and att:
                            post_vars = {'subject': att.name,
                                         'body': "Received" + 'Timekeeping' + '-' + str(
                                             self.check_in_date.month) + '/' + str(
                                             self.check_in_date.year),
                                         'partner_ids': [user.user_id.partner_id.id], }
                            thread_pool = att.env.get('mail.thread')
                            att.message_post(
                                type="notification",
                                subtype="mt_comment",
                                **post_vars)
                        work_type = self.get_contract_type(user.id)
                        if work_type == 'fulltime':
                            day_of_month = self.number_of_workday
                            day_off = 1
                        else:
                            day_of_month = self.number_of_workday / 2
                            day_off = 0
                        Payslips = self.env['hr.payslip'].sudo()
                        contract = self.env['hr.contract'].sudo().search(
                            [('employee_id', '=', user.id), ('state', '=', 'open')])
                        if contract:
                            contract_id = contract.id
                            hours_per_day = user.resource_calendar_id.hours_per_day
                            payslip = Payslips.create({
                                'name': 'Salary Slip of ' + user.name + ' for - ' + self.check_in_date.strftime(
                                    "%m/%Y"),
                                'employee_id': user.id,
                                'contract_id': contract_id,
                                'number_work_day_month': day_of_month,
                                'date_from': self.check_in_date,
                                'date_to': self.check_out_date,
                                'timekeeping_id': att.id,
                                'timekeeping_count': 1,
                                'number_day_off_allow_month': day_off,
                                'over_time_normal_day': (data['over_time_assign']),
                                'over_time_holiday': (data['over_time_holiday']),
                                'leave': (data['leave_total_up']),
                                'late_total': data['late_total'] * 1000,
                                'worked_days_line_ids': [(0, 0, {
                                    # 'name': 'Time Rate All Month',
                                    # 'code': 'WORK100',
                                    'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id,
                                    'number_of_days': data['work_days'],
                                    'number_of_hours': data['work_hour_total'],
                                    'contract_id': contract_id
                                })]
                            })
                            if not payslip.struct_id:
                                payslip.write({
                                    'struct_id': payslip.contract_id.struct_id.id
                                })
                            # payslip.compute_sheet()
                        # else:
                        #     Payslips.create({
                        #         'name': 'Salary Slip of ' + user.name + ' for - ' + self.check_in_date.strftime(
                        #             "%m/%Y"),
                        #         'employee_id': user.id,
                        #         'number_work_day_month': day_of_month,
                        #         'date_from': self.check_in_date,
                        #         'date_to': self.check_out_date,
                        #         'timekeeping_id': att.id,
                        #         'timekeeping_count': 1,
                        #         'number_day_off_allow_month': day_off,
                        #         'over_time_normal_day': (data['over_time_assign']),
                        #         'over_time_holiday': (data['over_time_holiday']),
                        #         'leave': (data['leave_total_up']),
                        #         'late_total': data['late_total'] * 1000,
                        #         'worked_days_line_ids': [(0, 0, {
                        #             # 'name': 'Time Rate All Month',
                        #             # 'code': 'WORK100',
                        #             'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id,
                        #             'number_of_days': data['work_days'],
                        #             'number_of_hours': data['work_hour_total'],
                        #         })]
                        #     })
            return True

    def send_sheet_to_employee(self):
        _logger.info("Executed")
        # res = super(ManagerAttendance, self).create()
        now = Datetime.now()
        if not self.date:
            self.write({
                'date': now
            })
        # Create record in my attendance
        My_attendance = self.env['my.attendance'].sudo()
        # email
        # employee = self.env['hr.employee'].sudo().search([('user_id', '!=', False)])
        employee = self.env['hr.employee'].sudo().search([('device_id', '!=', False)])
        data = {}
        count = 0
        for user in employee:
            # if user.user_id:
            template = None
            if user:
                values = self._get_attendance_employee(self.check_in_date, self.check_out_date, user.id)
                # values = self._get_attendance_employee(self.check_in_date, self.check_out_date, 56)
                if len(values) > 0:
                    count += 1
                    data.update({
                        'name': user.name,
                        'department': user.department_id.name,
                        'em_id': user.device_id,
                        'month': self.check_in_date.month,
                        'year': self.check_in_date.year,
                        'late_amount': values[len(values) - 1]['late_amount'],
                        'late_total': values[len(values) - 1]['late_total'],
                        'late_hour': values[len(values) - 1]['late_hour'],
                        'all_earn': values[len(values) - 1]['all_earn'],
                        'lose_checkout': values[len(values) - 1]['lose_checkout'],
                        'over_time_assign': values[len(values) - 1]['over_time_assign'],
                        'over_time_holiday': values[len(values) - 1]['over_time_holiday'],
                        'leave_total_up': values[len(values) - 1]['leave_total_up'],
                        'leave_total_p': values[len(values) - 1]['leave_total_p'],
                        'leave_count': values[len(values) - 1]['leave_count'],
                        'work_hour_total': values[len(values) - 1]['work_hour_total'],
                        'work_days': values[len(values) - 1]['work_days'],
                        'time_sheet_total': values[len(values) - 1]['time_sheet_total'],
                    })
                    values.pop(len(values) - 1)
                    values.sort(key=self.takeSecond)
                    template = self.env.ref('magenest_attendance.email_timekeeping').render({
                        'body': values,
                        'data': data
                    }, engine='ir.qweb', minimal_qcontext=True)
                    # Mail = self.env['mail.mail'].sudo()
                    # mail = Mail.create({
                    #     'author_id': self.user.partner_id.id,
                    #     'subject': 'Magenest Timekeeping' + str(self.check_in_date.month) + '/' + str(self.check_in_date.year),
                    #     'email_to': user.user_id.login,
                    #     'body_html': template
                    # })
                    # if mail:
                    #     #mail.send(auto_commit=False, raise_exception=False)
                    #     'ir.Cron'
                if count > 0:
                    att = My_attendance.create({
                        'name': 'Timekeeping ' + '-' + str(self.check_in_date.month) + '/' + str(
                            self.check_in_date.year) + '-' + user.name,
                        'check_in_date': self.check_in_date,
                        'check_out_date': self.check_out_date,
                        'user_create': self.user.id,
                        'employee_id': user.id,
                        'view': template
                    })
                    # Send messages to notify users
                    if user.user_id and att:
                        post_vars = {'subject': att.name,
                                     'body': "Received " + 'Timekeeping' + '-' + str(
                                         self.check_in_date.month) + '/' + str(
                                         self.check_in_date.year),
                                     'partner_ids': [user.user_id.partner_id.id], }
                        thread_pool = att.env.get('mail.thread')
                        att.message_post(
                            type="notification",
                            subtype="mt_comment",
                            **post_vars)
                    work_type = self.get_contract_type(user.id)
                    if work_type == 'fulltime':
                        day_of_month = self.number_of_workday
                        day_off = 1
                    else:
                        day_of_month = self.number_of_workday / 2
                        day_off = 0
                    Payslips = self.env['hr.payslip'].sudo()
                    contract = self.env['hr.contract'].sudo().search(
                        [('employee_id', '=', user.id), ('state', '=', 'open')], limit=1)
                    if contract:
                        contract_id = contract.id
                        hours_per_day = user.resource_calendar_id.hours_per_day
                        payslip = Payslips.create({
                            'name': 'Salary Slip of ' + user.name + ' for - ' + self.check_in_date.strftime("%m/%Y"),
                            'employee_id': user.id,
                            'contract_id': contract_id,
                            'number_work_day_month': day_of_month,
                            'date_from': self.check_in_date,
                            'date_to': self.check_out_date,
                            'timekeeping_id': att.id,
                            'timekeeping_count': 1,
                            'number_day_off_allow_month': day_off,
                            'over_time_normal_day': (data['over_time_assign']),
                            'over_time_holiday': (data['over_time_holiday']),
                            'leave': (data['leave_total_up']),
                            'late_total': data['late_total'] * 1000,
                            'worked_days_line_ids': [(0, 0, {
                                # 'name': 'Time Rate All Month',
                                # 'code': 'WORK100',
                                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id,
                                'number_of_days': data['work_days'],
                                'number_of_hours': data['work_hour_total'],
                                'contract_id': contract_id
                            })]
                        })
                        if not payslip.struct_id:
                            payslip.write({
                                'struct_id': payslip.contract_id.struct_id.id
                            })
                        # payslip.compute_sheet()
                    # else:
                    #     Payslips.create({
                    #         'name': 'Salary Slip of ' + user.name + ' for - ' + self.check_in_date.strftime(
                    #             "%m/%Y"),
                    #         'employee_id': user.id,
                    #         'number_work_day_month': day_of_month,
                    #         'date_from': self.check_in_date,
                    #         'date_to': self.check_out_date,
                    #         'timekeeping_id': att.id,
                    #         'timekeeping_count': 1,
                    #         'number_day_off_allow_month': day_off,
                    #         'over_time_normal_day': (data['over_time_assign']),
                    #         'over_time_holiday': (data['over_time_holiday']),
                    #         'leave': (data['leave_total_up']),
                    #         'late_total': data['late_total'] * 1000,
                    #     })
        if count > 0:
            self.write({'state': 'sent'})
        else:
            raise UserError(
                _('Not Have Any Employee Working In your Duration.Please Config Your Time And Try Again!'))

        return True


class ManagerMyAttendance(models.Model):
    _name = 'my.attendance'
    _inherit = 'mail.thread', 'mail.activity.mixin'

    name = fields.Char()
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=True)
    check_in_date = fields.Date(string='Check In From')
    check_out_date = fields.Date(string='To Check Out')
    user_create = fields.Many2one('res.users', 'Create By')
    view = fields.Html(string='Body', sanitize_attributes=False, readonly=True)
    time_feed_back = fields.One2many('timekeeping.line', 'timekeeping_id', 'TimeKeeping FeedBack')
    state = fields.Selection([
        ('time_keeping', 'Data Feed Back'),
        ('salary', 'Salary Feed Back'),
        ('done', 'Done'),
        ('lock', 'Lock'),
    ], 'Status', default='time_keeping')
    salary_detail = fields.Html(string='Salary', sanitize_attributes=False, readonly=True)
    is_feed_back = fields.Boolean(compute='check_feed_back', store=True)
    color = fields.Integer(default=10)
    # info work time
    employee_info = fields.Text(compute="_get_work_info_employee")

    @api.depends('employee_id')
    def _get_work_info_employee(self):
        for rec in self:
            if rec.employee_id:
                employee = self.env['hr.employee'].sudo().search([('id', '=', rec.employee_id.id)])
                data = []
                if employee.resource_calendar_id:
                    work_hours_week = employee.resource_calendar_id
                else:
                    work_hours_week = employee.user_id.company_id.resource_calendar_id if employee.user_id else None
                if work_hours_week:
                    for day in work_hours_week.attendance_ids:
                        data.append({
                            'day': self.dayNameFromWeekday(int(day.dayofweek)),
                            'from': tools.format_duration(day.hour_from),
                            'to': tools.format_duration(day.hour_to)
                        })
                type = ''
                if rec.sudo().employee_id.contract_id:
                    if rec.sudo().employee_id.contract_id.type == 'parttime':
                        type = 'Part-time'
                    else:
                        type = 'Full-Time',
                info = {
                    'title': _('Employee WorkTime Info'),
                    'content': [{
                        'type': type,
                        'work_time': data
                    }]
                }
                rec.employee_info = json.dumps(info, default=date_utils.json_default)
            else:
                rec.employee_info = json.dumps(False)

    def dayNameFromWeekday(self, weekday):
        if weekday == 0:
            return "Monday"
        if weekday == 1:
            return "Tuesday"
        if weekday == 2:
            return "Wednesday"
        if weekday == 3:
            return "Thursday"
        if weekday == 4:
            return "Friday"
        if weekday == 5:
            return "Saturday"
        if weekday == 6:
            return "Sunday"

    def write(self, vals):
        if 'view' in vals:
            if self._uid != 1:
                if not self.user_has_groups('magenest_attendance.group_advanced_import'):
                    raise UserError(_('You Are Not In Import Bio Group. Please Contact With Admin!'))
        return super(ManagerMyAttendance, self).write(vals)

    def unlink(self):
        if self._uid != 1:
            if not self.user_has_groups('magenest_attendance.group_advanced_import'):
                raise UserError(_('You Are Not In Import Bio Group. Please Contact With Admin!'))
        for rec in self:
            payslip = rec.env['hr.payslip'].sudo().search([('timekeeping_id', '=', rec.id)])
            if payslip.state not in ['done', 'cancel']:
                payslip.unlink()
        return super(ManagerMyAttendance, self).unlink()

    @api.depends('time_feed_back')
    def check_feed_back(self):
        for rec in self:
            rec.is_feed_back = False
            if rec.time_feed_back:
                if len(rec.time_feed_back) > 0:
                    rec.is_feed_back = True

    def action_call_attendance_list(self):
        views = [(
            self.env.ref('magenest_attendance.view_my_attendance_kanban').id, 'kanban')]
        if self.user_has_groups('magenest_attendance.group_advanced_import'):
            domain = []
        else:
            users = self.env['res.users'].search([('id', '=', self._uid)])
            employee_id = []
            for a in users.employee_ids:
                employee_id.append(a.id)
            domain = [('employee_id', 'in', employee_id), ('state', '!=', 'lock')]

        action = {"name": "My Timekeeping", "type": "ir.actions.act_window", "view_mode": "kanban",
                  "context": {"create": False},
                  "res_model": "my.attendance", 'domain': domain, 'view_id': False,
                  'views': views}
        return action

    def action_call_all_attendance_list(self):
        views = [(
            self.env.ref('magenest_attendance.view_my_attendance_kanban').id, 'kanban')]

        action = {"name": "My Timekeeping", "type": "ir.actions.act_window", "view_mode": "kanban",
                  "context": {"create": False},
                  "res_model": "my.attendance", 'domain': [], 'view_id': False,
                  'views': views}
        return action

    def get_my_attendance_filter(self):
        domain = []
        if self.user_has_groups('magenest_attendance.group_advanced_import'):
            domain = [('check_in', '>=', self.check_in_date), ('check_out', '<=', self.check_out_date),
                      ('employee_id', '=', self.employee_id.id)]
        else:
            users = self.env['res.users'].search([('id', '=', self._uid)])
            if len(users.employee_ids.ids) > 0:
                domain = [('check_in', '>=', self.check_in_date), ('check_out', '<=', self.check_out_date),
                          ('employee_id', '=', users.employee_ids.ids[0])]
        views = [(
            self.env.ref('hr_attendance.view_attendance_tree').id, 'list')]
        action = {"name": "My Attendance", "type": "ir.actions.act_window", "view_mode": "list",
                  "context": {"create": False},
                  "res_model": "hr.attendance", 'domain': domain, 'view_id': False,
                  'views': views}
        return action

    def view_timekeeping_template(self):
        views = [(
            self.env.ref('magenest_attendance.view_my_attendance_form').id, 'form')]
        action = {"name": "My Attendance", "type": "ir.actions.act_window", "view_mode": "form",
                  "context": {"create": False},
                  "res_model": "my.attendance", 'view_id': False, 'res_id': self.id,
                  'views': views}
        return action


class ManagerOvertime(models.Model):
    _name = 'employee.overtime'
    _rec_name = 'employee_id'
    name = fields.Char()
    assign_to = fields.Many2one('res.users', 'Create By', default=lambda self: self._uid)
    department = fields.Many2one('hr.department', 'Department', compute='_compute_department', store=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    employee_location = fields.Many2one('company.location', related='employee_id.employee_location', store=True)
    check_in_date = fields.Date(string='From', required=True)
    duration = fields.Float('Duration', digits=(2, 2), required=True, default=2)
    type = fields.Selection([('evening', 'Evening'), ('day_off', 'Day-Off'), ('holiday', 'Holiday')], required=True,
                            default='evening')
    description = fields.Char(string='Description')

    # employee_not_available
    employee_available = fields.Many2many(
        comodel_name='hr.employee', string='Employee available',
        compute='_compute_employee_available', store=False)

    _sql_constraints = [
        ('employee_check_in_uniq', 'UNIQUE(check_in_date,employee_id)', "An employee can overtime 1 time per day only"),
    ]

    @api.model
    def default_get(self, fields):
        rec = super(ManagerOvertime, self).default_get(fields)
        rec.update({
            'duration': 2
        })
        if 'check_in_date' not in rec:
            rec['check_in_date'] = date.today()
        return rec

    @api.depends('assign_to')
    def _compute_employee_available(self):
        current_user_employee_id = 0
        employee_ids = self.env['res.users'].browse(self._uid).employee_ids
        if len(employee_ids) > 0:
            current_user_employee_id = employee_ids[0].id
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                rec.employee_available = self.env['hr.employee'].search([])
            elif current_user_employee_id > 0:
                rec.employee_available = self.env['hr.employee'].browse(current_user_employee_id).child_ids
                rec.employee_available += employee_ids
                rec.employee_available += self.env['hr.employee'].browse(
                    current_user_employee_id).can_add_overtime_users.employee_ids
            else:
                rec.employee_available = employee_ids

    @api.depends('assign_to')
    def _compute_department(self):
        for rec in self:
            if rec.assign_to:
                if len(rec.assign_to.employee_ids.ids) > 0:
                    rec.department = rec.assign_to.employee_ids[0].department_id
            else:
                rec.department = False

    @api.onchange('duration')
    def on_change_duration(self):
        if self.duration and self.duration > 12:
            self.duration = 12.0
        if self.duration and self.duration < 1:
            self.duration = 1.0

        # Disable date in past,can not choose date in past from date widget,just add options="{'datepicker':{'disable_past_date': True}}" in the date field
        #
        # if self.check_in_date and str(self.check_in_date) < str(date.today()):
        #     self.check_in_date = date.today()
        #     return {
        #         'warning': {
        #             'title': "Warning",
        #             'message': "You Can Not Create Over Time In The Past",
        #         }
        #     }
        # return {
        #     'warning': {
        #         'title': "Warning",
        #         'message': "You Can Not Create Over Time In The Past",
        #     }
        # }


class ManagerTimeFeedBack(models.Model):
    _name = 'timekeeping.line'
    date = fields.Datetime('Date')
    wrong_value = fields.Selection(
        [('date', 'Time In/Out'), ('late', 'Late'), ('timework', 'Time Work'), ('rate', 'Rate'),
         ('over_time', 'Over Time'), ('salary', 'Salary Total'), ('bonus', 'Bonus'), ('fine', 'Late Total')],
        string='Wrong Value', )
    state = fields.Selection([
        ('draft', 'To Approve'),
        ('confirm', 'Approved'),
        ('refuse', 'Refuse'),
    ], 'Status', default='draft', track_visibility='onchange', readonly=True)
    description = fields.Text(required=True)
    manager_note = fields.Text(string='Note By Manager')
    timekeeping_id = fields.Many2one('my.attendance', readonly=True, copy=False)
    note_permission = fields.Boolean(compute='_get_permission_groups')

    @api.depends('manager_note')
    def _get_permission_groups(self):
        for rec in self:
            if self.env.user.has_group('magenest_attendance.group_advanced_import'):
                rec.note_permission = True
            else:
                rec.note_permission = False

    def action_approve(self):
        return self.write({'state': 'confirm'})

    def action_refuse(self):
        return self.write({'state': 'refuse'})


class ManageSingleAttendance(models.TransientModel):
    _name = "single.handle"

    employee = fields.Many2many('hr.employee', string='Employee', required=True)

    def send_sheet_to_employee(self):
        super = self.env['manager.attendance'].sudo().browse(self._context.get('active_id'))
        if len(super) == 1 and super.state == 'sent':
            employees = []
            wrong_employee = []
            for e in self.employee:
                check = self.env['my.attendance'].sudo().search(
                    [('employee_id', '=', e.id), ('check_in_date', '=', super.check_in_date),
                     ('check_out_date', '=', super.check_out_date)])
                if len(check) == 0 and e.device_id:
                    employees.append(e)
                else:
                    wrong_employee.append(e.name)
            if len(employees) > 0:
                super.handle_single_attandance(employees)
            else:
                raise UserError(
                    _("All Employees Has Been Timekeeping. Can Not Create.Check Employee Info And Try Again !"))
        else:
            raise UserError(_("Can Not Do This Action For Current Record.Check Info And Try Again !"))
        if len(wrong_employee) > 0:
            message = "Successfully. Exception:%s Can't Not Create !" % str(wrong_employee)
        else:
            message = "Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }


class PayslipTransientModel(models.TransientModel):
    _name = "hr.payslip.transient"

    def _default_payslip(self):
        if self._context.get('active_ids'):
            active_ids = []
            for payslip in self.env['hr.payslip'].browse(self._context.get('active_ids')):
                if payslip.state not in ['done', 'cancel']:
                    active_ids.append(payslip.id)
            return self.env['hr.payslip'].browse(active_ids)

    payslip = fields.Many2many('hr.payslip', string="Payslip", required=True, default=_default_payslip)

    def compute_sheet_remote(self):
        for rec in self:
            if len(rec.payslip) > 0:
                for payslip in rec.payslip:
                    payslip.compute_sheet()
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {'default_name': "Compute Sheet Complete!"}
        }
