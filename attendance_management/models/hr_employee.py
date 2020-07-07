from odoo import fields, models, api


class ModelName(models.Model):
    _inherit = 'hr.employee'

    can_add_overtime_users = fields.Many2many(
        'res.users', 'hr_employee_can_add_overtime_user_rel', string="Employees That You Can Add Overtime")
