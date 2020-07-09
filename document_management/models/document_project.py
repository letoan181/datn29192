from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..utils.google_drive_helper import GoogleDriveHelper


class ProjectDocument(models.Model):
    _inherit = 'project.project'

    document_project_name = fields.Char(string="Folder Name")
    google_drive_url = fields.Char(readonly=True)
    file_id = fields.Char(readonly=True)
    document_project_part = fields.One2many('document.project.part', 'document_project_id',
                                            string='Document Part')
    document_tab_visible = fields.Boolean(compute='_document_tab_visible')
    document_count = fields.Integer(compute='_document_count')
    tag_ids = fields.Many2many('document.tags', string='Tags')

    def _document_tab_visible(self):
        self.ensure_one()
        self.document_tab_visible = False
        if self.user_has_groups('base.group_system') or self.env['project.project'].sudo().browse(
                self.id).user_id.id == self._uid:
            self.document_tab_visible = True

    def _document_count(self):
        # compute amount document
        if self.user_has_groups('base.group_system'):
            domain = self.env['document.project.part'].sudo().search([('document_project_id', '=', self.id)])
            self.document_count = len(domain)
        else:
            if len(self.document_project_part) > 0:
                part_ids = [part.id for part in self.document_project_part]
                self.env.cr.execute(
                    """select res_id from document_permission where res_user_id=%s and model like 'project' and res_id in %s group by res_id""",
                    (self._uid, tuple(part_ids)))
                can_read_documents = self.env.cr.fetchall()
                self.document_count = len(can_read_documents)
            else:
                self.document_count = 0

    def action_document_project_part_list(self):
        if self.user_has_groups('base.group_system'):
            domain = [('document_project_id', '=', self.id)]
        else:
            domain = [('document_project_id', '=', self.id)]
            self.env.cr.execute(
                """select res_id from document_permission where res_user_id=%s and model like 'project' group by res_id""",
                (self._uid,))
            can_read_documents = self.env.cr.fetchall()
            domain.append(('id', 'in', [val[0] for val in can_read_documents]))
        action = {"name": self.name, "type": "ir.actions.act_window", "view_mode": "kanban,form",
                  "view_type": "form",
                  "res_model": "document.project.part",
                  "context": {"create": True, 'default_document_project_id': self.id}, 'domain': domain}
        return action

    def action_document_project_list(self):
        # Dung de khoi tao view voi domain chay bang python
        if self.user_has_groups('base.group_system'):
            domain = [('document_project_name', '!=', False)]
        else:
            self.env.cr.execute(
                """select document_project_id from document_project_part where id in  (select res_id from document_permission where res_user_id=%s and model like 'project' group by res_user_id,res_id)""",
                (self._uid,))
            can_read_documents = self.env.cr.fetchall()
            domain = [('id', 'in', [val[0] for val in can_read_documents])]
        views = [(self.env.ref('document_management.view_document_project_kanban').id, 'kanban'),
                 (self.env.ref('document_management.view_document_project_folder').id, 'folder'),
                 ]

        action = {"name": "Project Documents", "type": "ir.actions.act_window", "view_mode": "kanban,form,folder",
                  "view_type": "form", "context": {"create": False},
                  "res_model": "project.project", 'domain': domain, 'view_id': False,
                  'views': views}
        return action

    def write(self, values):
        if values.get('document_project_name'):
            if self.user_has_groups('base.group_system') or self.env['project.project'].sudo().browse(
                    self.id).user_id.id == self._uid:
                self.env.cr.execute("""select document_project_name from project_project where id=%s""",
                                    (self.id,))
                document_name = self.env.cr.fetchone()
                if document_name[0] is not None:
                    if values.get('document_project_name') == False:
                        googleDriveHelper = GoogleDriveHelper()
                        googleDriveHelper.deleteFile(self['file_id'])
                        values['google_drive_url'] = False
                        values['file_id'] = False
                        self.env['document.project.part'].sudo().search(
                            [('document_project_id', '=', self.id)]).unlink()
                    else:
                        google_drive_helper = GoogleDriveHelper()
                        google_drive_helper.update_file_name(file_id=self['file_id'],
                                                             new_name=values.get('document_project_name'))
                else:
                    if values.get('document_project_name'):
                        Config = self.env['ir.config_parameter'].sudo()
                        get_google_account = self.env['document.google.account'].sudo().search([('is_use', '=', True)],
                                                                                               limit=1)
                        if get_google_account and get_google_account.project_folder_base:
                            parent_file_url = get_google_account.project_folder_base
                        else:
                            parent_file_url = Config.get_param('document_management.general_folder_base')
                        # parent_file_url = Config.get_param('document_management.project_folder_base')
                        if parent_file_url is not False and len(parent_file_url) > 0:
                            parent_file_url_arr = parent_file_url.split('/')
                            parent_id = parent_file_url_arr[len(parent_file_url_arr) - 1]
                            googleDriveHelper = GoogleDriveHelper()
                            google_drive_new_folder = googleDriveHelper.create_sub_file(parent_id,
                                                                                        values.get(
                                                                                            'document_project_name'))
                            # values['google_drive_url'] = 'https://drive.google.com/drive/folders/' + \
                            #                              google_drive_new_folder[
                            #                                  'id']
                            # values['file_id'] = google_drive_new_folder['id']
                            base_url = 'https://drive.google.com/drive/folders/' + \
                                       google_drive_new_folder[
                                           'id']
                            file_id = google_drive_new_folder['id']
                            # force update database
                            self.env.cr.execute(
                                """update project_project set google_drive_url = %s , file_id = %s WHERE id=%s""",
                                (base_url, file_id, self.id))
                            self.env.cr.commit()
                        else:
                            raise UserError(_("Please config Project Folder base in General Setting"))
        return super(ProjectDocument, self).write(values)

    def get_project_document_action_document_part(self, context=None):
        domain = []
        if not context:
            context = self._context
        if context:
            if self.user_has_groups('base.group_system'):
                domain = [('document_project_id', '=', context['active_id'])]
            else:
                domain = [('document_project_id', '=', context['active_id'])]
                self.env.cr.execute(
                    """select res_id from document_permission where res_user_id=%s and model like 'project' group by res_id""",
                    (self._uid,))
                can_read_documents = self.env.cr.fetchall()
                domain.append(('id', 'in', [val[0] for val in can_read_documents]))
        # views = [(self.env.ref('document_management.view_document_project_part_file_kanban').id, 'kanban'),
        #          (self.env.ref('document_management.project_document_action_document_part_form2').id, 'form')]
        action = {"name": self.name, "type": "ir.actions.act_window", "view_mode": "kanban,form",
                  "view_type": "form",
                  "res_model": "document.project.part",
                  "context": {"create": True, 'default_document_project_id': self.id}, 'domain': domain}
        return action


class DocumentProjectPart(models.Model):
    _name = "document.project.part"

    name = fields.Char(required=True)
    document_project_id = fields.Many2one('project.project', inverse_name='id', string='Document',
                                          ondelete='cascade')
    google_drive_url = fields.Char(readonly=True)
    file_id = fields.Char(readonly=True)
    write_users = fields.Many2many('res.users', 'document_project_part_write_user_rel', 'project_part_id',
                                   'res_user_id',
                                   string='Write Users', required=True)
    read_users = fields.Many2many('res.users', 'document_project_part_read_user_rel', 'project_part_id',
                                  'res_user_id',
                                  string='Read Users', required=True)
    current_permission_can_update = fields.Boolean(compute='_compute_current_permission_can_update', default=False,
                                                   store=False)
    tag_ids = fields.Many2many('document.tags', string='Tags')

    def _compute_current_permission_can_update(self):
        for e in self:
            e.current_permission_can_update = False
            if self.user_has_groups('base.group_system'):
                e['current_permission_can_update'] = True
            elif e.create_uid.id == self._uid:
                e['current_permission_can_update'] = True
            else:
                current_project_id = self._context.get('default_document_project_id')
                if current_project_id:
                    if self.env['project.project'].browse(current_project_id).user_id.id == self._uid:
                        e['current_permission_can_update'] = True

    def get_project_document_action_document_part_file(self, context=None):
        # domain = [('document_file_id', '=', context['active_id'])]
        # self.env.cr.execute(
        #     """select file_id from document_file""")
        # documents_file = self.env.cr.fetchall()
        # domain.append(('id', 'in', [val[0] for val in documents_file]))
        domain = []
        can_create = False
        if not context:
            context = self._context
        if context:
            if self.user_has_groups('base.group_system'):
                can_create = True
            self.env.cr.execute(
                """select res_user_id from document_project_part_write_user_rel where res_user_id=%s and project_part_id=%s """,
                (self._uid, self.ids[0],))
            current_user_permission = self.env.cr.fetchone()
            if current_user_permission is not None and len(current_user_permission) > 0:
                can_create = True
            domain = [('0', '=', '1')]
            if can_create:
                domain = [('res_id', '=', context['active_id'])]
            else:
                self.env.cr.execute(
                    """select id from document_permission where res_user_id=%s and model='project' """,
                    (self._uid,))
                found_ids = self.env.cr.fetchone()
                if found_ids and len(found_ids) > 0:
                    domain = [('res_id', '=', context['active_id'])]
        action = {"name": self.name, "type": "ir.actions.act_window", "view_mode": "kanban,form,tree",
                  "view_type": "form",
                  "res_model": "document.project.file",
                  "context": {"create": can_create, 'default_res_id': self.id},
                  'domain': domain}
        return action

    def call_back_parent_root(self):
        action = self.document_project_id.action_document_project_list()
        action['target'] = 'main'
        return action

    def call_back_parent_part(self, context=None):
        if context and self.document_project_id:
            action = self.document_project_id.get_project_document_action_document_part(context)
            action['target'] = 'main'
            return action

    @api.model
    def create(self, values):
        document_project_id = values.get('document_project_id')
        if document_project_id is None:
            document_project_id = self._context.get('default_document_project_id')
        # if document_project_id is None:
        #     document_project_id = self._context.get('active_id')
        # check permission
        can_create = False
        if self.user_has_groups('base.group_system'):
            can_create = True
        if self.env['project.project'].browse(document_project_id).user_id.id == self._uid:
            can_create = True
        if can_create:
            google_drive_helper = GoogleDriveHelper()
            new_folder = google_drive_helper.create_sub_file(self.env['project.project'].sudo().browse(
                document_project_id).file_id, values.get('name'))
            values['google_drive_url'] = 'https://drive.google.com/drive/folders/' + new_folder['id']
            values['file_id'] = new_folder['id']
            folder = super(DocumentProjectPart, self).create(values)
            if values.get('write_users'):
                for e in values.get('write_users')[0][2]:
                    self.env['document.permission'].sudo().create({
                        'type': 'write',
                        'model': 'project',
                        'res_id': folder.id,
                        'res_user_id': e,
                    })
            if values.get('read_users'):
                for e in values.get('read_users')[0][2]:
                    if values.get('write_users'):
                        if e not in values.get('write_users')[0][2]:
                            self.env['document.permission'].sudo().create({
                                'type': 'read',
                                'model': 'project',
                                'res_id': folder.id,
                                'res_user_id': e,
                            })
                    else:
                        self.env['document.permission'].sudo().create({
                            'type': 'read',
                            'model': 'project',
                            'res_id': folder.id,
                            'res_user_id': e,
                        })
            return folder
        else:
            raise UserError(_("You don't have permission to do this action."))

    def write(self, values):
        folder = super(DocumentProjectPart, self).write(values)
        self.env.cr.execute(
            """select res_user_id from document_project_part_write_user_rel where project_part_id = %s""",
            (self.id,))
        all_write_user_ids = self.env.cr.fetchall()
        # liet ke tat ca ca user co quyen write
        if values.get('write_users') or values.get('read_users'):
            self.env['document.permission'].sudo().search(
                [('model', 'like', 'project'), ('type', 'like', 'write'), ('res_id', '=', self.id),
                 ('res_user_id', 'not in', tuple(e[0] for e in all_write_user_ids))]).unlink()
            # xoa tat ca user ma khong con quyen write

            if all_write_user_ids is not None and len(all_write_user_ids) > 0:
                # find current write user ids
                self.env.cr.execute(
                    """select res_user_id from document_permission where model like 'project' and type like 'write' and res_user_id in %s and res_id = %s """,
                    (tuple(e[0] for e in all_write_user_ids), self.id,))
                current_write_user_ids = self.env.cr.fetchall()
                # tim tat ca cac user vua duoc them quyen write
                new_write_user_ids = []
                for e in all_write_user_ids:
                    if e[0] not in list(a[0] for a in current_write_user_ids):
                        new_write_user_ids.append(e[0])
                for e in new_write_user_ids:
                    self.env['document.permission'].sudo().create({
                        'type': 'write',
                        'model': 'project',
                        'res_id': self.id,
                        'res_user_id': e,
                    })
                self.env.cr.execute(
                    """delete from document_permission where model like 'project' and type like 'read' and res_user_id in %s and res_id = %s """,
                    (tuple(e[0] for e in all_write_user_ids), self.id,))
                # xoa tat ca cac user ma co quyen read truoc do
            else:
                self.env['document.permission'].sudo().search(
                    [('model', 'like', 'project'), ('type', 'like', 'write'), ('res_id', '=', self.id)]).unlink()

            # read permission

            # list all users have permission read
            self.env.cr.execute(
                """select res_user_id from document_project_part_read_user_rel where project_part_id = %s""",
                (self.id,))
            all_read_users_ids = self.env.cr.fetchall()

            if all_read_users_ids is not None and len(all_read_users_ids) > 0:
                self.env.cr.execute(
                    """select res_user_id from document_permission where model like 'project' and type like 'read' and res_user_id in %s and res_id = %s """,
                    (tuple(e[0] for e in all_read_users_ids), self.id,))
                current_read_user_ids = self.env.cr.fetchall()
                # delete user have not permission read:
                self.env['document.permission'].sudo().search(
                    [('model', 'like', 'project'), ('type', 'like', 'read'), ('res_id', '=', self.id),
                     ('res_user_id', 'not in', list(str(a[0]) for a in all_write_user_ids)),
                     ('res_user_id', 'not in', list(str(a[0]) for a in all_read_users_ids))]).unlink()
                self.env['document.permission'].sudo().search(
                    [('model', 'like', 'project'), ('type', 'like', 'read'), ('res_id', '=', self.id),
                     ('res_user_id', 'in', list(str(a[0]) for a in all_write_user_ids))]).unlink()

                for e in all_read_users_ids:
                    if e[0] not in list(a[0] for a in all_write_user_ids) and e[0] not in list(
                            b[0] for b in current_read_user_ids):
                        self.env['document.permission'].sudo().create({
                            'type': 'read',
                            'model': 'project',
                            'res_id': self.id,
                            'res_user_id': e[0],
                        })
            else:
                self.env['document.permission'].sudo().search(
                    [('model', 'like', 'project'), ('type', 'like', 'read'), ('res_id', '=', self.id)]).unlink()

        return folder

    def unlink(self):
        google_drive_helper = GoogleDriveHelper()
        for rec in self:
            try:
                google_drive_helper.deleteFile(rec.file_id)
            except Exception as e:
                a = 0
            self.env['document.permission'].sudo().search(
                [('model', 'like', 'project'), ('res_id', '=', rec.id)]).unlink()
            self.env.cr.execute("""select file_id from document_project_file where res_id = %s""", (rec.id,))
            file_ids = self.env.cr.fetchall()
            if file_ids is not None and len(file_ids) > 0:
                self.env['document.file.permission'].sudo().search(
                    [('file_id', 'in', tuple(e[0] for e in file_ids))]).unlink()
                self.env['document.project.file'].sudo().search(
                    [('res_id', '=', rec.id)]).unlink()
        return super(DocumentProjectPart, self).unlink()


class ProjectTaskDocument(models.Model):
    _inherit = 'project.task'

    document_count = fields.Integer(compute='_document_count')

    def _document_count(self):
        self.ensure_one()
        # compute amount document
        if self.user_has_groups('base.group_system'):
            domain = self.env['document.project.part'].sudo().search([('document_project_id', '=', self.project_id.id)])
            self.document_count = len(domain)
        else:
            if len(self.project_id.document_project_part) > 0:
                part_ids = [part.id for part in self.project_id.document_project_part]
                self.env.cr.execute(
                    """select res_id from document_permission where res_user_id=%s and model like 'project' and res_id in %s group by res_id""",
                    (self._uid, tuple(part_ids)))
                can_read_documents = self.env.cr.fetchall()
                self.document_count = len(can_read_documents)
            else:
                self.document_count = 0

    def action_document_project_part_list(self):
        if self.user_has_groups('base.group_system'):
            domain = [('document_project_id', '=', self.project_id.id)]
        else:
            domain = [('document_project_id', '=', self.project_id.id)]
            self.env.cr.execute(
                """select res_id from document_permission where res_user_id=%s and model like 'project' group by res_id""",
                (self._uid,))
            can_read_documents = self.env.cr.fetchall()
            domain.append(('id', 'in', [val[0] for val in can_read_documents]))
        action = {"name": self.name, "type": "ir.actions.act_window", "view_mode": "kanban,form",
                  "view_type": "form",
                  "res_model": "document.project.part",
                  "context": {"create": True, 'default_document_project_id': self.project_id.id}, 'domain': domain}
        return action
