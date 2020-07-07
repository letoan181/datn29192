from odoo import _

from odoo import models, fields, api
from odoo.exceptions import UserError
from ..utils.google_drive_helper import GoogleDriveHelper
from ..utils.google_drive_revision_helper import GoogleDriveRevisionHelper


class DocumentPermission(models.Model):
    _name = "document.permission"
    _description = "Store all pare user file permission"

    model = fields.Selection(
        [('general', 'General'), ('project', 'Project'), ('quotation', 'Quotation'), ('crm', 'CRM')],
        required=True, default='general')
    type = fields.Selection([('read', 'Read'), ('write', 'Write')], required=True, default='read')

    res_id = fields.Integer(required=True)
    res_user_id = fields.Integer()
    google_drive_permission_id = fields.Char()
    file_id = fields.Char('File Id', compute='_compute_file_id')

    def _compute_file_id(self):
        all_file_id_dict = dict()
        # search general document
        self.env.cr.execute(
            """select document_permission.id,document_general_part.file_id from document_permission left join document_general_part on document_general_part.id=document_permission.res_id where document_permission.model like 'general'""")
        all_file_id = self.env.cr.fetchall()
        if all_file_id is not None and len(all_file_id) > 0:
            for e in all_file_id:
                all_file_id_dict[e[0]] = e[1]

        # search project document
        self.env.cr.execute(
            """select document_permission.id,document_project_part.file_id from document_permission left join document_project_part on document_project_part.id=document_permission.res_id where document_permission.model like 'project'""")
        all_file_id = self.env.cr.fetchall()
        if all_file_id is not None and len(all_file_id) > 0:
            for e in all_file_id:
                all_file_id_dict[e[0]] = e[1]

        # search quotation document
        self.env.cr.execute(
            """select document_permission.id,document_quotation_part.file_id from document_permission left join document_quotation_part on document_quotation_part.id=document_permission.res_id where document_permission.model like 'quotation'""")
        all_file_id = self.env.cr.fetchall()
        if all_file_id is not None and len(all_file_id) > 0:
            for e in all_file_id:
                all_file_id_dict[e[0]] = e[1]

        # search crm document
        self.env.cr.execute(
            """select document_permission.id,document_crm_part.file_id from document_permission left join document_crm_part on document_crm_part.id=document_permission.res_id where document_permission.model like 'crm'""")
        all_file_id = self.env.cr.fetchall()
        if all_file_id is not None and len(all_file_id) > 0:
            for e in all_file_id:
                all_file_id_dict[e[0]] = e[1]
        for permission in self:
            permission.file_id = all_file_id_dict.get(permission.id, 'False')

    # @api.model
    # def create(self, values):
    #     if self.model == 'general':
    #         self.env.cr.execute("""select file_id, google_email, type
    #         from document_permission
    #                left join document_general_part
    #                  on document_general_part.id = document_permission.res_id
    #                left join res_users on res_users.id = document_permission.res_user_id
    #         where document_permission.id = %s and document_permission.google_drive_permission_id is null""",
    #                             (str(self.id),))
    #         need_sync_data = self.env.cr.fetchone()
    #         if need_sync_data is not None:
    #             google_drive_helper = GoogleDriveHelper()
    #             if need_sync_data[2] == 'write':
    #                 new_permission = google_drive_helper.create_file_write_permission(need_sync_data[0],
    #                                                                                   need_sync_data[1])
    #                 values['google_drive_permission_id'] = new_permission
    #             if need_sync_data[2] == 'read':
    #                 new_permission = google_drive_helper.create_file_read_permission(need_sync_data[0],
    #                                                                                  need_sync_data[1])
    #                 values['google_drive_permission_id'] = new_permission
    #         else:
    #             raise UserError(_("We dont need to update this file permission"))
    #     return super(DocumentPermission, self).create(values)

    def unlink(self):
        if len(self.ids) > 0:
            self.env.cr.execute(
                """select model,res_id,google_drive_permission_id from document_permission where id in %s""",
                (tuple(self.ids),))
            all_permission = self.env.cr.fetchall()
            if all_permission is not None and len(all_permission) > 0:
                google_drive_helper = GoogleDriveHelper()
                for e in all_permission:
                    if e[0] == 'general' and e[2] is not None:
                        try:
                            google_drive_helper.drop_file_permission(
                                file_id=self.env['document.general.part'].sudo().search(
                                    [('id', '=', e[1])])[0]['file_id'], permission_id=e[2])
                        except Exception as ex:
                            a = 0
                    elif e[0] == 'quotation' and e[2] is not None:
                        try:
                            google_drive_helper.drop_file_permission(
                                file_id=self.env['document.quotation.part'].sudo().search(
                                    [('id', '=', e[1])])[0]['file_id'], permission_id=e[2])
                        except Exception as ex:
                            a = 0
                    elif e[0] == 'crm' and e[2] is not None:
                        try:
                            google_drive_helper.drop_file_permission(
                                file_id=self.env['document.crm.part'].sudo().search(
                                    [('id', '=', e[1])])[0]['file_id'], permission_id=e[2])
                        except Exception as ex:
                            a = 0
                    elif e[0] == 'project' and e[2] is not None:
                        try:
                            google_drive_helper.drop_file_permission(
                                file_id=self.env['document.project.part'].sudo().search(
                                    [('id', '=', e[1])])[0]['file_id'], permission_id=e[2])
                        except Exception as ex:
                            a = 0
            return super(DocumentPermission, self).unlink()

    def action_fetch_document_permission(self):
        if self.model == 'general':
            self.env.cr.execute("""select file_id, google_email, type
            from document_permission
                   left join document_general_part
                     on document_general_part.id = document_permission.res_id
                   left join res_users on res_users.id = document_permission.res_user_id
            where document_permission.id = %s and document_permission.google_drive_permission_id is null""",
                                (str(self.id),))
            need_sync_data = self.env.cr.fetchone()
            if need_sync_data is not None:
                google_drive_helper = GoogleDriveHelper()
                if need_sync_data[2] == 'write':
                    new_permission = google_drive_helper.create_file_write_permission(need_sync_data[0],
                                                                                      need_sync_data[1])
                    return self.write({'google_drive_permission_id': new_permission})

                if need_sync_data[2] == 'read':
                    new_permission = google_drive_helper.create_file_read_permission(need_sync_data[0],
                                                                                     need_sync_data[1])
                    return self.write({'google_drive_permission_id': new_permission})
            else:
                raise UserError(_("We dont need to update this file permission"))

    def action_drop_document_permission(self):
        if self.model == 'general':
            self.env.cr.execute("""select file_id, google_drive_permission_id
                from document_permission
                left join document_general_part
                     on document_general_part.id = document_permission.res_id
                where document_permission.id = %s and document_permission.google_drive_permission_id is not null""",
                                (str(self.id),))
            need_sync_data = self.env.cr.fetchone()
            if need_sync_data is not None:
                google_drive_helper = GoogleDriveHelper()
                google_drive_helper.drop_file_permission(need_sync_data[0],
                                                         need_sync_data[1])
                return self.write({'google_drive_permission_id': None})
            else:
                raise UserError(_("No permission attach to this document"))

    # General read,write permission
    def _process_sync_user_permission_queue(self, row_count):
        try:
            self.env.cr.execute("""select document_permission.id as id, file_id, google_email
from document_permission
       left join document_general_part
         on document_general_part.id = document_permission.res_id
       left join res_users on res_users.id = document_permission.res_user_id
where document_permission.google_drive_permission_id is null and model like 'general' and type like 'write'""")
            need_sync_data = self.env.cr.fetchmany(row_count)
            if need_sync_data:
                google_drive_helper = GoogleDriveHelper()
                for e in need_sync_data:
                    try:
                        new_permission = google_drive_helper.create_file_write_permission(e[1], e[2])
                        self.env['document.permission'].sudo().search([('id', '=', e[0])]).write(
                            {'google_drive_permission_id': new_permission})
                    except Exception as ex:
                        # raise UserError(_("Something went wrong, please try again later"))
                        e = 0

            self.env.cr.execute("""select document_permission.id as id, file_id, google_email
            from document_permission
                   left join document_general_part
                     on document_general_part.id = document_permission.res_id
                   left join res_users on res_users.id = document_permission.res_user_id
            where document_permission.google_drive_permission_id is null and model like 'general' and type like 'read'""")
            need_sync_data = self.env.cr.fetchmany(row_count)
            if need_sync_data:
                google_drive_helper = GoogleDriveHelper()
                for e in need_sync_data:
                    try:
                        new_permission = google_drive_helper.create_file_read_permission(e[1], e[2])
                        self.env['document.permission'].sudo().search([('id', '=', e[0])]).write(
                            {'google_drive_permission_id': new_permission})
                    except Exception as ex:
                        # raise UserError(_("Something went wrong, please try again later"))
                        e = 0
        except Exception as ex:
            e = 0

    # Quotation read,write permission
    def _process_sync_user_permission_queue_quotation(self, row_count):
        try:
            self.env.cr.execute("""select document_permission.id as id, file_id, google_email
from document_permission
      left join document_quotation_part
          on document_quotation_part.id = document_permission.res_id
      left join res_users on res_users.id = document_permission.res_user_id
where document_permission.google_drive_permission_id is null and model like 'quotation' and type like 'write'""")
            need_sync_data = self.env.cr.fetchmany(row_count)
            if need_sync_data:
                google_drive_helper = GoogleDriveHelper()
                for e in need_sync_data:
                    try:
                        new_permission = google_drive_helper.create_file_write_permission(e[1], e[2])
                        self.env['document.permission'].sudo().search([('id', '=', e[0])]).write(
                            {'google_drive_permission_id': new_permission})
                    except Exception as ex:
                        # raise UserError(_("Something went wrong, please try again later"))
                        e = 0
            self.env.cr.execute("""select document_permission.id as id, file_id, google_email
            from document_permission
                  left join document_quotation_part
                      on document_quotation_part.id = document_permission.res_id
                  left join res_users on res_users.id = document_permission.res_user_id
            where document_permission.google_drive_permission_id is null and model like 'quotation' and type like 'read'""")
            need_sync_data = self.env.cr.fetchmany(row_count)
            if need_sync_data:
                google_drive_helper = GoogleDriveHelper()
                for e in need_sync_data:
                    try:
                        new_permission = google_drive_helper.create_file_read_permission(e[1], e[2])
                        self.env['document.permission'].sudo().search([('id', '=', e[0])]).write(
                            {'google_drive_permission_id': new_permission})
                    except Exception as ex:
                        # raise UserError(_("Something went wrong, please try again later"))
                        e = 0
        except Exception as ex:
            e = 0

    # crm read,write permission
    def _process_sync_user_permission_queue_crm(self, row_count):
        try:
            self.env.cr.execute("""select document_permission.id as id, file_id, google_email
from document_permission
      left join document_crm_part
          on document_crm_part.id = document_permission.res_id
      left join res_users on res_users.id = document_permission.res_user_id
where document_permission.google_drive_permission_id is null and model like 'crm' and type like 'write'""")
            need_sync_data = self.env.cr.fetchmany(row_count)
            if need_sync_data:
                google_drive_helper = GoogleDriveHelper()
                for e in need_sync_data:
                    try:
                        new_permission = google_drive_helper.create_file_write_permission(e[1], e[2])
                        self.env['document.permission'].sudo().search([('id', '=', e[0])]).write(
                            {'google_drive_permission_id': new_permission})
                    except Exception as ex:
                        # raise UserError(_("Something went wrong, please try again later"))
                        e = 0
            self.env.cr.execute("""select document_permission.id as id, file_id, google_email
            from document_permission
                  left join document_crm_part
                      on document_crm_part.id = document_permission.res_id
                  left join res_users on res_users.id = document_permission.res_user_id
            where document_permission.google_drive_permission_id is null and model like 'crm' and type like 'read'""")
            need_sync_data = self.env.cr.fetchmany(row_count)
            if need_sync_data:
                google_drive_helper = GoogleDriveHelper()
                for e in need_sync_data:
                    try:
                        new_permission = google_drive_helper.create_file_read_permission(e[1], e[2])
                        self.env['document.permission'].sudo().search([('id', '=', e[0])]).write(
                            {'google_drive_permission_id': new_permission})
                    except Exception as ex:
                        # raise UserError(_("Something went wrong, please try again later"))
                        e = 0
        except Exception as ex:
            e = 0

    # Project read,write permission
    def _process_sync_user_permission_queue_project(self, row_count):
        try:
            self.env.cr.execute("""select document_permission.id as id, file_id, google_email
from document_permission
      left join document_project_part
          on document_project_part.id = document_permission.res_id
      left join res_users on res_users.id = document_permission.res_user_id
where document_permission.google_drive_permission_id is null and model like 'project' and type like 'write'""")
            need_sync_data = self.env.cr.fetchmany(row_count)
            if need_sync_data:
                google_drive_helper = GoogleDriveHelper()
                for e in need_sync_data:
                    try:
                        new_permission = google_drive_helper.create_file_write_permission(e[1], e[2])
                        self.env['document.permission'].sudo().search([('id', '=', e[0])]).write(
                            {'google_drive_permission_id': new_permission})
                    except Exception as ex:
                        # raise UserError(_("Something went wrong, please try again later"))
                        e = 0
            self.env.cr.execute("""select document_permission.id as id, file_id, google_email
             from document_permission
                   left join document_project_part
                       on document_project_part.id = document_permission.res_id
                   left join res_users on res_users.id = document_permission.res_user_id
             where document_permission.google_drive_permission_id is null and model like 'project' and type like 'read'""")
            need_sync_data = self.env.cr.fetchmany(row_count)
            if need_sync_data:
                google_drive_helper = GoogleDriveHelper()
                for e in need_sync_data:
                    try:
                        new_permission = google_drive_helper.create_file_read_permission(e[1], e[2])
                        self.env['document.permission'].sudo().search([('id', '=', e[0])]).write(
                            {'google_drive_permission_id': new_permission})
                    except Exception as ex:
                        # raise UserError(_("Something went wrong, please try again later"))
                        e = 0


        except Exception as ex:
            e = 0

    def action_track_permission_change(self):

        google_drive_revision_helper = GoogleDriveRevisionHelper()
        google_drive_revision_helper.sync_google_drive_file_changes()
        google_drive_revision_helper.sync_google_drive_file_revision()
        google_drive_revision_helper.sync_google_drive_file_revision_detail()
        # raise UserError(_("Something went wrong, please try again later"))
        e = 0

# class DocumentGeneralPartReadGroupRel(models.Model):
#     _name = "document.general.part.read.group.rel"
#
#     document_res_id = fields.Integer()
#     res_group_id = fields.Integer()
#     google_drive_permission_id = fields.Char()
#
#     @api.model
#     def create(self, values):
#         folder = super(DocumentGeneralPartReadGroupRel, self).create(values)
#         return folder
