import logging

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    document_general_folder_base = fields.Char("General Folder Base",
                                               config_parameter='document_management.general_folder_base')
    document_project_folder_base = fields.Char("Project Folder Base",
                                               config_parameter='document_management.project_folder_base')
    document_quotation_folder_base = fields.Char("Quotation Folder Base",
                                                 config_parameter='document_management.quotation_folder_base')
    document_crm_folder_base = fields.Char("CRM Folder Base",
                                           config_parameter='document_management.crm_folder_base')

    # start template

    document_doc_file_base_template = fields.Char("Google Document File Template",
                                                  config_parameter='document_management.doc_file_template')
    document_sheet_file_base_template = fields.Char("Google Sheet Document File Template",
                                                    config_parameter='document_management.sheet_file_template')
    document_power_point_file_base_template = fields.Char("Document Power Point File Template",
                                                          config_parameter='document_management.power_point_file_template')

    # start_page_token
    track_start_page_token = fields.Char("Tracking Start Page Token",
                                         config_parameter='document_management.track_start_page_token')


_logger = logging.getLogger(__name__)


class DocumentAbstractModel(models.AbstractModel):
    _name = 'document.abstract'

    def search_read(self, args=None, **kwargs):
        """ This Model Use Like Virtual Model To Call Search_read With Sudo()"""
        result = False
        if kwargs['res_model'] and kwargs['res_id']:
            model = kwargs['res_model']
            res_id = kwargs['res_id']
            records = self.env[model].sudo().search([('id', '=', res_id)], limit=1)
            if len(records) > 0:
                result = True
        # print(result)
        return result
