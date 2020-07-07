import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..utils.google_drive_helper import GoogleDriveHelper


class DocumentCrmFile(models.Model):
    _name = "document.crm.file"
    _inherit = ['mail.thread', 'mail.activity.mixin', ]
    _description = "Manage document files"

    @api.model
    def _compute_is_favorite(self):
        for document in self:
            document.is_favorite = self.env.user in document.favorite_user_ids

    def _inverse_is_favorite(self):
        favorite_document = not_fav_document = self.env['document.crm.file'].sudo()
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
    # res_model = fields.Selection([('general', 'General'), ('project', 'Project'), ('crm', 'crm')],
    #                              required=True, default='general')
    res_id = fields.Integer(string="Related Model ID", required=True)
    # document_file_id = fields.Many2one('document.crm.part', inverse_name='name', string="Document",
    #                                       ondelete='cascade', required=True)
    google_drive_url = fields.Char(string="File URL", readonly=True)
    file_id = fields.Char(string="File ID", readonly=True)
    color = fields.Integer(string='Color Index')
    write_users = fields.Many2many('res.users', 'document_crm_file_write_user_rel', 'res_file_id',
                                   'res_user_id',
                                   string='Write Users', default=lambda self: self.env.user)
    read_users = fields.Many2many('res.users', 'document_crm_file_read_user_rel', 'res_file_id',
                                  'res_user_id',
                                  string='Read Users')
    favorite_user_ids = fields.Many2many(
        'res.users', 'document_crm_file_favorite_user_rel', 'document_id', 'user_id',
        string='Favorite Members',
        default=_get_default_favorite_user_ids)
    is_favorite = fields.Boolean(
        string='Show on dashboard',
        compute='_compute_is_favorite', inverse='_inverse_is_favorite',
        help="Favorite teams to display them in the dashboard and access them easily.")

    # can edit
    current_permission_can_update = fields.Boolean(compute='_compute_current_permission_can_update', default=False,
                                                   store=False)
    # public permission
    public = fields.Boolean('Public', default=False, track_visibility='onchange')
    public_type = fields.Selection([('read', 'Read'), ('write', 'Write'), ('comment', 'Comment')], default='read',
                                   track_visibility='onchange')

    # user can update
    users_update = fields.Many2many('res.users', string="User Can Update")

    @api.onchange('users_update')
    def check_user_can_see_file(self):
        for rec in self:
            if len(rec.users_update) > 0:
                warning = []
                #users_can_see = [res.res_user_id for res in self.env['document.permission'].sudo().search([('res_id', '=', rec.res_id), ('model', '=', 'crm')])]
                users_can_see = []
                if len(rec.write_users) > 0:
                    for a in rec.write_users:
                        users_can_see.append(a.id)
                if len(rec.read_users) > 0:
                    for a in rec.read_users:
                        if a.id not in users_can_see:
                            users_can_see.append(a.id)
                for user in rec.users_update:
                    if user.id not in users_can_see:
                        warning.append(user.name)
                if len(warning) > 0:
                    message = ','.join(i for i in warning)
                    message += ':Can Not Access Current File'
                    warning_mess = {
                        'title': _('Warning'),
                        'message': message
                    }
                    return {'warning': warning_mess}

    def _compute_current_permission_can_update(self):
        for e in self:
            e.current_permission_can_update = False
            if self.user_has_groups('base.group_system'):
                e['current_permission_can_update'] = True
            elif self._uid in [u.id for u in e.users_update]:
                e['current_permission_can_update'] = True
            else:
                if e.create_uid.id == self._uid:
                    e['current_permission_can_update'] = True

    @api.model
    def action_document_crm_file_list(self):
        # Dung de khoi tao view voi domain chay bang python
        domain = []
        if self.user_has_groups('base.group_system'):
            domain = []
        else:
            self.env.cr.execute(
                """select id
from document_crm_file
where id in (select res_file_id from document_crm_file_write_user_rel where res_user_id = %s)
   or id in (select res_file_id from document_crm_file_read_user_rel where res_user_id = %s)""",
                (self._uid, self._uid,))
            can_read_documents = self.env.cr.fetchall()
            if can_read_documents is not None and len(can_read_documents) > 0:
                domain = [('id', 'in', [val[0] for val in can_read_documents])]
            else:
                domain = [('id', '=', 0)]
        views = [(
            self.env.ref('document_management.general_document_action_document_crm_part_file_kanban').id,
            'kanban'),
            (self.env.ref('document_management.view_document_crm_file_form').id, 'form'),
            (self.env.ref('document_management.view_document_crm_file_tree').id, 'list')]

        action = {"name": "CRM Documents", "type": "ir.actions.act_window", "view_mode": "kanban,form,list",
                  "view_type": "form", "context": {"create": False},
                  "res_model": "document.crm.file", 'domain': domain, 'view_id': False,
                  'views': views}
        return action

    def call_back_parent_root(self):
        res = self.env['document.crm.part'].sudo().browse(self.res_id)
        context = {'active_id': res.document_crm_id.id}
        action = res.document_crm_id.get_crm_document_action_document_part(context)
        action['target'] = 'main'
        return action

    def call_back_parent_part(self, context=None):
        res = self.env['document.crm.part'].sudo().browse(self.res_id)
        action = res.get_crm_document_action_document_part_file(context)
        action['target'] = 'main'
        return action

    @api.model
    def create(self, vals):
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

        if vals.get('is_copy') == True:
            google_drive_new_file = GoogleDriveHelper().create_copy(source_file_id=vals.get('file_id'),
                                                                    parent_file_id=vals.get('parent_file_id'),
                                                                    file_name=file_name)
        else:
            # find parent file id
            parent_file_id = self.env['document.crm.part'].sudo().search([('id', '=', vals.get('res_id'))],
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
                google_drive_new_file = google_drive_helper.create_sub_file(parent_id=parent_file_id, folder_name=file_name)

        vals['file_id'] = google_drive_new_file['id']

        if file_type == 'doc':
            vals['google_drive_url'] = 'https://docs.google.com/' + 'document' + '/d/' + google_drive_new_file['id']
        elif file_type == 'excel':
            vals['google_drive_url'] = 'https://docs.google.com/' + 'spreadsheets' + '/d/' + google_drive_new_file[
                'id']
        elif file_type == 'power_point':
            vals['google_drive_url'] = 'https://docs.google.com/' + 'presentation' + '/d/' + google_drive_new_file[
                'id']
        elif file_type == 'folder':
            vals['google_drive_url'] = 'https://drive.google.com/drive/folders/' + google_drive_new_file[
                'id']
        # update write user
        # file=super(DocumentCrmFile,self).create(vals)
        write_user_ids = []
        if vals.get('write_users'):
            write_user_ids = vals.get('write_users')
            for e in write_user_ids[0][2]:
                self.env['document.file.permission'].sudo().create({
                    'file_id': google_drive_new_file['id'],
                    'res_user_id': e,
                    'type': 'write',
                })
        if vals.get('read_users'):
            read_user_ids = vals.get('read_users')
            for a in read_user_ids[0][2]:
                if a not in write_user_ids[0][2]:
                    self.env['document.file.permission'].sudo().create({
                        'file_id': google_drive_new_file['id'],
                        'res_user_id': a,
                        'type': 'read',
                    })
        if vals.get('public'):
            public_type = vals.get('public_type')
            self.env['document.file.public.permission'].sudo().create({
                'file_id': google_drive_new_file['id'],
                'model': 'crm',
                'type': public_type,
            })
        if vals.get('is_copy') == True:
            del vals['is_copy']
            del vals['parent_file_id']
        return super(DocumentCrmFile, self).create(vals)

    def write(self, values):
        if values.get('is_favorite'):
            values.pop('is_favorite')
            self._fields['is_favorite'].determine_inverse(self)
        # update on google drive
        current_file = self.env['document.crm.file'].sudo().browse(self.id)
        # Current users
        old_write_users = 'Empty'
        old_read_users = 'Empty'
        if len(self.write_users) > 0:
            old_write_users = ','.join(str(e) for e in [user.name for user in self.write_users])
        if len(self.read_users) > 0:
            old_read_users = ','.join(str(e) for e in [user.name for user in self.read_users])
        folder = super(DocumentCrmFile, self).write(values)
        if values.get('name'):
            google_drive_helper = GoogleDriveHelper()
            google_drive_helper.update_file_name(file_id=current_file.file_id, new_name=values.get('name'))
        # update write user
        if values.get('write_users') or values.get('read_users'):
            # find all write users
            self.env.cr.execute(
                """select res_user_id from document_crm_file_write_user_rel where res_file_id = %s""",
                (self.id,))
            all_write_user_ids = self.env.cr.fetchall()
            if all_write_user_ids is not None and len(all_write_user_ids) > 0:
                # delete all write permission if its user dont have permission anymore
                self.env['document.file.permission'].sudo().search(
                    [('type', 'like', 'write'), ('file_id', '=', current_file.file_id),
                     ('res_user_id', 'not in', tuple(e[0] for e in all_write_user_ids))]).unlink()
                # find current write user ids
                self.env.cr.execute(
                    """select res_user_id from document_file_permission where type like 'write' and file_id like %s""",
                    (current_file.file_id,))
                current_write_user_ids = self.env.cr.fetchall()
                new_write_user_ids = []
                for e in all_write_user_ids:
                    if e[0] not in list(a[0] for a in current_write_user_ids):
                        new_write_user_ids.append(e[0])
                for e in new_write_user_ids:
                    self.env['document.file.permission'].sudo().create({
                        'type': 'write',
                        'file_id': current_file.file_id,
                        'res_user_id': e,
                    })
                # delete all read permission if its user already has write permission
                self.env.cr.execute(
                    """delete from document_file_permission where type like 'read' and res_user_id in %s and file_id like %s""",
                    (tuple(e[0] for e in all_write_user_ids), current_file.file_id,))
            else:
                self.env['document.file.permission'].sudo().search(
                    [('type', 'like', 'write'), ('file_id', '=', current_file.file_id)]).unlink()
            # update read users
            # list all new read users
            # list all user group can read only
            self.env.cr.execute(
                """select res_user_id from document_crm_file_read_user_rel where res_file_id = %s""",
                (self.id,))
            all_read_user_ids = self.env.cr.fetchall()
            if all_read_user_ids is not None and len(all_read_user_ids) > 0:
                # get current read users
                self.env.cr.execute(
                    """select res_user_id from document_file_permission where type like 'read' and file_id like %s""",
                    (current_file.file_id,))
                current_read_user_ids = self.env.cr.fetchall()
                # delete all document permission not in read groups and write users
                self.env['document.file.permission'].sudo().search(
                    [('type', 'like', 'read'), ('file_id', '=', current_file.file_id),
                     ('res_user_id', 'not in', list(str(a[0]) for a in all_write_user_ids))
                        , ('res_user_id', 'not in', list(str(a[0]) for a in all_read_user_ids))]).unlink()
                self.env['document.file.permission'].sudo().search(
                    [('type', 'like', 'read'), ('file_id', '=', current_file.file_id),
                     ('res_user_id', 'in', list(str(a[0]) for a in all_write_user_ids))]).unlink()
                for e in all_read_user_ids:
                    if e[0] not in list(a[0] for a in all_write_user_ids) and e[0] not in list(
                            b[0] for b in current_read_user_ids):
                        self.env['document.file.permission'].sudo().create({
                            'type': 'read',
                            'file_id': current_file.file_id,
                            'res_user_id': e[0],
                        })
            else:
                self.env['document.file.permission'].sudo().search(
                    [('type', 'like', 'read'), ('file_id', '=', current_file.file_id)]).unlink()
            #  Tracking write,read users
            if values.get('write_users'):
                if len(self.write_users) > 0:
                    new_write_users = ','.join(str(e) for e in [user.name for user in self.write_users])
                else:
                    new_write_users = 'Empty'
                body = "<p>Change Write Users: </p><p>" + 'Old Users: ' + (
                    old_write_users) + "</p><p>" + 'New Users: ' + (
                           new_write_users) + '</p>'
                self.message_post(body=body)
            if values.get('read_users'):
                if len(self.read_users) > 0:
                    new_read_users = ','.join(str(e) for e in [user.name for user in self.read_users])
                else:
                    new_read_users = "Empty"
                body = "<p>Change Read Users: </p><p>" + 'Old Users: ' + (
                    old_read_users) + "</p><p>" + 'New Users: ' + (
                           new_read_users) + '</p>'
                self.message_post(body=body)
        if 'public' in values:
            if self.public:
                public_type = self.public_type
                self.env['document.file.public.permission'].sudo().create({
                    'file_id': self.file_id,
                    'model': 'crm',
                    'type': public_type,
                })
            if not self.public:
                public_permissions = self.env['document.file.public.permission'].sudo().search(
                    [('model', '=', 'crm'), ('file_id', '=', self.file_id)])
                if public_permissions is not None and len(public_permissions) > 0:
                    for record in public_permissions:
                        record.unlink()
        if 'public' not in values and values.get('public_type'):
            public_permissions = self.env['document.file.public.permission'].sudo().search(
                [('model', '=', 'crm'), ('file_id', '=', self.file_id)])
            if public_permissions is not None and len(public_permissions) > 0:
                for record in public_permissions:
                    record.unlink()
            public_type = self.public_type
            self.env['document.file.public.permission'].sudo().create({
                'file_id': self.file_id,
                'model': 'crm',
                'type': public_type,
            })
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
            if e.public:
                self.env['document.file.public.permission'].sudo().search(
                    [('file_id', '=', e.file_id), ('model', '=', 'crm')]).unlink()
        return super(DocumentCrmFile, self).unlink()

    def action_fetch_file_permission(self):
        for rec in self:
            file_errors = self.env['document.file.permission.error'].sudo().search([('file_id', '=', rec.file_id)])
            if len(file_errors) > 0:
                raise UserError(_('Can not update permission right now.Try again in few seconds.'))
            try:
                self.env.cr.execute("""select document_file_permission.id as id, file_id, google_email
                from document_file_permission left join res_users on res_users.id = document_file_permission.res_user_id
                where document_file_permission.google_drive_permission_id is null and document_file_permission.status is null and type like 'write' and res_users.active is true and res_users.google_email is not null and file_id like %s """,
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
            # # update public permission
            # try:
            #     permissions_need_sync = self.env['document.file.public.permission'].sudo().search(
            #         [('model', '=', 'crm'),('google_drive_permission_id','=', False)])
            #     if permissions_need_sync:
            #         google_drive_helper = GoogleDriveHelper()
            #         new_permission = None
            #         for e in permissions_need_sync:
            #             try:
            #                 if e.type == 'read':
            #                     new_permission = google_drive_helper.create__public_file_read_permission(e.file_id)
            #                 if e.type == 'write':
            #                     new_permission = google_drive_helper.create_public_file_write_permission(e.file_id)
            #                 # update gg drive ID
            #                 if new_permission is not None:
            #                     e.google_drive_permission_id = new_permission
            #             except Exception as e:
            #                 """print(e)"""
            #     permissions_need_delete = self.env['document.file.public.permission'].sudo().search(
            #         [('model', '=', 'crm'), ('error_permission_id', '!=', False)])
            #     if permissions_need_delete:
            #         for p in permissions_need_delete:
            #             p.unlink()
            # except Exception as ex:
            #     e = 0
