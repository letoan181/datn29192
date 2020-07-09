
from odoo import fields, models, api
from odoo import tools

class ReportAttendanceAnaylys(models.Model):
    _name = 'hr.attendance.report'
    _auto = False
    _order = 'id desc'

    name = fields.Many2one('hr.employee', string='Employee')
    check_in = fields.Datetime()
    work_hours = fields.Float()
    late_time = fields.Float(string='Late')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_attendance_report')
        self._cr.execute("""create or replace view hr_attendance_report as (
                select
                    min(z.id) as id,
                    z.employee_id as name,
                    z.check_in as check_in,
                    z.worked_hours as work_hours,
                    z.late_today as late_time
                from hr_attendance z
                GROUP BY
                    z.employee_id,
                    z.worked_hours,
                    z.check_in,
                    z.late_today          
            )
        """)