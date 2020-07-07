from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..utils.google_drive_helper import GoogleDriveHelper


class DocumentGeneral(models.Model):
    _name = "document.general"
    # _inherit = ['portal.mixin', 'mail.alias.mixin', 'mail.thread']
    _description = "Manage document by user groups or user"

    @api.model
    def _compute_is_favorite(self):
        for document in self:
            document.is_favorite = self.env.user in document.favorite_user_ids

    def _inverse_is_favorite(self):
        favorite_document = not_fav_document = self.env['document.general'].sudo()
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

    name = fields.Char(required=True)
    google_drive_url = fields.Char(readonly=True)
    file_id = fields.Char(readonly=True)
    part_ids = fields.One2many('document.general.part', 'document_general_id',
                               string='Document Part')

    favorite_user_ids = fields.Many2many(
        'res.users', 'document_favorite_user_rel', 'document_id', 'user_id',
        string='Favorite Members',
        default=_get_default_favorite_user_ids)
    is_favorite = fields.Boolean(
        string='Show on dashboard',
        compute='_compute_is_favorite', inverse='_inverse_is_favorite',
        help="Favorite teams to display them in the dashboard and access them easily.")
    color = fields.Integer(string='Color Index')
    current_permission_can_update = fields.Boolean(compute='_compute_current_permission_can_update', default=False,
                                                   store=False)

    def _compute_current_permission_can_update(self):
        for e in self:
            e.current_permission_can_update = False
            if self.user_has_groups('base.group_system'):
                e['current_permission_can_update'] = True
            elif self.user_has_groups('document_management.group_document_general_manager'):
                e['current_permission_can_update'] = True
            else:
                if e.create_uid.id == self._uid:
                    e['current_permission_can_update'] = True

    def action_document_general_list(self):
        # Dung de khoi tao view voi domain chay bang python
        if self.user_has_groups('base.group_system'):
            domain = []
        else:
            self.env.cr.execute(
                """select document_general_id from document_general_part where id in  (select res_id from document_permission where res_user_id=%s and model like 'general' group by res_id)""",
                (self._uid,))
            can_read_documents = self.env.cr.fetchall()
            domain = [('id', 'in', [val[0] for val in can_read_documents])]
        action = {"name": "General Documents", "type": "ir.actions.act_window", "view_mode": "kanban,form,folder",
                  "view_type": "form",
                  "res_model": "document.general", 'domain': domain}
        return action

    # @api.model
    # def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
    #     """ Override _search in order to grep search on email field and make it
    #     lower-case and sanitized """
    #     print(domain)
    #     return super(DocumentGeneral, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def create(self, values):
        if self.user_has_groups('document_management.group_document_general_manager'):
            Config = self.env['ir.config_parameter'].sudo()
            parent_file_url = Config.get_param('document_management.general_folder_base')
            if parent_file_url is not False and len(parent_file_url) > 0:
                parent_file_url_arr = parent_file_url.split('/')
                parent_id = parent_file_url_arr[len(parent_file_url_arr) - 1]
                google_drive_helper = GoogleDriveHelper()
                google_drive_new_folder = google_drive_helper.create_sub_file(parent_id=parent_id,
                                                                              folder_name=values.get('name'))
                values['google_drive_url'] = 'https://drive.google.com/drive/folders/' + google_drive_new_folder['id']
                values['file_id'] = google_drive_new_folder['id']
                folder = super(DocumentGeneral, self).create(values)
                # trigger create document
                # bus = self.env['bus.bus']
                # bus.sendone('auto_refresh_folder_view', self._name)
                # record = next(iter(self)) if len(self) > 1 else self
                # a=self.env['bus.bus'].sendone('refresh', {
                #     'create': record.exists() and record.create_date == record.write_date or False,
                #     'model':  self._name,
                #     'uid': self.env.user.id,
                #     'ids': self.mapped('id')})
                return folder
            else:
                raise UserError(_("Please config general folder base in General Setting"))
        else:
            raise UserError(_("You don't have permission to do this action"))

    def _compute_is_readable(self):
        for event in self:
            event.is_readable = '1,2,3'

    def write(self, values):
        if values.get('is_favorite') and len(values) == 1:
            values.pop('is_favorite')
            self._fields['is_favorite'].determine_inverse(self)
            return super(DocumentGeneral, self).write(values) if values else True
        elif values.get('favorite_user_ids') and len(values) == 1:
            return super(DocumentGeneral, self).write(values)
        else:
            if self.user_has_groups('document_management.group_document_general_manager'):
                if values.get('name'):
                    google_drive_helper = GoogleDriveHelper()
                    google_drive_helper.update_file_name(file_id=self['file_id'], new_name=values.get('name'))
                folder = super(DocumentGeneral, self).write(values)
                return folder
            else:
                raise UserError(_("You don't have permission to do this action"))

    def unlink(self):
        try:
            google_drive_helper = GoogleDriveHelper()
            for e in self:
                google_drive_helper.deleteFile(file_id=e['file_id'])
        except Exception as ex:
            a = 0
        for e in self:
            self.env['document.general.part'].sudo().search(
                [('document_general_id', '=', e.id)]).unlink()
        return super(DocumentGeneral, self).unlink()

    def get_general_document_action_document_part(self, context=None):
        if not context:
            context = self._context
        domain = [('document_general_id', '=', context['active_id'])]
        if not self.user_has_groups('base.group_system'):
            self.env.cr.execute(
                """select res_id from document_permission where res_user_id=%s and model like 'general' group by res_id""",
                (self._uid,))
            can_read_documents = self.env.cr.fetchall()
            domain.append(('id', 'in', [val[0] for val in can_read_documents]))
        action = {"name": self.name, "type": "ir.actions.act_window", "view_mode": "kanban,form",
                  "view_type": "form",
                  "res_model": "document.general.part", "context": {"create": False}, 'domain': domain}
        return action


class DocumentGeneralPart(models.Model):
    _name = "document.general.part"
    _description = "Each general document contain some parts"

    name = fields.Char(required=True)
    document_general_id = fields.Many2one('document.general', inverse_name='name', string="Document",
                                          ondelete='cascade', required=True)
    google_drive_url = fields.Char(readonly=True)
    file_id = fields.Char(readonly=True)
    write_users = fields.Many2many('res.users', 'document_general_part_write_user_rel', 'general_part_id',
                                   'res_user_id',
                                   string='Write Users')
    read_groups = fields.Many2many('res.groups', 'document_general_part_read_group_rel', 'general_part_id',
                                   'res_group_id',
                                   string='Read Groups')

    color = fields.Integer(string='Color Index')
    current_permission_can_update = fields.Boolean(compute='_compute_current_permission_can_update', default=False,
                                                   store=False)

    def _compute_current_permission_can_update(self):
        for e in self:
            e.current_permission_can_update = False
            if self.user_has_groups('base.group_system'):
                e['current_permission_can_update'] = True
            else:
                if e.create_uid.id == self._uid:
                    e['current_permission_can_update'] = True

    def get_general_document_action_document_part_file(self, context=None):
        # domain = [('document_file_id', '=', context['active_id'])]
        # self.env.cr.execute(
        #     """select file_id from document_file""")
        # documents_file = self.env.cr.fetchall()
        # domain.append(('id', 'in', [val[0] for val in documents_file]))
        can_create = False
        if not context:
            context = self._context
        if self.user_has_groups('base.group_system'):
            can_create = True
        self.env.cr.execute(
            """select res_user_id from document_general_part_write_user_rel where res_user_id=%s and general_part_id=%s """,
            (self._uid, self.ids[0],))
        document_permission = self.env.cr.fetchone()
        if document_permission is not None and len(document_permission) > 0:
            can_create = True
        self.env.cr.execute(
            """select res_user_id from document_general_part_write_user_rel where res_user_id=%s and general_part_id=%s """,
            (self._uid, self.ids[0],))
        domain = [('0', '=', '1')]
        if can_create:
            domain = [('res_id', '=', context['active_id'])]
        else:
            self.env.cr.execute(
                """select id from document_permission where res_user_id=%s and model='general' """,
                (self._uid,))
            found_ids = self.env.cr.fetchone()
            if found_ids and len(found_ids) > 0:
                domain = [('res_id', '=', context['active_id'])]
        action = {"name": self.name, "type": "ir.actions.act_window", "view_mode": "kanban,form",
                  "view_type": "form",
                  "res_model": "document.general.file",
                  "context": {"create": can_create, 'default_res_id': self.id},
                  'domain': domain}
        return action

    def call_back_parent_root(self):
        action = self.document_general_id.action_document_general_list()
        action['target'] = 'main'
        return action

    @api.model
    def create(self, values):
        if self.user_has_groups('document_management.group_document_general_part_manager'):
            google_drive_helper = GoogleDriveHelper()
            new_folder = google_drive_helper.create_sub_file(self.env['document.general'].sudo().browse(
                values['document_general_id']).file_id, values.get('name'))
            values['google_drive_url'] = 'https://drive.google.com/drive/folders/' + new_folder['id']
            values['file_id'] = new_folder['id']
            folder = super(DocumentGeneralPart, self).create(values)
            if values.get('write_users'):
                for e in values.get('write_users')[0][2]:
                    self.env['document.permission'].sudo().create({
                        'type': 'write',
                        'model': 'general',
                        'res_id': folder.id,
                        'res_user_id': e,
                    })
            if values.get('read_groups'):
                group_ids = []
                for e in values.get('read_groups')[0][2]:
                    group_ids.append(e)
                if len(group_ids) > 0:
                    user_ids = self.get_user_id_from_group_list(group_ids)
                    for uid in user_ids:
                        if values.get('write_users'):
                            if uid not in values.get('write_users')[0][2]:
                                self.env['document.permission'].sudo().create({
                                    'type': 'read',
                                    'model': 'general',
                                    'res_id': folder.id,
                                    'res_user_id': uid,
                                })
                        else:
                            self.env['document.permission'].sudo().create({
                                'type': 'read',
                                'model': 'general',
                                'res_id': folder.id,
                                'res_user_id': uid,
                            })
            return folder
        else:
            raise UserError(_("You don't have permission to do this action"))

    def write(self, values):
        for rec in self:
            if self.user_has_groups('document_management.group_document_general_part_manager'):
                folder = super(DocumentGeneralPart, self).write(values)
                # update file name
                if values.get('name'):
                    google_drive_helper = GoogleDriveHelper()
                    google_drive_helper.update_file_name(rec['file_id'], values.get('name'))
                # update file permission
                # list all new write users
                # find all write users
                self.env.cr.execute(
                    """select res_user_id from document_general_part_write_user_rel where general_part_id = %s""",
                    (rec.id,))
                all_write_user_ids = self.env.cr.fetchall()
                if values.get('write_users') or values.get('read_groups'):
                    self.env.cr.execute(
                        """select file_id from document_general_file where res_id=%s""",
                        (rec.id,))
                    all_file_ids = self.env.cr.fetchall()
                    if all_write_user_ids is not None and len(all_write_user_ids) > 0:
                        # delete all write permission if its user dont have permission anymore
                        self.env['document.permission'].sudo().search(
                            [('model', 'like', 'general'), ('type', 'like', 'write'), ('res_id', '=', rec.id),
                             ('res_user_id', 'not in', tuple(e[0] for e in all_write_user_ids))]).unlink()
                        # find current write user ids
                        self.env.cr.execute(
                            """select res_user_id from document_permission where model like 'general' and type like 'write' and res_user_id in %s and res_id=%s""",
                            (tuple(e[0] for e in all_write_user_ids), rec.id,))
                        current_write_user_ids = self.env.cr.fetchall()
                        new_write_user_ids = []
                        for e in all_write_user_ids:
                            if e[0] not in list(a[0] for a in current_write_user_ids):
                                new_write_user_ids.append(e[0])
                        for e in new_write_user_ids:
                            self.env['document.permission'].sudo().create({
                                'type': 'write',
                                'model': 'general',
                                'res_id': rec.id,
                                'res_user_id': e,
                            })
                        # delete all read permission if its user already has write permission
                        self.env.cr.execute(
                            """delete from document_permission where model like 'general' and type like 'read' and res_user_id in %s and res_id=%s""",
                            (tuple(e[0] for e in all_write_user_ids), rec.id,))

                        ## update document file permission
                        # self.env.cr.execute(
                        #     """select file_id from document_file_permission where model like 'general' and type like 'read' and res_user_id in %s and res_id=%s""",
                        #     (tuple(e[0] for e in all_write_user_ids), self.id,))
                        ## delete all write permission if its user dont have permission anymore
                        if all_file_ids is not None and len(all_file_ids) > 0:
                            self.env['document.file.permission'].sudo().search(
                                [('type', 'like', 'write'), ('file_id', 'in', tuple(e[0] for e in all_file_ids)),
                                 ('res_user_id', 'not in', tuple(e[0] for e in all_write_user_ids))]).unlink()
                            ## update document file write permission for all new user
                            new_document_file_permission = []
                            for e in new_write_user_ids:
                                for file_id_item in all_file_ids:
                                    new_document_file_permission.append({
                                        'res_user_id': e,
                                        'type': 'write',
                                        'file_id': file_id_item[0],
                                    })
                            self.env['document.file.permission'].sudo().create(new_document_file_permission)
                    else:
                        self.env['document.permission'].sudo().search(
                            [('model', 'like', 'general'), ('type', 'like', 'write'), ('res_id', '=', rec.id)]).unlink()
                        self.env['document.file.permission'].sudo().search(
                            [('type', 'like', 'write'), ('file_id', 'in', tuple(e[0] for e in all_file_ids))]).unlink()
                    # list all new read users
                    # list all user group can read only
                    self.env.cr.execute(
                        """select res_group_id from document_general_part_read_group_rel where general_part_id = %s""",
                        (rec.id,))
                    all_group_ids = self.env.cr.fetchall()
                    if all_group_ids is not None and len(all_group_ids) > 0:
                        all_read_user_ids = self.get_user_id_from_group_list(list(e[0] for e in all_group_ids))
                        self.env.cr.execute(
                            """select res_user_id from document_permission where type like 'read' and model like 'general' and res_id = %s""",
                            (rec.id,))
                        current_read_user_ids = self.env.cr.fetchall()
                        # delete all document permission not in read groups and write users
                        self.env['document.permission'].sudo().search(
                            [('model', 'like', 'general'), ('type', 'like', 'read'), ('res_id', '=', rec.id),
                             ('res_user_id', 'not in', list(str(a[0]) for a in all_write_user_ids))
                                , ('res_user_id', 'not in', list(str(a) for a in all_read_user_ids))]).unlink()

                        # delete all document file permission not in read groups and write users
                        self.env['document.file.permission'].sudo().search(
                            [('type', 'like', 'read'), ('file_id', 'in', tuple(e[0] for e in all_file_ids)),
                             ('res_user_id', 'not in', list(str(a[0]) for a in all_write_user_ids))
                                , ('res_user_id', 'not in', list(str(a) for a in all_read_user_ids))]).unlink()

                        # delete all document permission read but already write
                        self.env['document.permission'].sudo().search(
                            [('model', 'like', 'general'), ('type', 'like', 'read'), ('res_id', '=', rec.id),
                             ('res_user_id', 'in', list(str(a[0]) for a in all_write_user_ids))]).unlink()

                        # delete all document file permission read but already write
                        self.env['document.file.permission'].sudo().search(
                            [('type', 'like', 'read'), ('file_id', '=', tuple(e[0] for e in all_file_ids)),
                             ('res_user_id', 'in', list(str(a[0]) for a in all_write_user_ids))]).unlink()

                        new_document_read_permission = []
                        new_document_file_read_permission = []
                        for e in all_read_user_ids:
                            if e not in list(a[0] for a in all_write_user_ids) and e not in list(
                                    b[0] for b in current_read_user_ids):
                                new_document_read_permission.append({
                                    'type': 'read',
                                    'model': 'general',
                                    'res_id': rec.id,
                                    'res_user_id': e,
                                })
                                for file_id_item in all_file_ids:
                                    new_document_file_read_permission.append({
                                        'type': 'read',
                                        'file_id': file_id_item[0],
                                        'res_user_id': e,
                                    })

                        self.env['document.permission'].sudo().create(new_document_read_permission)
                        self.env['document.file.permission'].sudo().create(new_document_file_read_permission)
                    else:
                        self.env['document.permission'].sudo().search(
                            [('model', 'like', 'general'), ('type', 'like', 'read'), ('res_id', '=', rec.id)]).unlink()
                        self.env['document.file.permission'].sudo().search(
                            [('type', 'like', 'read'), ('file_id', 'in', tuple(e[0] for e in all_file_ids))]).unlink()
                    # start update document file permission

                return folder
            else:
                raise UserError(_("You don't have permission to do this action"))

    def unlink(self):
        google_drive_helper = GoogleDriveHelper()
        for e in self:
            try:
                google_drive_helper.deleteFile(file_id=e['file_id'])
            except Exception as ex:
                a = 0
        for e in self:
            self.env['document.general.file'].sudo().search(
                [('res_id', '=', e.id)]).unlink()
        for e in self:
            self.env['document.permission'].sudo().search(
                [('model', 'like', 'general'), ('res_id', '=', e.id), ('type', 'like', 'write')]).unlink()
        return super(DocumentGeneralPart, self).unlink()

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
