from odoo import models, api
from ..utils.google_drive_helper import GoogleDriveHelper


class ResGroups(models.Model):
    _inherit = 'res.groups'

    def write(self, vals):
        init_users = set(u.id for u in self.users)
        # Call super
        group = super(ResGroups, self).write(vals)
        # get all users in groups after edit
        if self.users:
            users = [user.id for user in self.users]
        else:
            users = []
        need_add = [add for add in users if add not in init_users]
        need_users_add_data = []
        for user_id in need_add:
            email = self.env['res.users'].sudo().search([('id', '=', user_id)]).google_email
            need_users_add_data.append([user_id, email])
        need_remove = [remove for remove in init_users if remove not in users]
        try:
            is_users_change = False
            for e in vals.keys():
                if 'users' in e:
                    is_users_change = True
            if is_users_change:
                google_drive_helper = GoogleDriveHelper()
                for rec in self:
                    #     # remove all not permission anymore
                    self.env.cr.execute(
                        """ select general_part_id from document_general_part_read_group_rel where res_group_id = %s group by general_part_id""",
                        (rec.id,))
                    general_part_ids = self.env.cr.fetchall()
                    if general_part_ids is not None and len(general_part_ids) > 0:
                        document_part_ids = [e[0] for e in general_part_ids]
                        # find all childen file
                        all_children_files = self.env['document.general.file'].sudo().search(
                            [('res_id', 'in', document_part_ids)])
                        permission_files = []
                        if len(all_children_files) > 0:
                            for file in all_children_files:
                                permissions = self.env['document.file.permission'].sudo().search(
                                    [('file_id', '=', file.file_id), ('type','=','read')])
                                if len(permissions) > 0:
                                    for permission in permissions:
                                        permission_files.append(permission)
                        if len(permission_files) > 0:
                            for user_permission in permission_files:
                                # remove and drop permission file
                                if user_permission.res_user_id in need_remove:
                                    if user_permission.google_drive_permission_id:
                                        try:
                                            google_drive_helper.drop_file_permission(user_permission.file_id,
                                                                                     user_permission.google_drive_permission_id)
                                            user_permission.unlink()
                                        except Exception as e:
                                            """Need handle when drop error"""
                                            need_to_drop_permission = []
                                            need_to_drop_permission.append({
                                                'res_user_id': user_permission.res_user_id,
                                                'file_id': user_permission.file_id,
                                                'google_drive_permission_id': user_permission.google_drive_permission_id,
                                                'type': 'read',
                                                'status': 'drop error',
                                            })
                                            self.env['document.file.permission.error'].sudo().create(
                                                need_to_drop_permission)
                                            user_permission.write({
                                                'google_drive_permission_id': None
                                            })
                                    # Drop document.permission
                                    for part_id in document_part_ids:
                                        self.env['document.permission'].sudo().search(
                                            [('res_id', '=', part_id), ('res_user_id', 'in', need_remove),
                                             ('model', '=', 'general'),
                                             ('type', 'like', 'read')]).unlink()
                        # add new permission
                        if len(all_children_files) > 0:
                            for file in all_children_files:
                                for rec in need_users_add_data:
                                    try:
                                        new_permission = google_drive_helper.create_file_read_permission(
                                            file.file_id,
                                            rec[1])
                                        # permission file
                                        document_file_permission_need_insert = []
                                        document_file_permission_need_insert.append({
                                            'type': 'read',
                                            'file_id': file.file_id,
                                            'res_user_id': rec[0],
                                            'google_drive_permission_id': new_permission
                                        })
                                        self.env['document.file.permission'].sudo().create(
                                            document_file_permission_need_insert)
                                    except Exception as e:
                                        document_file_permission_need_insert = []
                                        document_file_permission_need_insert.append({
                                            'type': 'read',
                                            'file_id': file.file_id,
                                            'res_user_id': rec[0]
                                        })
                                        self.env['document.file.permission'].sudo().create(
                                            document_file_permission_need_insert)
                                    # permission folder
                                    if len(document_part_ids) > 0:
                                        for part_id in document_part_ids:
                                            need_to_add = []
                                            need_to_add.append({
                                                'type': 'read',
                                                'model': 'general',
                                                'res_id': part_id,
                                                'res_user_id': rec[0],
                                            })
                                            self.env['document.permission'].sudo().create(need_to_add)
        except Exception as e:
            """Sh@dowWalker"""
        return group

    def unlink(self):
        for rec in self:
            # if len(rec.users) > 0:
            #     group_users_ids = [user.id for user in rec.users]
            #     for user_id in group_users_ids:
            #         self.env['document.permission'].sudo().search(
            #             [('res_user_id', '=', user_id)]).unlink()
            #         self.env['document.file.permission'].sudo().search(
            #             [('res_user_id', '=', user_id)]).unlink()
            # find all general part has res_groups = rec
            self.env.cr.execute(
                """ select general_part_id from document_general_part_read_group_rel where res_group_id = %s group by general_part_id""",
                (rec.id,))
            general_part_ids = self.env.cr.fetchall()
            if general_part_ids is not None and len(general_part_ids) > 0:
                document_part_ids = [e[0] for e in general_part_ids]
                document_general_parts = self.env['document.general.part'].sudo().search([('id', 'in', document_part_ids)])
                # drop this group out of res_groups's general_part (permission will be drop following)
                document_general_parts.sudo().write({
                    'read_groups': [(3, rec.id)]
                })
        return super(ResGroups, self).unlink()
