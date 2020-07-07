from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..utils.google_drive_helper import GoogleDriveHelper


class ResUsers(models.Model):
    _inherit = 'res.users'
    google_email = fields.Char(string="Google Email")

    @api.model
    def create(self, vals):
        user = super(ResUsers, self).create(vals)
        if vals.get('google_email'):
            groups = user.groups_id
            group_ids = []
            for e in groups:
                group_ids.append(str(e.id))
            self.env.cr.execute(
                """ select general_part_id from document_general_part_read_group_rel where res_group_id in %s group by general_part_id""",
                (tuple(group_ids),))
            general_part_ids = self.env.cr.fetchall()
            need_to_insert = []
            if general_part_ids is not None and len(general_part_ids) > 0:
                for e in general_part_ids:
                    need_to_insert.append({
                        'type': 'read',
                        'model': 'general',
                        'res_id': e[0],
                        'res_user_id': user.id,
                    })
                self.env['document.permission'].sudo().create(need_to_insert)
                document_general_file_permission_need_insert = []
                # for e in general_part_ids:
                # print('toan')
                self.env.cr.execute(
                    """select file_id from document_general_file where res_id in %s group by file_id""",
                    (tuple(e[0] for e in general_part_ids),))
                all_file_ids = self.env.cr.fetchall()
                for file in all_file_ids:
                    document_general_file_permission_need_insert.append({
                        'type': 'read',
                        'file_id': file[0],
                        'res_user_id': user.id
                    })
                self.env['document.file.permission'].sudo().create(document_general_file_permission_need_insert)
        return user

    def write(self, vals):
        a = super(ResUsers, self).write(vals)
        try:
            is_group_change = False
            for e in vals.keys():
                if 'group' in e:
                    is_group_change = True
            if vals.get('google_email'):
                google_drive_helper = GoogleDriveHelper()
                #     # remove all existing permission
                for user in self:
                    #         # if new_email != email[0]:
                    user_permissions = self.env['document.file.permission'].sudo().search(
                        [('res_user_id', '=', user.id)])
                    need_to_drop_permission = []
                    for e in user_permissions:
                        if e.google_drive_permission_id:
                            need_to_drop_permission.append({
                                'res_user_id': e.res_user_id,
                                'file_id': e.file_id,
                                'google_drive_permission_id': e.google_drive_permission_id,
                                'type': e.type,
                                'status': 'drop error',
                            })
                    self.env['document.file.permission.error'].sudo().create(need_to_drop_permission)
                    user_permissions.write({
                        'google_drive_permission_id': None
                    })
            if is_group_change:
                for rec in self:
                    groups = self.env['res.users'].sudo().browse(rec.id).groups_id
                    groups_ids = []
                    for e in groups:
                        groups_ids.append(str(e.id))
                    self.env.cr.execute(
                        """ select general_part_id from document_general_part_read_group_rel where res_group_id in %s group by general_part_id""",
                        (tuple(groups_ids),))
                    document_part_id = self.env.cr.fetchall()
                    if document_part_id is not None and len(document_part_id) > 0:
                        document_part_id = [e[0] for e in document_part_id]
                        self.env.cr.execute(
                            """select res_id from document_permission where res_user_id=%s and type like 'read' """,
                            (self.id,))
                        document_permission_id = self.env.cr.fetchall()
                        document_permission_id = [e[0] for e in document_permission_id]
                        need_to_add = []
                        for e in document_part_id:
                            if e not in document_permission_id:
                                need_to_add.append({
                                    'type': 'read',
                                    'model': 'general',
                                    'res_id': e,
                                    'res_user_id': rec.id,
                                })
                        self.env['document.permission'].sudo().create(need_to_add)

                        for a in document_permission_id:
                            if a not in document_part_id:
                                self.env['document.permission'].sudo().search(
                                    [('res_id', '=', a), ('res_user_id', '=', rec.id), ('model', '=', 'general'),
                                     ('type', 'like', 'read')]).unlink()
                    else:
                        self.env['document.permission'].sudo().search(
                            [('res_user_id', '=', rec.id), ('model', '=', 'general'),
                             ('type', 'like', 'read')]).unlink()
                    # update user permission file
                    user_file_permission = []
                    # list all file_id user can read
                    self.env.cr.execute("""select file_id
from document_general_file
where res_id in (select res_id from document_permission where model like 'general'
                                                                       and type like 'read'
                                                                       and res_user_id = %s)""", (rec.id,))
                    all_file_ids = self.env.cr.fetchall()
                    if all_file_ids is not None and len(all_file_ids) > 0:
                        all_file_ids = [e[0] for e in all_file_ids]
                        self.env.cr.execute(
                            """select file_id from document_file_permission where type like 'read' and res_user_id = %s group by file_id""",
                            (rec.id,))
                        current_read_file_ids = self.env.cr.fetchall()
                        if current_read_file_ids is None:
                            current_read_file_ids = []
                        else:
                            current_read_file_ids = [e[0] for e in current_read_file_ids]
                        document_file_permission_need_insert = []
                        for e in all_file_ids:
                            if e not in current_read_file_ids:
                                document_file_permission_need_insert.append({
                                    'type': 'read',
                                    'file_id': e,
                                    'res_user_id': rec.id
                                })
                        if len(document_file_permission_need_insert) > 0:
                            self.env['document.file.permission'].sudo().create(document_file_permission_need_insert)
                        self.env['document.file.permission'].sudo().search(
                            [('file_id', 'not in', all_file_ids), ('res_user_id', '=', rec.id),
                             ('type', '=', 'read')]).unlink()
                    else:
                        self.env['document.file.permission'].sudo().search(
                            [('res_user_id', '=', rec.id)]).unlink()
        except Exception as ex:
            print(ex)
        # Not throw exception to raise error
        if 'active' in vals and vals['active'] == False:
            for rec in self:
                # drop permission
                self.env['document.permission'].sudo().search(
                    [('res_user_id', '=', rec.id)]).unlink()
                self.env['document.file.permission'].sudo().search(
                    [('res_user_id', '=', rec.id)]).unlink()
                # delete from crm
                self.env.cr.execute(
                    """DELETE FROM document_crm_file_read_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_crm_file_write_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_crm_part_write_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_crm_part_read_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_crm_file_res_users_rel where res_users_id=%s """, (rec.id,))
                # delete from project
                self.env.cr.execute(
                    """DELETE FROM document_project_file_read_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_project_file_write_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_project_part_write_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_project_part_read_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_project_file_res_users_rel where res_users_id=%s """, (rec.id,))
                # delete from quotation
                self.env.cr.execute(
                    """DELETE FROM document_quotation_file_read_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_quotation_file_write_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_quotation_part_write_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_quotation_part_read_user_rel where res_user_id=%s """, (rec.id,))
                self.env.cr.execute(
                    """DELETE FROM document_quotation_file_res_users_rel where res_users_id=%s """, (rec.id,))
                # delete from general
                self.env.cr.execute(
                    """DELETE FROM document_general_part_write_user_rel where res_user_id=%s """, (rec.id,))

        if 'active' in vals and vals['active'] == True:
            for rec in self:
                user_in_process = self.env['document.file.permission.error'].sudo().search([('res_user_id', '=', rec.id)])
                if len(user_in_process) > 0:
                    raise UserError(_('This user is being processed by the system, please wait or try again later!'))
                else:
                    groups = rec.groups_id
                    group_ids = []
                    for e in groups:
                        group_ids.append(str(e.id))
                    self.env.cr.execute(
                        """ select general_part_id from document_general_part_read_group_rel where res_group_id in %s group by general_part_id""",
                        (tuple(group_ids),))
                    general_part_ids = self.env.cr.fetchall()
                    need_to_insert = []
                    if general_part_ids is not None and len(general_part_ids) > 0:
                        for e in general_part_ids:
                            need_to_insert.append({
                                'type': 'read',
                                'model': 'general',
                                'res_id': e[0],
                                'res_user_id': rec.id,
                            })
                        self.env['document.permission'].sudo().create(need_to_insert)
                        document_general_file_permission_need_insert = []
                        # for e in general_part_ids:
                        # print('toan')
                        self.env.cr.execute(
                            """select file_id from document_general_file where res_id in %s group by file_id""",
                            (tuple(e[0] for e in general_part_ids),))
                        all_file_ids = self.env.cr.fetchall()
                        for file in all_file_ids:
                            document_general_file_permission_need_insert.append({
                                'type': 'read',
                                'file_id': file[0],
                                'res_user_id': rec.id
                            })
                        self.env['document.file.permission'].sudo().create(document_general_file_permission_need_insert)

        return a

    def unlink(self):
        for rec in self:
            self.env['document.permission'].sudo().search(
                [('res_user_id', '=', rec.id)]).unlink()
            self.env['document.file.permission'].sudo().search(
                [('res_user_id', '=', rec.id)]).unlink()
        return super(ResUsers, self).unlink()

    def _process_drop_out_inactive_permission_queue(self):
        try:
            # Get all user inactive
            self.env.cr.execute(
                """ select id from res_users where active is FALSE""",)
            users = self.env.cr.fetchall()
            for user in users:
                user_id = user[0]
                # drop permission
                self.env['document.permission'].sudo().search(
                    [('res_user_id', '=', user_id)]).unlink()
                self.env['document.file.permission'].sudo().search(
                    [('res_user_id', '=', user_id)]).unlink()
                # delete from crm
                self.env.cr.execute(
                    """DELETE FROM document_crm_file_read_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_crm_file_write_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_crm_part_write_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_crm_part_read_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_crm_file_res_users_rel where res_users_id=%s """, (user_id,))
                # delete from project
                self.env.cr.execute(
                    """DELETE FROM document_project_file_read_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_project_file_read_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_project_part_write_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_project_part_read_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_project_file_res_users_rel where res_users_id=%s """, (user_id,))
                # delete from quotation
                self.env.cr.execute(
                    """DELETE FROM document_quotation_file_read_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_quotation_file_read_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_quotation_part_write_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_quotation_part_read_user_rel where res_user_id=%s """, (user_id,))
                self.env.cr.execute(
                    """DELETE FROM document_quotation_file_res_users_rel where res_users_id=%s """, (user_id,))
                # delete from general
                self.env.cr.execute(
                    """DELETE FROM document_general_part_write_user_rel where res_user_id=%s """, (user_id,))
        except Exception as ex:
            print(ex)
        return True

