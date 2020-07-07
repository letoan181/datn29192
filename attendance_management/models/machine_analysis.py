# -*- coding: utf-8 -*-
###################################################################################
#
#    Magenest Technologies.
#    Copyright (C) 2018-TODAY magenest(<https://store.magenest.com/>).
#    Author: Magenest developers(<https://store.magenest.com/>)
#
from odoo import models, fields, api
from odoo import tools
from datetime import datetime, timedelta, date


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    device_id = fields.Char(string='Biometric Device ID')
    zk_id = fields.Many2one('zk.machine', string='Biometric Device IP')
    attendance_by_time_sheet = fields.Boolean(string="TimeSheet Attendance", default=False)


class ZkMachine(models.Model):
    _name = 'zk.machine.attendance'
    _inherit = 'hr.attendance'

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """overriding the __check_validity function for employee attendance."""
        pass

    device_id = fields.Char(string='Biometric Device ID')
    punch_type = fields.Selection([('0', 'Check In'),
                                   ('1', 'Check Out'),
                                   ('2', 'Break Out'),
                                   ('3', 'Break In'),
                                   ('4', 'Overtime In'),
                                   ('5', 'Overtime Out'),
                                   ('6', 'Time Sheet'),
                                   ('255', 'Not Define')],
                                  string='Punching Type')

    attendance_type = fields.Selection([('1', 'Finger'),
                                        ('15', 'Face'),
                                        ('2', 'Type_2'),
                                        ('3', 'Password'),
                                        ('4', 'Card'), ('5', 'Time Sheet')], string='Category')
    punching_time = fields.Datetime(string='Punching Time')
    address_id = fields.Many2one('res.partner', string='Working Address')
    zk_id = fields.Many2one('zk.machine',string='Biometric Machine IP')

class ReportZkDevice(models.Model):
    _name = 'zk.report.daily.attendance'
    _auto = False
    _order = 'punching_day desc'

    name = fields.Many2one('hr.employee', string='Employee')
    punching_day = fields.Datetime(string='Date')
    address_id = fields.Many2one('res.partner', string='Working Address')
    attendance_type = fields.Selection([('1', 'Finger'),
                                        ('15', 'Face'),
                                        ('2', 'Type_2'),
                                        ('3', 'Password'),
                                        ('4', 'Card')],
                                       string='Category')
    punch_type = fields.Selection([('0', 'Check In'),
                                   ('1', 'Check Out'),
                                   ('2', 'Break Out'),
                                   ('3', 'Break In'),
                                   ('4', 'Overtime In'),
                                   ('5', 'Overtime Out')], string='Punching Type')
    punching_time = fields.Datetime(string='Punching Time')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'zk_report_daily_attendance')
        query = """
            create or replace view zk_report_daily_attendance as (
                select
                    min(z.id) as id,
                    z.employee_id as name,
                    z.write_date as punching_day,
                    z.address_id as address_id,
                    z.attendance_type as attendance_type,
                    z.punching_time as punching_time,
                    z.punch_type as punch_type
                from zk_machine_attendance z
                    join hr_employee e on (z.employee_id=e.id)
                GROUP BY
                    z.employee_id,
                    z.write_date,
                    z.address_id,
                    z.attendance_type,
                    z.punch_type,
                    z.punching_time
            )
        """
        self._cr.execute(query)


class ReportHrAttendanceLateToday(models.Model):
    _name = 'hr.attendance.daily.late'
    _auto = False
    _order = 'late_time desc'

    name = fields.Many2one('hr.employee', string='Employee')
    late_time = fields.Float(string='Late Today')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_attendance_daily_late')
        self._cr.execute("""create or replace view hr_attendance_daily_late as (
                select
                    min(z.id) as id,
                    z.employee_id as name,
                    z.late_today as late_time
                from hr_attendance z
                where z.date_check_in = '%s'
                GROUP BY
                    z.employee_id,
                    z.late_today
            )
        """ % (datetime.today().strftime("%d/%m/%Y")))

class MassUpdateZk(models.TransientModel):
    _name = 'mass.update.zk'
    _description = 'Update Employee Biometric Device'

    location = fields.Many2one(
        comodel_name='company.location',
        string='Location',
        required=True)
    zk_id = fields.Many2one(
        comodel_name='zk.machine',
        string='Biometric Device',
        required=True)

    def mass_update_zk(self):
        if self.location and self.zk_id:
            self.env['hr.employee'].sudo().search([('employee_location', '=', self.location.id)])\
                .write({'zk_id': self.zk_id})
        return True

