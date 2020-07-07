# -*- coding: utf-8 -*-

import logging
from datetime import datetime

import passlib.context
import pytz
from odoo.addons.resource.models.resource import float_to_time
from pytz import timezone

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Datetime
from ..zk import ZK

_logger = logging.getLogger(__name__)
DEFAULT_CRYPT_CONTEXT = passlib.context.CryptContext(
    # kdf which can be verified by the context. The default encryption kdf is
    # the first of the list
    ['pbkdf2_sha512', 'plaintext'],
    # deprecated algorithms are still verified as usual, but ``needs_update``
    # will indicate that the stored hash should be replaced by a more recent
    # algorithm. Passlib 1.6 supports an `auto` value which deprecates any
    # algorithm but the default, but Ubuntu LTS only provides 1.5 so far.
    deprecated=['plaintext'],
)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    device_id = fields.Char(string='Biometric Device ID')
    date_check_in = fields.Char()
    late_today = fields.Float(string='Late Today', compute='_compute_late_today', store=True)

    @api.depends('check_in', 'check_out')
    def _compute_late_today(self):
        get_config_timekeeping = self.env['manager.attendance'].search([], limit=1)
        for attendance in self:
            if attendance.check_in and len(get_config_timekeeping) > 0:
                check_in = attendance.check_in.astimezone(timezone(get_config_timekeeping.time_zone))
                if datetime.combine(check_in.date(), check_in.time()) < datetime.combine(check_in.date(), float_to_time(
                        get_config_timekeeping.hour_am_to)):
                    late_today = (datetime.combine(check_in.date(), check_in.time()) - datetime.combine(check_in.date(),
                                                                                                        float_to_time(
                                                                                                            get_config_timekeeping.hour_am_from))).total_seconds() / 60.0
                else:
                    late_today = (datetime.combine(check_in.date(), check_in.time()) - datetime.combine(check_in.date(),
                                                                                                        float_to_time(
                                                                                                            get_config_timekeeping.hour_pm_from))).total_seconds() / 60.0
                attendance.late_today = round(late_today, 2)
            else:
                attendance.late_today = False

    def download_attendance_queue_from_time_sheet(self, date=None):
        zk = self.env['zk.machine'].search([], limit=1)
        if len(zk) > 0:
            time_zone = zk.time_zone
        else:
            time_zone = self.env.user.tz
        employees = self.env['hr.employee'].sudo().search([('attendance_by_time_sheet', '=', True)])
        if date is not None:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        if len(employees) > 0 and date:
            for employee in employees:
                time_sheets = self.env['account.analytic.line'].sudo().search([('employee_id', '=', employee.id), ('date', '>=', date)], order="date asc")
                for time_sheet in time_sheets:
                    time_sheet_date = time_sheet.date.strftime("%d/%m/%Y")
                    duplicate_attendance = self.env['hr.attendance'].sudo().search([('date_check_in', '=', time_sheet_date), ('employee_id', '=', employee.id)])
                    if duplicate_attendance:
                        continue
                    else:
                        date_start = self.env['account.analytic.line'].sudo().search([('employee_id', '=', employee.id), ('date', '=', time_sheet.date)], order="date_start asc")[0].date_start
                        date_end = self.env['account.analytic.line'].sudo().search([('employee_id', '=', employee.id), ('date', '=', time_sheet.date)], order="date_start desc")[0].date_end
                        if date_start.date() != date_end.date():
                            date_end = datetime(date_start.year, date_start.month, date_start.day, 10, 15, 00)
                        self.env['hr.attendance'].sudo().create({'employee_id': employee.id,
                                                                 'check_in': date_start,
                                                                 'check_out': date_end,
                                                                 'date_check_in': time_sheet_date})
            return True


class ZkUsers(models.Model):
    _name = 'zk.users'
    _order = "device_id_int ASC"

    name = fields.Char(string='Name')
    device_id = fields.Char('Device ID', readonly=True)
    device_id_int = fields.Integer(compute='_convert_device_id_to_int', store=True)
    attendance_type = fields.Selection([('1', 'Finger'),
                                        ('15', 'Face'),
                                        ('2', 'Type_2'),
                                        ('3', 'Password'),
                                        ('4', 'Card')], string='Category', readonly=True)
    uid = fields.Char(readonly=True)
    zk_id = fields.Many2one('zk.machine', string="Device")
    relate_emp = fields.Many2one('hr.employee', string='Relate Employee', ondelete='cascade')

    # has_employee = fields.Boolean(default=False)
    @api.depends('device_id')
    def _convert_device_id_to_int(self):
        for rec in self:
            rec.device_id_int = int(rec.device_id)

    def unlink(self):
        """Delete zkuser from Odoo"""
        for rec in self:
            if rec.zk_id.allow_delete_user:
                try:
                    conn = rec.zk_id.connect()
                except Exception as e:
                    raise UserError("Connect Fail!")
                if conn.is_connect and rec.uid:
                    conn.delete_user(uid=int(rec.uid), user_id=rec.device_id)
                    if rec.relate_emp:
                        rec.relate_emp.write({
                            'device_id': False,
                            'zk_id': False
                        })
        return super(ZkUsers, self).unlink()

    def action_delete_users(self):
        _logger.info("++++++++++++Executed++++++++++++++++++++++")
        self.unlink()

    def write(self, vals):
        if 'relate_emp' in vals:
            # check if related employee existed:
            if vals.get('relate_emp') and len(
                    self.env['zk.users'].search([('relate_emp', '=', vals.get('relate_emp'))]).ids) > 0:
                if self.relate_emp != False and self.env['zk.users'].search([('relate_emp', '=', vals.get('relate_emp'))]).relate_emp != self.relate_emp:
                    raise UserError(_('Employee %s Exist Link To Device ID %s' % (
                        self.env['zk.users'].search([('relate_emp', '=', vals.get('relate_emp'))]).relate_emp.name,
                        self.env['zk.users'].search([('relate_emp', '=', vals.get('relate_emp'))]).device_id)))
            if vals.get('relate_emp') == False:
                if self.relate_emp:
                    self.relate_emp.write({
                        'device_id': False,
                        'zk_id': False,
                    })
            else:
                if self.relate_emp:
                    self.relate_emp.write({
                        'device_id': False,
                        'zk_id': False
                    })
                emp = self.env['hr.employee'].sudo().browse(vals.get('relate_emp'))
                emp.write({
                    'device_id': self.device_id,
                    'zk_id': self.zk_id.id
                })
        return super(ZkUsers, self).write(vals)

    # @api.onchange('relate_emp')
    # def _onchange_relate_user(self):
    #     if self.relate_emp:
    #         duplicate = self.env['zk.users'].search([('relate_emp', '=', self.relate_emp.id)])
    #         if len(duplicate) > 0:
    #             raise UserError('Duplicate Relate Employee!')


class ZkMachine(models.Model):
    _name = 'zk.machine'

    name = fields.Char(string='Machine IP', required=True)
    port_no = fields.Integer(string='Port No', required=True, default=4370)
    # Ma hoa password  inverse='_set_password',invisible=True, copy=False
    pass_word = fields.Char(string='Password', required=True)
    address_id = fields.Many2one('res.partner', string='Working By')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    auto_clear_log = fields.Boolean(default=False,
                                    help='Check Here To Clear All ZK Attendance Record Every DownLoad Data',
                                    string='Clear All Log')
    auto_create_new_emp = fields.Boolean(default=False, help='Check Here To Create New Employee During Download',
                                         string='Create New Employee')
    auto_sync_user = fields.Boolean(default=False, help='Check Here To Sync User With Employee When Pull Users',
                                    string='Sync User-Employee')
    allow_delete_user = fields.Boolean(default=False, help='Check Here To Allow Delete ZK Users From Odoo',
                                       string=' Allow Delete User')
    user = fields.One2many('zk.users', 'zk_id', string='ZK Users', domain=lambda self: self._get_users_domain())
    time_zone = fields.Selection('_tz_get', string='Timezone', required=True,
                                 default=lambda self: self.env.user.tz or 'UTC')
    last_date_pull = fields.Char()
    state = fields.Selection([('ready', 'Ready'), ('in_process', 'In Process')], readonly=True, default='ready')

    def _get_users_domain(self):
        domain = []
        users = self.env['zk.users'].search([('relate_emp', '=', False)])
        for user in users:
            domain.append(user.id)
        return [('id', 'in', domain)]

    @api.onchange('auto_clear_log')
    def _onchange_clear_log(self):
        if self.auto_clear_log:
            warning_mess = {
                'title': _('Confirmation!'),
                'message': 'Are you sure to clear all log data in device ?'
            }
            return {'warning': warning_mess}

    @api.onchange('allow_delete_user')
    def _onchange_delete_user(self):
        if self.allow_delete_user:
            warning_mess = {
                'title': _('Confirmation!'),
                'message': 'Are you sure to allow to delete ZK user from Odoo ?'
            }
            return {'warning': warning_mess}

    @api.model
    def _tz_get(self):
        return [(x, x) for x in pytz.all_timezones]

    def _set_password(self):
        ctx = self._crypt_context()
        for zk in self:
            self._set_encrypted_password(zk.id, ctx.encrypt(zk.pass_word))

    def _set_encrypted_password(self, uid, pw):
        assert self._crypt_context().identify(pw) != 'plaintext'

        self.env.cr.execute(
            'UPDATE zk_machine SET pass_word=%s WHERE id=%s',
            (pw, uid)
        )
        self.invalidate_cache(['pass_word'], [uid])

    def connect(self):
        conn = None
        for info in self:
            machine_ip = info.name
            port = info.port_no
            pass_word = info.pass_word
            # zk = zklib.ZKLib(machine_ip, port)
            zk = ZK(machine_ip, port=port, password=pass_word, verbose=True)
            try:
                conn = zk.connect()
                # print(conn.get_serialnumber())
                # print(conn.get_device_name())
            except Exception as e:
                raise ValueError("Process terminate : {}".format(e))
        return conn

    def reset_status(self):
        return self.write({'state': 'ready'})

    def test_connection(self):
        try:
            conn = self.connect()
        except Exception as e:
            raise UserError(_('Unable to connect, please check the parameters and network connections.' + str(e)))
        if not conn.is_connect:
            raise UserError(_('Unable to connect, please check the parameters and network connections.'))
        else:
            return {
                'name': 'Message',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'custom.pop.message',
                'target': 'new',
                'context': {'default_name': "Successfully Connection."}
            }

    def _crypt_context(self):
        """ Passlib CryptContext instance used to encrypt and verify
        passwords. Can be overridden if technical, legal or political matters
        require different kdfs than the provided default.

        Requires a CryptContext as deprecation and upgrade notices are used
        internally
        """
        return DEFAULT_CRYPT_CONTEXT

    def download_users(self):
        try:
            conn = self.connect()
        except Exception as e:
            raise UserError(str(e))
        if not conn.is_connect:
            raise UserError(_('Unable to connect, please check the parameters and network connections.'))
        else:
            users = conn.get_users()
            User = self.env['zk.users'].sudo()
            for user in users:
                duplicate_user = User.search(
                    [('device_id', '=', user.user_id)])
                if duplicate_user:
                    continue
                else:
                    User.create({
                        'name': user.name,
                        'device_id': user.user_id,
                        'uid': user.uid,
                        'zk_id': self.id,
                        'attendance_type': '1'
                    })
            if self.auto_sync_user:
                employee_can_sync = self.env['hr.employee'].sudo().search([('zk_id', '=', self.id), ('device_id', '!=', False)])
                for emp in employee_can_sync:
                    need_to_sync = User.search([('device_id', '=', emp.device_id)])
                    if len(need_to_sync) == 1:
                        try:
                            need_to_sync.write({
                                'relate_emp': emp.id, })
                        except Exception as e:
                            "print(""str(e))"
                            # 'has_employee': True
                            # Update by SQL
                            # self.env.cr.execute(
                            #     """update zk_users set relate_emp = %s WHERE device_id=%s""", (emp.id,emp.device_id,))
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {'default_name': "Download User Complete!"}
        }

    def download_attendance(self):
        _logger.info("++++++++++++Cron Executed++++++++++++++++++++++")
        zk_attendance = self.env['zk.machine.attendance']
        att_obj = self.env['hr.attendance']
        if self.state != 'in_process':
            # mark in process for this record
            self.env.cr.execute(
                """update zk_machine set state = 'in_process' WHERE id=%s""", (self.id,))
            self.env.cr.commit()
            for info in self:
                try:
                    conn = info.connect()
                except Exception as e:
                    raise UserError(str(e))
                attendances = None
                try:
                    if conn:
                        attendances = conn.get_attendance()
                        if attendances:
                            for each in attendances:
                                atten_time = each.timestamp
                                local_tz = pytz.timezone(
                                    self.env.user.partner_id.tz or 'GMT')
                                local_dt = local_tz.localize(atten_time, is_dst=None)
                                utc_dt = local_dt.astimezone(pytz.utc)
                                utc_dt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                                atten_time = each.timestamp.strptime(
                                    utc_dt, "%Y-%m-%d %H:%M:%S")
                                atten_time = fields.Datetime.to_string(atten_time)
                                get_user_id = self.env['hr.employee'].search(
                                    [('device_id', '=', str(each.user_id)), ('zk_id', '=', self.id)])
                                # if each.user_id == 3:
                                #     print('vi')
                                #     print(atten_time)
                                if each.punch not in [0, 1, 2, 3, 4, 5]:
                                    each.punch = 255
                                if get_user_id:
                                    duplicate_atten_ids = zk_attendance.search(
                                        [('device_id', '=', str(each.user_id)),
                                         ('punching_time', '=', atten_time),
                                         ('zk_id', '=', self.id)])
                                    if duplicate_atten_ids:
                                        continue
                                    else:
                                        try:
                                            zk_attendance.create({'employee_id': get_user_id.id,
                                                                  'device_id': each.user_id,
                                                                  'attendance_type': "1",
                                                                  'punch_type': str(each.punch),
                                                                  'punching_time': atten_time,
                                                                  'address_id': info.address_id.id,
                                                                  'zk_id': self.id})
                                            date = each.timestamp.strftime("%d/%m/%Y")
                                            att_var = att_obj.search(
                                                [('employee_id', '=', get_user_id.id), ('date_check_in', '=', date)])
                                            if not att_var:
                                                try:
                                                    att_obj.create({'employee_id': get_user_id.id,
                                                                    'check_in': atten_time,
                                                                    'date_check_in': date})
                                                except Exception as e:
                                                    'print(" Error " + str(e))'
                                            else:
                                                att_var.write({'check_out': atten_time})
                                            # if each.punch not in [0, 1]:
                                            #     "print('Wrong Code' + str(each.punch))"
                                        except Exception as e:
                                            print("Error" + str(e))
                                        else:
                                            pass
                                # create new employee
                                else:
                                    if self.auto_create_new_emp:
                                        users = None
                                        try:
                                            users = conn.get_users()
                                        except Exception as e:
                                            "print('Error:' + str(e))"
                                        new_emp = None
                                        if users:
                                            for user in users:
                                                if user.user_id == str(each.user_id):
                                                    new_emp = user
                                                    break
                                        employee = self.env['hr.employee'].create(
                                            {'device_id': str(each.user_id),
                                             'name': new_emp.name,
                                             'zk_id': self.id})
                                        zk_attendance.create({'employee_id': employee.id,
                                                              'device_id': each.user_id,
                                                              'attendance_type': '1',
                                                              'punch_type': str(each.punch),
                                                              'punching_time': atten_time,
                                                              'zk_id': self.id
                                                              })
                                        try:
                                            att_obj.create({'employee_id': employee.id,
                                                            'check_in': atten_time})
                                        except Exception as e:
                                            'print(" Error " + str(e))'
                            # Write Date Pull
                            date_now = Datetime.now().astimezone(timezone(self.time_zone)).strftime("%d/%m/%Y")
                            try:
                                self.env.cr.execute(
                                    """update zk_machine set state = 'ready' WHERE id=%s""",
                                    (self.id,))
                                self.env.cr.execute(
                                    """update zk_machine set last_date_pull = %s WHERE id=%s""",
                                    (date_now, self.id,))
                                self.env.cr.commit()
                            except Exception as e:
                                """print(e)"""
                                self.env.cr.execute(
                                    """update zk_machine set state = 'ready' WHERE id=%s""",
                                    (self.id,))
                                self.env.cr.commit()
                            return {
                                'name': 'Message',
                                'type': 'ir.actions.act_window',
                                'view_mode': 'form',
                                'res_model': 'custom.pop.message',
                                'target': 'new',
                                'context': {'default_name': "Download Data Complete!"}
                            }
                        else:
                            raise UserError(_('Unable to get the attendance log, please try again later.'))
                    else:
                        raise UserError(_('Unable to connect, please check the parameters and network connections.'))
                except Exception as e:
                    raise ValueError("Process terminate : {}".format(e))
                finally:
                    if attendances:
                        if info.auto_clear_log:
                            if conn:
                                conn.clear_attendance()
                    if conn:
                        conn.disconnect()

    def _download_attendance_queue(self, zk_id=None):
        zk = self.env['zk.machine'].search([], limit=1)
        if len(zk) > 0:
            time_zone = zk.time_zone
            date_now = Datetime.now().astimezone(timezone(time_zone)).strftime("%d/%m/%Y")
            zk_need_pull = self.env['zk.machine'].search([('last_date_pull', '!=', date_now), ('id', '=', zk_id)])
            zk_attendance = self.env['zk.machine.attendance']
            att_obj = self.env['hr.attendance']
            if len(zk_need_pull) > 0:
                for info in zk_need_pull:
                    if info.state != 'in_process':
                        self.env.cr.execute(
                            """update zk_machine set state = 'in_process' WHERE id=%s""",
                            (info.id,))
                        self.env.cr.commit()
                        conn = None
                        try:
                            conn = info.connect()
                        except Exception as e:

                            self.env.cr.execute(
                                """update zk_machine set state = 'ready' WHERE id=%s""",
                                (info.id,))
                            self.env.cr.commit()
                        try:
                            attendances = None
                            if conn:
                                attendances = conn.get_attendance()
                                if attendances:
                                    for each in attendances:
                                        atten_time = each.timestamp
                                        local_tz = pytz.timezone(time_zone)
                                        local_dt = local_tz.localize(atten_time, is_dst=None)
                                        utc_dt = local_dt.astimezone(pytz.utc)
                                        utc_dt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                                        atten_time = each.timestamp.strptime(
                                            utc_dt, "%Y-%m-%d %H:%M:%S")
                                        atten_time = fields.Datetime.to_string(atten_time)
                                        get_user_id = info.env['hr.employee'].search(
                                            [('device_id', '=', str(each.user_id)), ('zk_id', '=', info.id)])
                                        if each.punch not in [0, 1, 2, 3, 4, 5]:
                                            each.punch = 255
                                        if get_user_id:
                                            duplicate_atten_ids = zk_attendance.search(
                                                [('device_id', '=', str(each.user_id)),
                                                 ('punching_time', '=', atten_time),
                                                 ('zk_id', '=', info.id)])
                                            if duplicate_atten_ids:
                                                continue
                                            else:
                                                try:
                                                    zk_attendance.create({'employee_id': get_user_id.id,
                                                                          'device_id': each.user_id,
                                                                          'attendance_type': "1",
                                                                          'punch_type': str(each.punch),
                                                                          'punching_time': atten_time,
                                                                          'address_id': info.address_id.id,
                                                                          'zk_id': info.id})
                                                    date = each.timestamp.strftime("%d/%m/%Y")
                                                    att_var = att_obj.search(
                                                        [('employee_id', '=', get_user_id.id),
                                                         ('date_check_in', '=', date)])
                                                    if not att_var:
                                                        try:
                                                            att_obj.create({'employee_id': get_user_id.id,
                                                                            'check_in': atten_time,
                                                                            'date_check_in': date})
                                                        except Exception as e:
                                                            'print(" Error " + str(e))'
                                                    else:
                                                        att_var.write({'check_out': atten_time})
                                                    # if each.punch not in [0, 1]:
                                                    #     "print('Wrong Code' + str(each.punch))"
                                                except Exception as e:
                                                    print("Error" + str(e))
                                                else:
                                                    pass
                                        # create new employee
                                        else:
                                            if info.auto_create_new_emp:
                                                users = None
                                                try:
                                                    users = conn.get_users()
                                                except Exception as e:
                                                    "print('Error:' + str(e))"
                                                new_emp = None
                                                if users:
                                                    for user in users:
                                                        if user.user_id == str(each.user_id):
                                                            new_emp = user
                                                            break
                                                employee = info.env['hr.employee'].create(
                                                    {'device_id': str(each.user_id),
                                                     'name': new_emp.name,
                                                     'zk_id': info.id})
                                                zk_attendance.create({'employee_id': employee.id,
                                                                      'device_id': each.user_id,
                                                                      'attendance_type': "1",
                                                                      'punch_type': str(each.punch),
                                                                      'punching_time': atten_time,
                                                                      'zk_id': info.id,
                                                                      })
                                                try:
                                                    att_obj.create({'employee_id': employee.id,
                                                                    'check_in': atten_time})
                                                except Exception as e:
                                                    'print(" Error " + str(e))'
                                    # Write Date Pull
                                    date_now = Datetime.now().astimezone(timezone(info.time_zone)).strftime("%d/%m/%Y")
                                    try:
                                        # info.write({'last_date_pull': date_now})
                                        self.env.cr.execute(
                                            """update zk_machine set state = 'ready',last_date_pull = %s  WHERE id=%s""",
                                            (date_now, info.id,))
                                        self.env.cr.commit()
                                    except Exception as e:
                                        self.env.cr.execute(
                                            """update zk_machine set state = 'ready' WHERE id=%s""",
                                            (info.id,))
                                        self.env.cr.commit()
                                else:
                                    self.env.cr.execute(
                                        """update zk_machine set state = 'ready' WHERE id=%s""",
                                        (info.id,))
                                    self.env.cr.commit()
                        except Exception as e:
                            "print(e)"
                        finally:
                            self.env.cr.execute(
                                """update zk_machine set state = 'ready' WHERE id=%s""",
                                (info.id,))
                            self.env.cr.commit()


class CustomPopMessage(models.TransientModel):
    _name = "custom.pop.message"

    name = fields.Char('Message')
