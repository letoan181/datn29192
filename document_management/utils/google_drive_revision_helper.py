import json

from odoo import _
from odoo.exceptions import UserError
from odoo.http import request
from ..utils.google_drive_helper import GoogleDriveHelper


class GoogleDriveRevisionHelper:
    google_drive_helper = None

    def _google_call_back(self, request_id, response, exception):
        if exception:
            raise UserError(_("Something went wrong, please try again"))
        else:
            a = 0

    def sync_google_drive_file_changes(self):
        try:
            if self.google_drive_helper is None:
                self.google_drive_helper = GoogleDriveHelper()
            # check and init track_start_page_token
            Config = request.env['ir.config_parameter'].sudo()
            track_start_page_token = Config.get_param('document_management.track_start_page_token')
            if track_start_page_token == False or track_start_page_token is None:
                track_start_page_data = self.google_drive_helper.get_change_start_page_token()
                track_start_page_token = track_start_page_data['startPageToken']
                request.env['ir.config_parameter'].sudo().set_param('document_management.track_start_page_token',
                                                                    track_start_page_token)
            # get next changes
            if track_start_page_token:
                next_change = self.google_drive_helper.get_change_next_change(track_start_page_token)
                if next_change['changes'] is not None and len(next_change['changes']) > 0:
                    request.env['document.google.drive.change'].sudo().create({
                        'track_start_page_token': track_start_page_token,
                        'track_end_page_token': next_change['newStartPageToken'],
                        'response': json.dumps(next_change)
                    })
                    if next_change['newStartPageToken'] is not None:
                        Config.set_param('document_management.track_start_page_token', next_change['newStartPageToken'])
                    for e in next_change['changes']:
                        if e['type'] == 'file':
                            old_file = request.env['document.google.drive.file'].sudo().search(
                                [('file_id', 'like', e['fileId'])])
                            if len(old_file.ids) == 0:
                                request.env['document.google.drive.file'].sudo().create([{
                                    'file_id': e['fileId']
                                }])
                            request.env['document.google.drive.file'].sudo().search(
                                [('file_id', 'like', e['fileId'])]).write({
                                'need_update': True,
                                'file_name': e['file']['name']
                            })
        except Exception as ex:
            a = 0

    def sync_google_drive_file_revision(self):
        if self.google_drive_helper is None:
            self.google_drive_helper = GoogleDriveHelper()
        # check if current file does not exist
        new_file_revisions = request.env['document.google.drive.file'].sudo().search(
            [('need_update', '=', True), ('status', '=', None)], limit=100)
        for new_file_revision in new_file_revisions:
            track_start_page_token = None
            error_message = "Something went wrong"
            if not new_file_revision['track_start_page_token']:
                try:
                    track_start_page_token = self.google_drive_helper.get_revision_start_page_token(
                        new_file_revision['file_id'])
                    for e in track_start_page_token['revisions']:
                        try:
                            request.env.cr.execute(
                                """INSERT INTO document_google_drive_revision (file_id, revision_id) SELECT %s,%s WHERE NOT EXISTS ( SELECT id FROM document_google_drive_revision WHERE file_id like %s and revision_id = %s )""",
                                (new_file_revision['file_id'], e['id'], new_file_revision['file_id'], e['id'],))
                        except Exception as ex:
                            a=0
                except Exception as ex:
                    error_message = str(ex)
            if track_start_page_token is None:
                request.env['document.google.drive.file'].sudo().search(
                    [('file_id', 'like', new_file_revision['file_id'])]).write({
                    'status': error_message
                })

    def sync_google_drive_file_revision_detail(self):
        if self.google_drive_helper is None:
            self.google_drive_helper = GoogleDriveHelper()
        # check if current file does not exist
        new_file_revisions = request.env['document.google.drive.revision'].sudo().search(
            [('status', '=', None)], limit=100)
        for new_file_revision in new_file_revisions:
            track_start_page_token = None
            error_message = "Something went wrong"
            if not new_file_revision['track_start_page_token']:
                try:
                    track_start_page_token = self.google_drive_helper.get_revision_detail(
                        new_file_revision['file_id'], new_file_revision['revision_id'],)
                    a=0
                except Exception as ex:
                    error_message = str(ex)
            # if track_start_page_token is None:
            #     request.env['document.google.drive.file'].sudo().search(
            #         [('file_id', 'like', new_file_revision['file_id'])]).write({
            #         'status': error_message
            #     })

        a=0
