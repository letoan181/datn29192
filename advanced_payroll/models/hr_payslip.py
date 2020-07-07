from odoo import exceptions
from odoo import fields, models, api
from odoo.http import request


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    @api.model
    def _get_parent(self):
        return False


class SalaryInformationLine(models.Model):
    _name = 'salary.information.line'

    date_from = fields.Char('Date From')
    date_to = fields.Char('Date To')
    amount_receive = fields.Float('Amount Receive')
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Contract Id')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    salary_information_line_ids = fields.One2many('salary.information.line', 'employee_id',
                                                  'Salary Information', readonly=True)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    late_total = fields.Monetary(string='Late Total (Min)', digits=(16, 2), currency_field='currency_id')
    fine = fields.Monetary(string='Fine', digits=(16, 2), currency_field='currency_id')
    bonus = fields.Monetary(string='Bonus', digits=(16, 2), currency_field='currency_id')

    # company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True,
    #                                    relation="res.currency")

    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id)
    number_work_day_month = fields.Integer(string='Number of must working days in a month', required=True)
    number_day_off_allow_month = fields.Integer(string='Number day off in a month is allowed')
    amount_payroll_company_payable = fields.Float('# Amount Payroll Company payable', readonly=True,
                                                  compute='compute_amount_company_payable',
                                                  currency_field='currency_id')
    amount_employee_receivable = fields.Float('# Amount Employee Receivable', readonly=True,
                                              compute='compute_amount_employee_receivable',
                                              currency_field='currency_id')
    amount_social_insurance_company_payable = fields.Float('# Amount Social Insurance Company payable', readonly=True,
                                                           compute='compute_amount_insurance_company_payable',
                                                           currency_field='currency_id')
    over_time_normal_day = fields.Float('Over Time Normal Day (Hours)', digits=(16, 2))
    over_time_holiday = fields.Float('Over Time Holiday (Hours)', digits=(16, 2))
    timekeeping_count = fields.Integer()
    # timekeeping_id = fields.Many2one('my.attendance')
    # compute emp bank
    emp_bank_account = fields.Char(string='Bank Number Account', compute='_get_emp_bank_account')
    # Leave hours
    leave = fields.Float('Leave Unpaid Total(Hours)', digits=(16, 2))

    @api.constrains("number_work_day_month")
    def _validate_number_work_day_month(self):
        for rec in self:
            if rec.number_work_day_month <= 0:
                raise exceptions.ValidationError("Number of must working days in a month > 0")

    @api.depends('employee_id')
    def _get_emp_bank_account(self):
        for rec in self:
            if rec.employee_id:
                user = rec.employee_id.user_id
                if user:
                    res_partner = user.partner_id
                    bank_ids = res_partner.bank_ids
                    if bank_ids is not None and len(bank_ids) > 1:
                        for bank_id in bank_ids:
                            rec.emp_bank_account = bank_id.acc_number
                            break
                    else:
                        rec.emp_bank_account = bank_ids.acc_number
                else:
                    rec.emp_bank_account =False

    def compute_sheet(self):
        for payslip in self.filtered(lambda slip: slip.state not in ['cancel', 'done']):
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            # delete old payslip lines
            payslip.line_ids.unlink()
            lines = [(0, 0, line) for line in payslip._get_payslip_lines()]
            payslip.write({'line_ids': lines, 'number': number, 'state': 'verify', 'compute_date': fields.Date.today()})
        # create my timekeeping
        if len(self.line_ids) > 0:
            template = self.env.ref('magenest_attendance.employee_salary_details').render({
                'value': self
            }, engine='ir.qweb', minimal_qcontext=True)
            self.timekeeping_id.write({
                'salary_detail': template,
                'state': 'salary'
            })
        return True

    def compute_amount_employee_receivable(self):
        #     sum = 0
        #     for e in rec.line_ids:
        #         sum += e.total
        #     rec.amount_employee_receivable = sum
        #     return sum
        for rec in self:
            lines = rec.line_ids.filtered(lambda line: line.code == 'NET')
            rec.amount_employee_receivable = sum([line.total for line in lines])
            return sum([line.total for line in lines])


    def compute_amount_company_payable(self):
        for rec in self:
            lines = rec.line_ids.filtered(lambda line: line.code == 'NET')
            sums = sum([line.total for line in lines])
            if rec.contract_id.id:
                sums += rec.contract_id.social_insurance * 21.5 / 100
            rec.amount_payroll_company_payable = sums

    def compute_amount_insurance_company_payable(self):
        for rec in self:
            if rec.contract_id.id:
                rec.amount_social_insurance_company_payable = rec.contract_id.social_insurance * 21.5 / 100
            else:
                rec.amount_social_insurance_company_payable = False

    def action_payslip_done(self):
        # a = self.line_ids
        # print(a)
        request.env['salary.information.line'].create({
            'date_from': self.date_from,
            'date_to': self.date_to,
            'amount_receive': self.compute_amount_employee_receivable(),
            'employee_id': self.employee_id.id
        })
        self.compute_amount_employee_receivable()
        self.compute_amount_company_payable()
        self.compute_amount_insurance_company_payable()
        if self.timekeeping_id:
            self.timekeeping_id.write({
                'state': 'done',
                'color': 1
            })
        return super(HrPayslip, self).action_payslip_done()

    # @api.multi
    # def get_time_keeping(self):
    #     action = {
    #         "name": "Time Keeping",
    #         "type": "ir.actions.act_window",
    #         "view_mode": "form",
    #         "view_type": "form",
    #         "res_model": "my.attendance",
    #         "context": {"create": False, "delete": True},
    #         "domain": [],
    #         "res_id": self.timekeeping_id.id
    #     }
    #     return action
