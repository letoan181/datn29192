# -*- coding: utf-8 -*-
{
    'name': "advanced_payroll",
    'summary': """
       The best addon in universal""",
    'description': """
        Long description of module's purpose
    """,
    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'depends': ['base', 'account', 'account_payment', 'maintenance', 'hr_payroll', 'hr_contract', 'hr_expense', 'sale'],
    'data': [
        'data/hr_payroll_data.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_view_inherit.xml',
        'views/hr_contract_inherit_view.xml',
        'views/hr_payslip_inherit_view.xml',
        # 'views/hr_payslip_report.xml'
    ],
}
