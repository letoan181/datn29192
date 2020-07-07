from odoo import api, fields, models


class AttendanceDayOff(models.Model):
    _inherit = "attendance.day.off"

    paid_holidays = fields.Boolean(string="Paid holidays", help="Nếu chọn, ngày nghỉ sẽ được tính lương", default=False)
