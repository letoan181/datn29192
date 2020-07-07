from odoo import models, fields, api


class MassActionProject(models.TransientModel):
    _name = "mass.update.project.file"

    def _default_file(self):
        if self._context.get('active_ids'):
            return self.env['document.project.file'].browse(self._context.get('active_ids'))

    file = fields.Many2many('document.project.file', string="Record", required=True, default=_default_file)
    write_users = fields.Many2many('res.users', 'document_project_file_mass_write_user_rel', 'mass_id',
                                   'res_user_id',
                                   string='Write Users', )
    read_users = fields.Many2many('res.users', 'document_project_file_mass_read_user_rel', 'mass_id',
                                  'res_user_id',
                                  string='Read Users')
    users = fields.Many2many('res.users', 'document_project_file_mass_release_user_rel', 'mass_id',
                             'res_user_id',
                             string='Select Users')
    context = fields.Char(compute='_get_context')
    invisible = fields.Boolean(compute='_get_context')
    # external user
    external_name = fields.Char(string='User Name')
    external_email = fields.Char(string="Google Email")
    external_type = fields.Selection([('read', 'Read'), ('write', 'Write')], default='read')

    @api.depends('file')
    def _get_context(self):
        if len(self.file) > 0:
            self.invisible = False
            if self._context['update'] == True:
                self.context = 'update'
            if self._context['drop'] == True:
                self.context = 'drop'
        else:
            self.invisible = True

    def update_can_edit_user(self):
        message = 'Select Files/Users To Update!'
        file_success = []
        file_fail = []
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        if len(rec.users) > 0:
                            for user in rec.users:
                                if user not in file.users_update:
                                    file.write({
                                        'users_update': [(4, user.id)]
                                    })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def update_external_users(self):
        message = 'Select File To Update!'
        file_success = []
        file_fail = []
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        if rec.external_name and rec.external_email and rec.external_type:
                            exist_email = [a.user_email for a in file.external_users]
                            if rec.external_email not in exist_email:
                                file.write({
                                    'external_users': [[0, 0, {'name': rec.external_name, 'user_email': rec.external_email, 'type': rec.external_type}]]
                                })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def update_users(self):
        file_success = []
        file_fail = []
        message = 'Select Files To Update!'
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        if rec.write_users and len(rec.write_users) > 0:
                            curent_write_users = [a.id for a in file.write_users if len(file.write_users) > 0]
                            for w_user in rec.write_users:
                                if w_user.id not in curent_write_users:
                                    file.write({
                                        'write_users': [(4, w_user.id)]
                                    })
                        if rec.read_users and len(rec.read_users) > 0:
                            curent_read_users = [u.id for u in file.read_users if len(file.read_users) > 0]
                            for r_user in rec.read_users:
                                if r_user.id not in curent_read_users:
                                    file.write({
                                        'read_users': [(4, r_user.id)]
                                    })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def delete_user(self):
        file_success = []
        file_fail = []
        message = 'Select Files To Update!'
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        list_w_uid = [u.id for u in file.write_users if len(file.write_users) > 0]
                        list_r_uid = [u.id for u in file.read_users if len(file.read_users) > 0]
                        if len(rec.users) > 0:
                            for user in rec.users:
                                if user.id in list_w_uid:
                                    file.write({
                                        'write_users': [(3, user.id)]
                                        # can use this instead [[6, False, [2]]]
                                    })
                                if user.id in list_r_uid:
                                    file.write({
                                        'read_users': [(3, user.id)]
                                    })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def get_permission(self, file=None):
        can_update = False
        for e in self:
            if self.user_has_groups('base.group_system'):
                can_update = True
            elif self._uid in [u.id for u in file.users_update]:
                can_update = True
            else:
                if file.create_uid.id == self._uid:
                    can_update = True
        return can_update


class MassActionQuotation(models.TransientModel):
    _name = "mass.update.quotation.file"

    def _default_file(self):
        if self._context.get('active_ids'):
            return self.env['document.quotation.file'].browse(self._context.get('active_ids'))

    file = fields.Many2many('document.quotation.file', string="Record", required=True, default=_default_file)
    write_users = fields.Many2many('res.users', 'document_quotation_file_mass_write_user_rel', 'mass_id',
                                   'res_user_id',
                                   string='Write Users', )
    read_users = fields.Many2many('res.users', 'document_quotation_file_mass_read_user_rel', 'mass_id',
                                  'res_user_id',
                                  string='Read Users')
    users = fields.Many2many('res.users', 'document_quotation_file_mass_release_user_rel', 'mass_id',
                             'res_user_id',
                             string='Select Users')
    context = fields.Char(compute='_get_context')
    invisible = fields.Boolean(compute='_get_context')
    # external user
    external_name = fields.Char(string='User Name')
    external_email = fields.Char(string="Google Email")
    external_type = fields.Selection([('read', 'Read'), ('write', 'Write')], default='read')

    @api.depends('file')
    def _get_context(self):
        if len(self.file) > 0:
            self.invisible = False
            if self._context['update'] == True:
                self.context = 'update'
            if self._context['drop'] == True:
                self.context = 'drop'
        else:
            self.invisible = True

    def update_can_edit_user(self):
        message = 'Select Files/Users To Update!'
        file_success = []
        file_fail = []
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        if len(rec.users) > 0:
                            for user in rec.users:
                                if user not in file.users_update:
                                    file.write({
                                        'users_update': [(4, user.id)]
                                    })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def update_external_users(self):
        message = 'Fill All Data External User Or Select File To Update!'
        file_success = []
        file_fail = []
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        if rec.external_name and rec.external_email and rec.external_type:
                            exist_email = [a.user_email for a in file.external_users]
                            if rec.external_email not in exist_email:
                                file.write({
                                    'external_users': [[0, 0, {'name': rec.external_name, 'user_email': rec.external_email, 'type': rec.external_type}]]
                                })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def update_users(self):
        file_success = []
        file_fail = []
        message = 'Select Files To Update!'
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        if rec.write_users and len(rec.write_users) > 0:
                            curent_write_users = [a.id for a in file.write_users if len(file.write_users) > 0]
                            for w_user in rec.write_users:
                                if w_user.id not in curent_write_users:
                                    file.write({
                                        'write_users': [(4, w_user.id)]
                                    })
                        if rec.read_users and len(rec.read_users) > 0:
                            curent_read_users = [u.id for u in file.read_users if len(file.read_users) > 0]
                            for r_user in rec.read_users:
                                if r_user.id not in curent_read_users:
                                    file.write({
                                        'read_users': [(4, r_user.id)]
                                    })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def delete_user(self):
        file_success = []
        file_fail = []
        message = 'Select Files To Update!'
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        list_w_uid = [u.id for u in file.write_users if len(file.write_users) > 0]
                        list_r_uid = [u.id for u in file.read_users if len(file.read_users) > 0]
                        if len(rec.users) > 0:
                            for user in rec.users:
                                if user.id in list_w_uid:
                                    file.write({
                                        'write_users': [(3, user.id)]
                                        # can use this instead [[6, False, [2]]]
                                    })
                                if user.id in list_r_uid:
                                    file.write({
                                        'read_users': [(3, user.id)]
                                    })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def get_permission(self, file=None):
        can_update = False
        for e in self:
            if self.user_has_groups('base.group_system'):
                can_update = True
            elif self._uid in [u.id for u in file.users_update]:
                can_update = True
            else:
                if file.create_uid.id == self._uid:
                    can_update = True
        return can_update


class MassActionCRM(models.TransientModel):
    _name = "mass.update.crm.file"

    def _default_file(self):
        if self._context.get('active_ids'):
            return self.env['document.crm.file'].browse(self._context.get('active_ids'))

    file = fields.Many2many('document.crm.file', string="Record", required=True, default=_default_file)
    write_users = fields.Many2many('res.users', 'document_crm_file_mass_write_user_rel', 'mass_id',
                                   'res_user_id',
                                   string='Write Users', )
    read_users = fields.Many2many('res.users', 'document_crm_file_mass_read_user_rel', 'mass_id',
                                  'res_user_id',
                                  string='Read Users')
    users = fields.Many2many('res.users', 'document_crm_file_mass_release_user_rel', 'mass_id',
                             'res_user_id',
                             string='Select Users')
    context = fields.Char(compute='_get_context')
    invisible = fields.Boolean(compute='_get_context')
    # external user
    external_name = fields.Char(string='User Name')
    external_email = fields.Char(string="Google Email")
    external_type = fields.Selection([('read', 'Read'), ('write', 'Write')], default='read')

    @api.depends('file')
    def _get_context(self):
        if len(self.file) > 0:
            self.invisible = False
            if self._context['update'] == True:
                self.context = 'update'
            if self._context['drop'] == True:
                self.context = 'drop'
        else:
            self.invisible = True

    def update_can_edit_user(self):
        message = 'Select Files/Users To Update!'
        file_success = []
        file_fail = []
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        if len(rec.users) > 0:
                            for user in rec.users:
                                if user not in file.users_update:
                                    file.write({
                                        'users_update': [(4, user.id)]
                                    })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def update_external_users(self):
        message = 'Fill All Data External User Or Select File To Update!'
        file_success = []
        file_fail = []
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        if rec.external_name and rec.external_email and rec.external_type:
                            exist_email = [a.user_email for a in file.external_users]
                            if rec.external_email not in exist_email:
                                file.write({
                                    'external_users': [[0, 0, {'name': rec.external_name, 'user_email': rec.external_email, 'type': rec.external_type}]]
                                })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def update_users(self):
        file_success = []
        file_fail = []
        message = 'Select Files To Update!'
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        if rec.write_users and len(rec.write_users) > 0:
                            curent_write_users = [a.id for a in file.write_users if len(file.write_users) > 0]
                            for w_user in rec.write_users:
                                if w_user.id not in curent_write_users:
                                    file.write({
                                        'write_users': [(4, w_user.id)]
                                    })
                        if rec.read_users and len(rec.read_users) > 0:
                            curent_read_users = [u.id for u in file.read_users if len(file.read_users) > 0]
                            for r_user in rec.read_users:
                                if r_user.id not in curent_read_users:
                                    file.write({
                                        'read_users': [(4, r_user.id)]
                                    })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def delete_user(self):
        file_success = []
        file_fail = []
        message = 'Select Files To Update!'
        for rec in self:
            files = rec.file
            if len(files) > 0:
                for file in files:
                    can_update = self.get_permission(file)
                    if can_update:
                        file_success.append(file.name)
                        list_w_uid = [u.id for u in file.write_users if len(file.write_users) > 0]
                        list_r_uid = [u.id for u in file.read_users if len(file.read_users) > 0]
                        if len(rec.users) > 0:
                            for user in rec.users:
                                if user.id in list_w_uid:
                                    file.write({
                                        'write_users': [(3, user.id)]
                                        # can use this instead [[6, False, [2]]]
                                    })
                                if user.id in list_r_uid:
                                    file.write({
                                        'read_users': [(3, user.id)]
                                    })
                    else:
                        file_fail.append(file.name)
                if len(file_fail) > 0 and len(file_success) > 0:
                    message = "Successfully.Exception: %s Not Permission!" % str(file_fail)
                elif len(file_success) == 0:
                    message = "Not Permission On Files"
                else:
                    message = " All Successfully!"
        return {
            'name': 'Message',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'raise.pop.message',
            'target': 'new',
            'context': {'default_name': message}
        }

    def get_permission(self, file=None):
        can_update = False
        for e in self:
            if self.user_has_groups('base.group_system'):
                can_update = True
            elif self._uid in [u.id for u in file.users_update]:
                can_update = True
            else:
                if file.create_uid.id == self._uid:
                    can_update = True
        return can_update


class RaisePopMessage(models.TransientModel):
    _name = "raise.pop.message"

    name = fields.Char('Message')


class MassActionPopup(models.TransientModel):
    _name = "mass.action.update.permission"

    name = fields.Char()
    type = fields.Selection(
        [('all', 'All Model'), ('gen', 'General'), ('project', 'Project'), ('quotation', 'Quotation'), ('crm', 'CRM')], required=True,
        default='all')

    def force_update(self):
        if self.type == 'all':
            need_to_unlink = self.env['document.permission'].sudo().search([])
            # delete all
            need_to_unlink.unlink()
            # generate permission general document users
            self.env.cr.execute(
                """select general_part_id,res_user_id from document_general_part_write_user_rel """, )
            general_w_user_rel = self.env.cr.fetchall()
            # general_w_user_rel = self.env['document.general.part.write.user.rel'].sudo().search([])
            gen_write_users = []
            for e in general_w_user_rel:
                gen_write_users.append([e[0], e[1]])
                self.env['document.permission'].sudo().create({
                    'type': 'write',
                    'model': 'general',
                    'res_id': e[0],
                    'res_user_id': e[1],
                })
            self.env.cr.execute(
                """select general_part_id,res_group_id from document_general_part_read_group_rel """, )
            general_r_groups_rel = self.env.cr.fetchall()
            for e in general_r_groups_rel:
                user_ids = self.env['document.general.part'].sudo().get_user_id_from_group(e[1])
                for uid in user_ids:
                    if [e[0], uid] not in gen_write_users:
                        self.env['document.permission'].sudo().create({
                            'type': 'read',
                            'model': 'general',
                            'res_id': e[0],
                            'res_user_id': uid,
                        })
            # generate permission project document users
            self.env.cr.execute(
                """select project_part_id,res_user_id from document_project_part_write_user_rel """, )
            project_w_user_rel = self.env.cr.fetchall()
            project_write_users = []
            for e in project_w_user_rel:
                project_write_users.append([e[0], e[1]])
                self.env['document.permission'].sudo().create({
                    'type': 'write',
                    'model': 'project',
                    'res_id': e[0],
                    'res_user_id': e[1],
                })
            self.env.cr.execute(
                """select project_part_id,res_user_id from document_project_part_read_user_rel """, )
            project_r_user_rel = self.env.cr.fetchall()
            for e in project_r_user_rel:
                if [e[0], e[1]] not in project_write_users:
                    self.env['document.permission'].sudo().create({
                        'type': 'read',
                        'model': 'project',
                        'res_id': e[0],
                        'res_user_id': e[1],
                    })
            # generate permission quotation document users
            self.env.cr.execute(
                """select quotation_part_id,res_user_id from document_quotation_part_write_user_rel """, )
            quotation_w_user_rel = self.env.cr.fetchall()
            quotation_write_users = []
            for e in quotation_w_user_rel:
                quotation_write_users.append([e[0], e[1]])
                self.env['document.permission'].sudo().create({
                    'type': 'write',
                    'model': 'quotation',
                    'res_id': e[0],
                    'res_user_id': e[1],
                })
            self.env.cr.execute(
                """select quotation_part_id,res_user_id from document_quotation_part_read_user_rel """, )
            quotation_r_user_rel = self.env.cr.fetchall()
            for e in quotation_r_user_rel:
                if [e[0], e[1]] not in quotation_write_users:
                    self.env['document.permission'].sudo().create({
                        'type': 'read',
                        'model': 'quotation',
                        'res_id': e[0],
                        'res_user_id': e[1],
                    })
            # generate permission crm document users
            self.env.cr.execute(
                """select crm_part_id,res_user_id from document_crm_part_write_user_rel """, )
            crm_w_user_rel = self.env.cr.fetchall()
            crm_write_users = []
            for e in crm_w_user_rel:
                crm_write_users.append([e[0], e[1]])
                self.env['document.permission'].sudo().create({
                    'type': 'write',
                    'model': 'crm',
                    'res_id': e[0],
                    'res_user_id': e[1],
                })
            self.env.cr.execute(
                """select crm_part_id,res_user_id from document_crm_part_read_user_rel """, )
            crm_r_user_rel = self.env.cr.fetchall()
            for e in crm_r_user_rel:
                if [e[0], e[1]] not in crm_write_users:
                    self.env['document.permission'].sudo().create({
                        'type': 'read',
                        'model': 'crm',
                        'res_id': e[0],
                        'res_user_id': e[1],
                    })
        elif self.type == 'gen':
            need_to_unlink = self.env['document.permission'].sudo().search([('type', '=', 'general')])
        elif self.type == 'project':
            need_to_unlink = self.env['document.permission'].sudo().search([('type', '=', 'project')])
        elif self.type == 'quotation':
            need_to_unlink = self.env['document.permission'].sudo().search([('type', '=', 'quotation')])
        else:
            need_to_unlink = self.env['document.permission'].sudo().search([('type', '=', 'crm')])
        return True
