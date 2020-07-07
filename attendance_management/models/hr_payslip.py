from odoo import models, fields, api


class HrPayslipInherit(models.Model):
    _inherit = 'hr.payslip'

    timekeeping_id = fields.Many2one('my.attendance')

    def get_time_keeping(self):
        action = {
            "name": "Time Keeping",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "my.attendance",
            "context": {"create": False, "delete": True},
            "domain": [],
            "res_id": self.timekeeping_id.id
        }
        return action
