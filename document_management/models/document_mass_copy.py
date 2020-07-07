from odoo import fields, models, api


class MassCopy(models.TransientModel):
    _name = 'document.project.file.mass.copy'
    _description = 'Mass copy document'

    document_type = fields.Selection(
        string='Document type',
        selection=[('project', 'Project'),
                   ('crm', 'CRM'),
                   ('quotation', 'Quotation'), ],
        required=True,
        default='project')

    document_project_id = fields.Many2one('project.project', string='Project Folder', )
    document_project_part = fields.Many2one('document.project.part', string='Folder', )

    document_crm_id = fields.Many2one('crm.lead', string='CRM Folder')
    document_crm_part = fields.Many2one('document.crm.part', string='Folder Part', )

    document_quotation_id = fields.Many2one('sale.order', string='Quotation Folder', )
    document_quotation_part = fields.Many2one('document.quotation.part', string='Folder Part')

    def mass_copy(self):
        list = self.env[self._context['active_model']].browse(self._context['active_ids'])
        create = None
        if self.document_type == 'project':
            part = self.document_project_part.id
            parent_file_id = self.document_project_part.file_id
            create = self.env['document.project.file'].sudo()
        elif self.document_type == 'crm':
            part = self.document_crm_part.id
            parent_file_id = self.document_crm_part.file_id
            create = self.env['document.crm.file'].sudo()
        elif self.document_type == 'quotation':
            part = self.document_quotation_part.id
            parent_file_id = self.document_quotation_part.file_id
            create = self.env['document.quotation.file'].sudo()
        else:
            parent_file_id = None
            part = None
        external_users = []
        if parent_file_id and part and create is not None:
            for rec in list:
                # write_users= rec.write_users,
                # read_users= rec.read_users,
                write_list = []
                read_list = []
                for e in rec.write_users:
                    write_list.append(e.id)
                for a in rec.read_users:
                    read_list.append(a.id)
                for a in rec.external_users:
                    external_users.append([0, 0, {'name': a.name, 'user_email': a.user_email, 'type': a.type}])
                    # 'file_id': google_drive_new_file['id'],
                    # 'res_user_id': e,
                    # 'type': 'write',

                vals = {
                    'name': rec.name,
                    'type': rec.type,
                    'res_id': part,
                    'google_drive_url': rec.google_drive_url,
                    'file_id': rec.file_id,
                    'color': rec.color,
                    'public': rec.public,
                    'public_type': rec.public_type,
                    'write_users': [(6, 0, write_list)],
                    'read_users': [(6, 0, read_list)],
                    'users_update': rec.users_update,
                    'external_users': external_users,
                    'is_copy': True,
                    'parent_file_id': parent_file_id,
                }
                create.create(vals)
                vals.clear()
