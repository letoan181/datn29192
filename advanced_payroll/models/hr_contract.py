from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    type = fields.Selection([('partime', 'Partime'), ('fulltime', 'Fulltime')], required=True)
    lunch_allowance = fields.Monetary('Lunch Allowance', digits=(16, 2), help="Phụ cấp ăn trưa")
    travel_allowance = fields.Monetary('Travel Allowance', digits=(16, 2), help="Phụ cấp đi lại")
    telephone_allowance = fields.Monetary('Telephone Allowance', digits=(16, 2), help="Phụ cấp điện thoại")
    responsibility_allowance = fields.Monetary('Responsibility Allowance', digits=(16, 2), help="Phụ cấp trách nhiệm")
    seniority_allowance = fields.Monetary('Seniority Allowance', digits=(16, 2), help="Phụ cấp thâm niên")
    house_rent_allowance = fields.Monetary('House Rent Allowance', digits=(16, 2), help="Phụ cấp nhà ở")
    family_circumtance_deductions = fields.Monetary('Family Circumtance Deductions', digits=(16, 2),
                                                    help="Giảm trừ gia cảnh")
    social_insurance = fields.Monetary('Social Insurance', digits=(16, 2),
                                       help="Mức đóng bảo hiểm xã hội")
