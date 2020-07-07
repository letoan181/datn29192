import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..utils.google_drive_helper import GoogleDriveHelper


class DocumentGeneralFile(models.Model):
    _name = "document.general.file"
    _inherit = ['mail.thread', 'mail.activity.mixin', ]
    _description = "Manage document files"

    @api.model
    def _compute_is_favorite(self):
        for document in self:
            document.is_favorite = self.env.user in document.favorite_user_ids

    def _inverse_is_favorite(self):
        favorite_document = not_fav_document = self.env['document.general.file'].sudo()
        for document in self:
            if self.env.user in document.favorite_user_ids:
                favorite_document |= document
            else:
                not_fav_document |= document
        # Project User has no write access for project.
        favorite_document.write({'favorite_user_ids': [(3, self.env.uid)]})
        not_fav_document.write({'favorite_user_ids': [(4, self.env.uid)]})
        return True

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    name = fields.Char(string="File Name", required=True, track_visibility='onchange')
    type = fields.Selection(
        [('doc', 'Doc'), ('excel', 'Excel'), ('power_point', 'PowerPoint'), ('folder', '#Folder Beta')], required=True,
        default='doc')
    res_id = fields.Integer(string="Related Model ID", required=True)
    # document_file_id = fields.Many2one('document.quotation.part', inverse_name='name', string="Document",
    #                                       ondelete='cascade', required=True)
    favorite_user_ids = fields.Many2many(
        'res.users', 'document_file_favorite_user_rel', 'document_id', 'user_id',
        string='Favorite Members',
        default=_get_default_favorite_user_ids)
    is_favorite = fields.Boolean(
        string='Show on dashboard',
        compute='_compute_is_favorite', inverse='_inverse_is_favorite',
        help="Favorite teams to display them in the dashboard and access them easily.")
    google_drive_url = fields.Char(string="File URL", readonly=True)
    file_id = fields.Char(string="File ID", readonly=True)
    color = fields.Integer(string='Color Index')

    # can edit
    current_permission_can_update = fields.Boolean(compute='_compute_current_permission_can_update', default=False,
                                                   store=False)

    def _compute_current_permission_can_update(self):
        for e in self:
            e.current_permission_can_update = False
            if self.user_has_groups('base.group_system'):
                e['current_permission_can_update'] = True
            elif self.user_has_groups('document_management.group_document_general_part_manager'):
                e['current_permission_can_update'] = True
            else:
                if e.create_uid.id == self._uid:
                    e['current_permission_can_update'] = True
    @api.model
    def action_document_general_file_list(self):
        # Dung de khoi tao view voi domain chay bang python
        if self.user_has_groups('base.group_system'):
            domain = []
        else:
            self.env.cr.execute(
                """select id from document_general_file where res_id in (select document_permission.res_id from document_permission where model like 'general' and res_user_id=%s)""",
                (self._uid,))
            can_read_documents = self.env.cr.fetchall()
            domain = [('id', 'in', [val[0] for val in can_read_documents])]
        views = [(self.env.ref('document_management.general_document_action_document_general_part_file_kanban').id,
                  'kanban'),
                 (self.env.ref('document_management.view_document_general_file_form').id, 'form')]
        action = {"name": "General Documents", "type": "ir.actions.act_window", "view_mode": "kanban,form",
                  "view_type": "form", "context": {"create": False},
                  "res_model": "document.general.file", 'domain': domain, 'view_id': False,
                  'views': views}
        return action

    def call_back_parent_root(self):
        res = self.env['document.general.part'].sudo().browse(self.res_id)
        context = {'active_id': res.document_general_id.id}
        action = res.document_general_id.get_general_document_action_document_part(context)
        action['target'] = 'main'
        return action

    def call_back_parent_part(self, context=None):
        res = self.env['document.general.part'].sudo().browse(self.res_id)
        action = res.get_general_document_action_document_part_file(context)
        action['target'] = 'main'
        return action

    @api.model
    def create(self, vals):
        if vals.get('res_id'):
            ##check if can create
            can_create = False
            if self.user_has_groups('base.group_system'):
                can_create = True
            elif self.user_has_groups('document_management.group_document_general_manager'):
                can_create = True
            else:
                self.env.cr.execute(
                    """select res_user_id from document_general_part_write_user_rel where res_user_id=%s and general_part_id=%s """,
                    (self._uid, vals.get('res_id'),))
                current_user_permission = self.env.cr.fetchone()
                if current_user_permission is not None and len(current_user_permission) > 0:
                    can_create = True
            if can_create:
                # update on google drive
                Config = self.env['ir.config_parameter'].sudo()
                file_template_id = ''
                parent_file_id = ''
                file_name = vals.get('name')
                file_type = vals.get('type')
                if file_type == 'doc':
                    vals['color'] = 4
                elif file_type == 'excel':
                    vals['color'] = 10
                elif file_type == 'power_point':
                    vals['color'] = 3
                else:
                    vals['color'] = 5
                # find parent file id
                parent_file_id = self.env['document.general.part'].sudo().search([('id', '=', vals.get('res_id'))],
                                                                                 limit=1).file_id
                # find template id
                template_url = False
                if file_type != 'folder':
                    if file_type == 'doc':
                        template_url = Config.get_param('document_management.doc_file_template')
                    elif file_type == 'excel':
                        template_url = Config.get_param('document_management.sheet_file_template')
                    elif file_type == 'power_point':
                        template_url = Config.get_param('document_management.power_point_file_template')
                    if template_url is False or len(template_url) == 0:
                        raise UserError(_("Please config file template on General Settings"))
                    template_ids = re.search("(key=|/d/)([A-Za-z0-9-_]+)", template_url)
                    if template_ids:
                        file_template_id = template_ids.group(2)
                    else:
                        raise UserError(_("Can't get file id from file url"))
                    google_drive_helper = GoogleDriveHelper()
                    google_drive_new_file = google_drive_helper.create_copy(source_file_id=file_template_id,
                                                                            parent_file_id=parent_file_id,
                                                                            file_name=file_name)
                else:
                    google_drive_helper = GoogleDriveHelper()
                    google_drive_new_file = google_drive_helper.create_sub_file(parent_id=parent_file_id,
                                                                                folder_name=file_name)

                vals['file_id'] = google_drive_new_file['id']
                if file_type == 'doc':
                    vals['google_drive_url'] = 'https://docs.google.com/' + 'document' + '/d/' + google_drive_new_file[
                        'id']
                elif file_type == 'excel':
                    vals['google_drive_url'] = 'https://docs.google.com/' + 'spreadsheets' + '/d/' + \
                                               google_drive_new_file[
                                                   'id']
                elif file_type == 'power_point':
                    vals['google_drive_url'] = 'https://docs.google.com/' + 'presentation' + '/d/' + \
                                               google_drive_new_file[
                                                   'id']
                elif file_type == 'folder':
                    vals['google_drive_url'] = 'https://drive.google.com/drive/folders/' + google_drive_new_file[
                        'id']
                result = super(DocumentGeneralFile, self).create(vals)
                # update write user

                # find all write users
                self.env.cr.execute(
                    """select res_user_id from document_general_part_write_user_rel where general_part_id = %s group by res_user_id""",
                    (result.res_id,))
                all_write_user_ids = self.env.cr.fetchall()
                if all_write_user_ids is not None and len(all_write_user_ids) > 0:
                    # delete all write permission if its user dont have permission anymore
                    self.env['document.file.permission'].sudo().search(
                        [('type', 'like', 'write'), ('file_id', '=', google_drive_new_file['id']),
                         ('res_user_id', 'not in', tuple(e[0] for e in all_write_user_ids))]).unlink()
                    # find current write user ids
                    self.env.cr.execute(
                        """select res_user_id from document_file_permission where type like 'write' and file_id like %s""",
                        (google_drive_new_file['id'],))
                    current_write_user_ids = self.env.cr.fetchall()
                    new_write_user_ids = []
                    for e in all_write_user_ids:
                        if e[0] not in list(a[0] for a in current_write_user_ids):
                            new_write_user_ids.append(e[0])
                    for e in new_write_user_ids:
                        self.env['document.file.permission'].sudo().create({
                            'type': 'write',
                            'file_id': google_drive_new_file['id'],
                            'res_user_id': e,
                        })
                    # delete all read permission if its user already has write permission
                    self.env.cr.execute(
                        """delete from document_file_permission where file_id like %s and type like 'read' and res_user_id in %s""",
                        (google_drive_new_file['id'], tuple(e[0] for e in all_write_user_ids),))
                else:
                    self.env['document.file.permission'].sudo().search(
                        [('type', 'like', 'write'), ('file_id', '=', google_drive_new_file['id'])]).unlink()
                # update read users
                # list all new read users
                # list all user group can read only
                self.env.cr.execute(
                    """select res_group_id from document_general_part_read_group_rel where general_part_id = %s""",
                    (result.res_id,))
                all_read_group_ids = self.env.cr.fetchall()
                if all_read_group_ids is not None and len(all_read_group_ids) > 0:
                    all_read_group_ids = [e[0] for e in all_read_group_ids]
                    all_read_user_ids = self.get_user_id_from_group_list(all_read_group_ids)
                    if all_read_user_ids is not None and len(all_read_user_ids) > 0:
                        # get current read users
                        self.env.cr.execute(
                            """select res_user_id from document_file_permission where type like 'read' and file_id like %s""",
                            (google_drive_new_file['id'],))
                        current_read_user_ids = self.env.cr.fetchall()
                        # delete all document permission not in read groups and write users
                        self.env['document.file.permission'].sudo().search(
                            [('type', 'like', 'read'), ('file_id', '=', google_drive_new_file['id']),
                             ('res_user_id', 'not in', list(str(a[0]) for a in all_write_user_ids))
                                , ('res_user_id', 'not in', all_read_group_ids)]).unlink()
                        self.env['document.file.permission'].sudo().search(
                            [('type', 'like', 'read'), ('file_id', '=', google_drive_new_file['id']),
                             ('res_user_id', 'in', list(str(a[0]) for a in all_write_user_ids))]).unlink()
                        for e in all_read_user_ids:
                            if e not in list(a[0] for a in all_write_user_ids) and e not in list(
                                    b[0] for b in current_read_user_ids):
                                self.env['document.file.permission'].sudo().create({
                                    'type': 'read',
                                    'file_id': google_drive_new_file['id'],
                                    'res_user_id': e,
                                })

                return result
            else:
                raise UserError(_("You don't have permission to do this action"))
        else:
            raise UserError(_("You don't have permission to do this action"))

    def write(self, values):
        # update on google drive
        current_file = self.env['document.general.file'].sudo().browse(self.id)
        if values.get('name'):
            google_drive_helper = GoogleDriveHelper()
            google_drive_helper.update_file_name(file_id=current_file['file_id'], new_name=values.get('name'))
        if values.get('is_favorite'):
            values.pop('is_favorite')
            self._fields['is_favorite'].determine_inverse(self)
        folder = super(DocumentGeneralFile, self).write(values)
        return folder

    def unlink(self):
        google_drive_helper = GoogleDriveHelper()
        for e in self:
            try:
                google_drive_helper.deleteFile(file_id=e['file_id'])
            except Exception as ex:
                a = 0
        for e in self:
            self.env['document.file.permission'].sudo().search(
                [('file_id', '=', e.file_id)]).unlink()
        return super(DocumentGeneralFile, self).unlink()

    def get_user_id_from_group(self, group_id):
        users_ids = []
        sql_query = """select uid from res_groups_users_rel where gid = %s"""
        params = (group_id,)
        self.env.cr.execute(sql_query, params)
        results = self.env.cr.fetchall()
        for users_id in results:
            users_ids.append(users_id[0])
        return users_ids

    def get_user_id_from_group_list(self, group_ids):
        users_ids = []
        sql_query = """select uid from res_groups_users_rel where gid in %s group by uid"""
        params = (tuple(str(e) for e in group_ids),)
        self.env.cr.execute(sql_query, params)
        results = self.env.cr.fetchall()
        for users_id in results:
            users_ids.append(users_id[0])
        return users_ids

    def action_fetch_file_permission(self):
        for rec in self:
            file_errors = self.env['document.file.permission.error'].sudo().search([('file_id', '=', rec.file_id)])
            if len(file_errors) > 0:
                raise UserError(_('Can not update permission right now.Try again in few seconds.'))
            try:
                self.env.cr.execute("""select document_file_permission.id as id, file_id, google_email
                from document_file_permission left join res_users on res_users.id = document_file_permission.res_user_id
                where document_file_permission.google_drive_permission_id is null and document_file_permission.status is NULL and type like 'write' and res_users.active is true and res_users.google_email is not null and file_id like %s """,
                                    (rec.file_id,))
                need_sync_data = self.env.cr.fetchall()
                if need_sync_data:
                    google_drive_helper = GoogleDriveHelper()
                    for e in need_sync_data:
                        # mark in process for this record
                        self.env.cr.execute(
                            """update document_file_permission set status = 'in_process' WHERE id=%s""", (e[0],))
                        self.env.cr.commit()
                        try:
                            new_permission = google_drive_helper.create_file_write_permission(e[1], e[2])
                            self.env['document.file.permission'].sudo().search([('id', '=', e[0])]).write(
                                {'google_drive_permission_id': new_permission,
                                 'status': False})
                        except Exception as ex:
                            self.env['document.file.permission'].sudo().search([('id', '=', e[0])]).write(
                                {'status': 'error',
                                 'error_message': str(ex)})
                            # raise UserError(_("Something went wrong, please try again later"))
                            e = 0
            except Exception as ex:
                e = 0
            try:
                self.env.cr.execute("""select document_file_permission.id as id, file_id, google_email
                       from document_file_permission left join res_users on res_users.id = document_file_permission.res_user_id
                       where document_file_permission.google_drive_permission_id is null and document_file_permission.status is null and type like 'read' and res_users.active is true and res_users.google_email is not null and file_id like %s """,
                                    (rec.file_id,))
                need_sync_data = self.env.cr.fetchall()
                if need_sync_data:
                    google_drive_helper = GoogleDriveHelper()
                    for e in need_sync_data:
                        # mark in process for this record
                        self.env.cr.execute(
                            """update document_file_permission set status = 'in_process' WHERE id=%s""", (e[0],))
                        self.env.cr.commit()
                        try:
                            new_permission = google_drive_helper.create_file_read_permission(e[1], e[2])
                            self.env['document.file.permission'].sudo().search([('id', '=', e[0])]).write(
                                {'google_drive_permission_id': new_permission,
                                 'status': False})
                        except Exception as ex:
                            self.env['document.file.permission'].sudo().search([('id', '=', e[0])]).write(
                                {'status': 'error',
                                 'error_message': str(ex)})
                            # raise UserError(_("Something went wrong, please try again later"))
                            e = 0
            except Exception as ex:
                e = 0
