# -*- coding: utf-8 -*-
import re

from odoo import http
from odoo.http import request


class DocumentManagement(http.Controller):
    def get_permission(self, record=None, model=None):
        perm = {
            'perm_create': False,
            'perm_write': False,
            'perm_unlink': False
        }
        if model == 'document.general':
            if request.env['res.users'].browse(request._uid).user_has_groups('base.group_system') or request.env[
                'res.users'].browse(request._uid).user_has_groups(
                'document_management.group_document_general_manager'):
                perm = {
                    'perm_create': True,
                    'perm_write': True,
                    'perm_unlink': True,
                    'perm_create_child': False
                }
        elif model == 'project.project':
            perm = {
                'perm_create': False,
                'perm_write': False,
                'perm_unlink': False
            }
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or record.user_id.id == request._uid:
                perm.update({
                    'perm_create_child': True
                })
        elif model == 'sale.order':
            perm = {
                'perm_create': False,
                'perm_write': False,
                'perm_unlink': False
            }
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or record.user_id.id == request._uid:
                perm.update({
                    'perm_create_child': True
                })
        elif model == 'crm.lead':
            perm = {
                'perm_create': False,
                'perm_write': False,
                'perm_unlink': False
            }
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or record.user_id.id == request._uid:
                perm.update({
                    'perm_create_child': True
                })
        elif model == 'document.general.part':
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or record.create_uid.id == request._uid:
                perm = {
                    'perm_create': False,
                    'perm_write': True,
                    'perm_unlink': True
                }
            check_perm_part = False
            write_users = [e for e in request.env[model].sudo().browse(record.id).write_users]
            users = [user.id for user in write_users]
            if request._uid in users:
                check_perm_part = True
            if request.env['res.users'].browse(request._uid).user_has_groups('base.group_system') or request.env[
                'res.users'].browse(request._uid).user_has_groups(
                'document_management.group_document_general_part_manager') or check_perm_part:
                perm.update({
                    'perm_create_child': True
                })
        elif model == 'document.project.part':
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or record.document_project_id.user_id.id == request._uid or record.create_uid.id == request._uid:
                perm = {
                    'perm_create': True,
                    'perm_write': True,
                    'perm_unlink': True
                }
            check_perm_part = False
            write_users = [e for e in request.env[model].sudo().browse(record.id).write_users]
            users = [user.id for user in write_users]
            if request._uid in users:
                check_perm_part = True
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or check_perm_part:
                perm.update({
                    'perm_create_child': True
                })
        elif model == 'document.quotation.part':
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or record.document_quotation_id.user_id.id == request._uid or record.create_uid.id == request._uid:
                perm = {
                    'perm_create': True,
                    'perm_write': True,
                    'perm_unlink': True
                }
            check_perm_part = False
            write_users = [e for e in request.env[model].sudo().browse(record.id).write_users]
            users = [user.id for user in write_users]
            if request._uid in users:
                check_perm_part = True
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or check_perm_part:
                perm.update({
                    'perm_create_child': True
                })
        elif model == 'document.crm.part':
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or record.document_crm_id.user_id.id == request._uid or record.create_uid.id == request._uid:
                perm = {
                    'perm_create': True,
                    'perm_write': True,
                    'perm_unlink': True
                }
            check_perm_part = False
            write_users = [e for e in request.env[model].sudo().browse(record.id).write_users]
            users = [user.id for user in write_users]
            if request._uid in users:
                check_perm_part = True
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or check_perm_part:
                perm.update({
                    'perm_create_child': True
                })
        elif model == 'document.general.file':
            if request.env['res.users'].browse(request._uid).user_has_groups('base.group_system') or request.env[
                'res.users'].browse(request._uid).user_has_groups(
                'document_management.group_document_general_part_manager') or record.create_uid.id == request._uid:
                perm = {
                    'perm_create': True,
                    'perm_write': True,
                    'perm_unlink': True
                }
            check_perm_part = False
            rel = 'document.general.part'
            write_users = [e for e in request.env[rel].sudo().browse(record.res_id).write_users]
            users = [user.id for user in write_users]
            if request._uid in users:
                check_perm_part = True
            if check_perm_part:
                perm = {
                    'perm_create': True,
                    'perm_write': False,
                    'perm_unlink': False
                }
        elif model == 'document.project.file':
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or record.create_uid.id == request._uid:
                perm = {
                    'perm_create': True,
                    'perm_write': True,
                    'perm_unlink': True
                }
            check_perm_part = False
            rel = 'document.project.part'
            write_users = [e for e in request.env[rel].sudo().browse(record.res_id).write_users]
            users = [user.id for user in write_users]
            if request._uid in users:
                check_perm_part = True
            if check_perm_part:
                perm = {
                    'perm_create': True,
                    'perm_write': False,
                    'perm_unlink': False
                }

        elif model == 'document.quotation.file':
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or record.create_uid.id == request._uid:
                perm = {
                    'perm_create': True,
                    'perm_write': True,
                    'perm_unlink': True
                }
            check_perm_part = False
            rel = 'document.quotation.part'
            write_users = [e for e in request.env[rel].sudo().browse(record.res_id).write_users]
            users = [user.id for user in write_users]
            if request._uid in users:
                check_perm_part = True
            if check_perm_part:
                perm = {
                    'perm_create': True,
                    'perm_write': False,
                    'perm_unlink': False
                }
        elif model == 'document.crm.file':
            if request.env['res.users'].browse(request._uid).user_has_groups(
                    'base.group_system') or record.create_uid.id == request._uid:
                perm = {
                    'perm_create': True,
                    'perm_write': True,
                    'perm_unlink': True
                }
            check_perm_part = False
            rel = 'document.crm.part'
            write_users = [e for e in request.env[rel].sudo().browse(record.res_id).write_users]
            users = [user.id for user in write_users]
            if request._uid in users:
                check_perm_part = True
            if check_perm_part:
                perm = {
                    'perm_create': True,
                    'perm_write': False,
                    'perm_unlink': False
                }
        return perm

    def get_action(self, model, child_model=None, record=None, active_id=None):
        action = None
        if record:
            # node_id = int(re.findall('\d+', current_node)[0])
            # model = current_node.split('_', 1)[1]
            if model == 'project.project':
                context = None
                context_child = {'default_document_project_id': record.id}
            elif model == 'sale.order':
                context = None
                context_child = {'default_document_quotation_id': record.id}
            elif model == 'crm.lead':
                context = None
                context_child = {'default_document_crm_id': record.id}
            elif model == 'document.general.part':
                context = None
                context_child = {'default_res_id': record.id}
            elif model == 'document.project.part':
                context = {'default_document_project_id': active_id}
                context_child = {'default_res_id': record.id}
            elif model == 'document.quotation.part':
                context = {'default_document_quotation_id': active_id}
                context_child = {'default_res_id': record.id}
            elif model == 'document.crm.part':
                context = {'default_document_crm_id': active_id}
                context_child = {'default_res_id': record.id}
            else:
                context = {'default_res_id': active_id}
                context_child = None
            action = {"create": {'type': 'ir.actions.act_window',
                                 'res_model': model,
                                 'context': context,
                                 'views': [[False, 'form']],
                                 'target': 'new'},
                      "create_child": {'type': 'ir.actions.act_window',
                                       'res_model': child_model,
                                       'context': context_child,
                                       'views': [[False, 'form']],
                                       'target': 'new'},
                      "edit": {
                          'type': 'ir.actions.act_window',
                          'res_model': model,
                          'res_id': record.id,
                          'views': [[False, 'form']],
                          'target': 'new',
                      },
                      "delete": {
                          'model': model,
                          'method': 'unlink',
                          'res_id': record.id
                      }
                      }
        return action

    @http.route('/document/view/tree/directory', type='json', auth='public')
    def get_root(self, model=None, permission=None, **kw):
        params = None
        children_model = None
        model_type = None
        if permission == None:
            if request.env['res.users'].browse(request._uid).user_has_groups('base.group_system'):
                permission = True
        virtual_folder = ''
        # print(permission)
        if model == 'document.general':
            params = ['document_general_id', 'document.general.part', 'name']
            model_type = 'general'
            children_model = 'document.general.part'
        elif model == 'project.project':
            params = ['document_project_id', 'document.project.part', 'document_project_name']
            model_type = 'project'
            children_model = 'document.project.part'
        elif model == 'sale.order':
            params = ['document_quotation_id', 'document.quotation.part', 'document_quotation_name']
            model_type = 'quotation'
            children_model = 'document.quotation.part'
        elif model == 'crm.lead':
            params = ['document_crm_id', 'document.crm.part', 'document_crm_name']
            model_type = 'crm'
            children_model = 'document.crm.part'
        data = []
        if params and model_type:
            if permission:
                domain = [(params[2], '!=', False)]
            else:
                res_ids = [a.res_id for a in request.env['document.permission'].sudo().search(
                    [('res_user_id', '=', request._uid), ('model', 'like', model_type)])]
                if params[0] == 'document_general_id':
                    ids = [a.document_general_id.id for a in
                           request.env[params[1]].sudo().search([('id', 'in', res_ids)])]
                elif params[0] == 'document_project_id':
                    ids = [a.document_project_id.id for a in
                           request.env[params[1]].sudo().search([('id', 'in', res_ids)])]
                elif params[0] == 'document_quotation_id':
                    ids = [a.document_quotation_id.id for a in
                           request.env[params[1]].sudo().search([('id', 'in', res_ids)])]
                elif params[0] == 'document_crm_id':
                    ids = [a.document_crm_id.id for a in request.env[params[1]].sudo().search([('id', 'in', res_ids)])]
                else:
                    ids = []
                domain = [('id', 'in', ids)]
            if model:
                root = request.env[model].sudo().search(domain)
                if len(root) > 0:
                    part_domain = None
                    for directory in root:
                        # print(directory.permission_create)
                        perm = self.get_permission(record=directory, model=model)
                        action = self.get_action(model=model, child_model=children_model, record=directory)
                        if model == 'document.general':
                            data.append(
                                {"id": str(directory.id) + '_' + model.replace(".", "_"), "model": model, "parent": "#",
                                 "text": directory.name, "is_child_listed": False, "permission": perm,
                                 "action": action},
                            )
                            children_model = 'document.general.part'
                            part_domain = [('document_general_id', '=', directory.id)]
                        elif model == 'project.project':
                            data.append(
                                {"id": str(directory.id) + '_' + model.replace(".", "_"), "model": model, "parent": "#",
                                 "text": directory.document_project_name, "is_child_listed": False, "permission": perm,
                                 "action": action},
                            )
                            children_model = 'document.project.part'
                            part_domain = [('document_project_id', '=', directory.id)]
                        elif model == 'sale.order':
                            data.append(
                                {"id": str(directory.id) + '_' + model.replace(".", "_"), "model": model, "parent": "#",
                                 "text": directory.document_quotation_name, "is_child_listed": False,
                                 "permission": perm,
                                 "action": action},
                            )
                            children_model = 'document.quotation.part'
                            part_domain = [('document_quotation_id', '=', directory.id)]
                        elif model == 'crm.lead':
                            data.append(
                                {"id": str(directory.id) + '_' + model.replace(".", "_"), "model": model, "parent": "#",
                                 "text": directory.document_crm_name, "is_child_listed": False,
                                 "permission": perm,
                                 "action": action},
                            )
                            children_model = 'document.crm.part'
                            part_domain = [('document_crm_id', '=', directory.id)]
                        if not permission and part_domain:
                            res_ids = [a.res_id for a in request.env['document.permission'].sudo().search(
                                [('res_user_id', '=', request._uid), ('model', 'like', model_type)])]
                            part_domain.append(('id', 'in', res_ids))
                        nodes = request.env[children_model].sudo().search(part_domain)
                        if len(nodes) > 0:
                            data.append(
                                {"id": str(directory.id) + '_' + model.replace(".", "_") + '_' + 'virtual_folder',
                                 "parent": str(directory.id) + '_' + model.replace(".", "_"), "text": virtual_folder,
                                 "is_child_listed": False})
                            # for node in nodes:
                            #     data.append({"id": str(node.id) + '_' + children_model,
                            #                  "parent": str(directory.id) + '_' + model.replace(".", "_"), "text": node.name, "is_child_listed": False})

            return data
        else:
            return False

    @http.route('/document/view/tree/node', type='json', auth='public')
    def get_node(self, current_node=None, permission=None, **kw):
        result = []
        child_model = None
        folder = []
        model_type = None
        is_last_file = False
        domain = None
        if current_node is not None:
            nodes = [current_node]
            for node in nodes:
                node_id = int(re.findall('\d+', node)[0])
                model = node.split('_', 1)[1]
                model = model.replace('_', '.')
                if model == 'document.general':
                    child_model = 'document.general.part'
                    model_type = 'general'
                elif model == 'project.project':
                    child_model = 'document.project.part'
                    model_type = 'project'
                elif model == 'sale.order':
                    child_model = 'document.quotation.part'
                    model_type = 'quotation'
                elif model == 'crm.lead':
                    child_model = 'document.crm.part'
                    model_type = 'crm'
                elif model == 'document.general.part':
                    child_model = 'document.general.file'
                    model_type = 'general'
                    is_last_file = True
                elif model == 'document.project.part':
                    child_model = 'document.project.file'
                    model_type = 'project'
                    is_last_file = True
                elif model == 'document.quotation.part':
                    child_model = 'document.quotation.file'
                    model_type = 'quotation'
                    is_last_file = True
                elif model == 'document.crm.part':
                    child_model = 'document.crm.file'
                    model_type = 'crm'
                    is_last_file = True
                # elif model == 'document.general.file':
                #     child_model = 'document.general.file'
                #     is_last_file = True
                # elif model == 'document.project.file':
                #     child_model = 'document.project.file'
                #     is_last_file = True
                # elif model == 'document.quotation.file':
                #     child_model = 'document.quotation.file'
                #     is_last_file = True
                # elif model == 'document.crm.file':
                #     child_model = 'document.crm.file'
                #     is_last_file = True
                if permission:
                    domain = []
                elif not permission and not is_last_file:
                    res_ids = [a.res_id for a in request.env['document.permission'].sudo().search(
                        [('res_user_id', '=', request._uid), ('model', 'like', model_type)])]
                    # ids = [a.id for a in request.env[child_model].sudo().search([('res_id', 'in', res_ids)])]
                    domain = [('id', 'in', res_ids)]
                elif not permission and is_last_file:
                    ids = [node_id, ]
                    domain = [('res_id', 'in', ids)]
                if child_model:
                    files = request.env[child_model].sudo().search(domain)
                    if len(files) > 0:
                        if is_last_file:
                            for file in files:
                                if file.res_id == node_id:
                                    # folder.append({
                                    #     'name': file.name,
                                    #     'type': 'file'
                                    # })
                                    type = file.type
                                    perm = self.get_permission(record=file, model=child_model)
                                    action = self.get_action(model=child_model,
                                                             record=file, active_id=node_id)
                                    result.append(
                                        {"id": str(file.id) + '_' + child_model.replace(".", "_") + '_' + type + 'type',
                                         "parent": node,
                                         "text": file.name,
                                         "is_child_listed": False, "permission": perm, "action": action,
                                         "a_attr": {"href": file.google_drive_url}})
                                    # result.append({"id": str(file.id) + '_' + child_model.replace(".", "_") + '_' + 'link',
                                    #                "parent": str(file.id) + '_' + child_model.replace(".", "_"),
                                    #                "text": 'Open Google Drive',
                                    #                "a_attr": {"href": file.google_drive_url}})
                        else:
                            if child_model == 'document.general.part':
                                child_child_model = 'document.general.file'
                                for file in files:
                                    if file.document_general_id.id == node_id:
                                        # folder.append({
                                        #     'name': file.name,
                                        #     'type': 'folder'
                                        # })
                                        perm = self.get_permission(record=file, model=child_model)
                                        action = self.get_action(model=child_model, child_model=child_child_model,
                                                                 record=file, active_id=node_id)
                                        result.append(
                                            {"id": str(file.id) + '_' + child_model.replace(".", "_"), "parent": node,
                                             "text": file.name,
                                             "is_child_listed": False, "permission": perm, "action": action})
                                        child_child_model = 'document.general.file'
                                        domain = [('res_id', '=', file.id)]
                                        child_files = request.env[child_child_model].sudo().search(domain)
                                        if len(child_files) > 0:
                                            result.append(
                                                {"id": str(file.id) + '_' + child_model.replace(".",
                                                                                                "_") + '_' + 'virtual_folder',
                                                 "parent": str(file.id) + '_' + child_model.replace(".", "_"),
                                                 "text": '',
                                                 "is_child_listed": False})
                            if child_model == 'document.project.part':
                                child_child_model = 'document.project.file'
                                for file in files:
                                    if file.document_project_id.id == node_id:
                                        # folder.append({
                                        #     'name': file.name,
                                        #     'type': 'folder'
                                        # })
                                        perm = self.get_permission(record=file, model=child_model)
                                        action = self.get_action(model=child_model, child_model=child_child_model,
                                                                 record=file, active_id=node_id)
                                        result.append(
                                            {"id": str(file.id) + '_' + child_model.replace(".", "_"), "parent": node,
                                             "text": file.name,
                                             "is_child_listed": False, "permission": perm, "action": action})
                                        child_child_model = 'document.project.file'
                                        domain = [('res_id', '=', file.id)]
                                        child_files = request.env[child_child_model].sudo().search(domain)
                                        if len(child_files) > 0:
                                            result.append(
                                                {"id": str(file.id) + '_' + child_model.replace(".",
                                                                                                "_") + '_' + 'virtual_folder',
                                                 "parent": str(file.id) + '_' + child_model.replace(".", "_"),
                                                 "text": '',
                                                 "is_child_listed": False})
                            if child_model == 'document.quotation.part':
                                child_child_model = 'document.quotation.file'
                                for file in files:
                                    if file.document_quotation_id.id == node_id:
                                        # folder.append({
                                        #     'name': file.name,
                                        #     'type': 'folder'
                                        # })
                                        perm = self.get_permission(record=file, model=child_model)
                                        action = self.get_action(model=child_model, child_model=child_child_model,
                                                                 record=file, active_id=node_id)
                                        result.append(
                                            {"id": str(file.id) + '_' + child_model.replace(".", "_"), "parent": node,
                                             "text": file.name,
                                             "is_child_listed": False, "permission": perm, "action": action})
                                        child_child_model = 'document.quotation.file'
                                        domain = [('res_id', '=', file.id)]
                                        child_files = request.env[child_child_model].sudo().search(domain)
                                        if len(child_files) > 0:
                                            result.append(
                                                {"id": str(file.id) + '_' + child_model.replace(".",
                                                                                                "_") + '_' + 'virtual_folder',
                                                 "parent": str(file.id) + '_' + child_model.replace(".", "_"),
                                                 "text": '',
                                                 "is_child_listed": False})
                            if child_model == 'document.crm.part':
                                child_child_model = 'document.crm.file'
                                for file in files:
                                    if file.document_crm_id.id == node_id:
                                        # folder.append({
                                        #     'name': file.name,
                                        #     'type': 'folder'
                                        # })
                                        perm = self.get_permission(record=file, model=child_model)
                                        action = self.get_action(model=child_model, child_model=child_child_model,
                                                                 record=file, active_id=node_id)
                                        result.append(
                                            {"id": str(file.id) + '_' + child_model.replace(".", "_"), "parent": node,
                                             "text": file.name,
                                             "is_child_listed": False, "permission": perm, "action": action})
                                        child_child_model = 'document.crm.file'
                                        domain = [('res_id', '=', file.id)]
                                        child_files = request.env[child_child_model].sudo().search(domain)
                                        if len(child_files) > 0:
                                            result.append(
                                                {"id": str(file.id) + '_' + child_model.replace(".",
                                                                                                "_") + '_' + 'virtual_folder',
                                                 "parent": str(file.id) + '_' + child_model.replace(".", "_"),
                                                 "text": '',
                                                 "is_child_listed": False})
        return {
            'current_node': current_node,
            'data': result,
            'folder': folder
        }

    # @http.route('/document/get/action', type='json', auth='public')
    # def get_action(self, current_node=None, permission=None):
    #     if permission:
    #         node_id = int(re.findall('\d+', current_node)[0])
    #         model = current_node.split('_', 1)[1]
    #         action = {
    #             'type': 'ir.actions.act_window',
    #             'res_model': model,
    #             'res_id': node_id,
    #             'views': [[False, 'form']],
    #             'target': 'new'
    #         }
    #     return action

    # @http.route('/document/get/permission', type='json', auth='public')
    # def get_permission(self, node=None):
    #     if node:
    #         node_id = int(re.findall('\d+', node)[0])
    #         model = node.split('_', 1)[1]
