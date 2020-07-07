from odoo import models, fields


class ProjectTags(models.Model):
    """ Tags of document's tasks """
    _name = "document.tags"
    _description = "Document File Tags"

    name = fields.Char(required=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]


class GeneralDocumentFileTags(models.Model):
    _inherit = "document.general.file"

    tag_ids = fields.Many2many('document.tags', string='Tags')


class ProjectDocumentFileTag(models.Model):
    _inherit = "document.project.file"

    tag_ids = fields.Many2many('document.tags', string='Tags')


class QuotationDocumentFileTags(models.Model):
    _inherit = "document.quotation.file"

    tag_ids = fields.Many2many('document.tags', string='Tags')


class CrmDocumentFileTags(models.Model):
    _inherit = "document.crm.file"

    tag_ids = fields.Many2many('document.tags', string='Tags')
