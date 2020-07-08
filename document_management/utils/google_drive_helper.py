import oauth2client
import oauth2client.client
from googleapiclient.discovery import build
from oauth2client.client import GoogleCredentials

from odoo import _
from odoo.exceptions import UserError, RedirectWarning
from odoo.http import request


class GoogleDriveHelper:
    driver_service_singleton = None
    new_permission_id = None
    context_env = None

    def set_context_env(self, context_env):
        self.context_env = context_env

    def _google_call_back(self, request_id, response, exception):
        if exception:
            raise UserError(_("Something went wrong, please try again"))
        else:
            a = 0

    def _get_driver_service(self=None):
        if self.driver_service_singleton is None:
            if self.context_env is not None:
                Config = self.context_env.env['ir.config_parameter'].sudo()
                google_drive_refresh_token = Config.get_param('google_drive_refresh_token')
            else:
                Config = request.env['ir.config_parameter'].sudo()
                google_drive_refresh_token = Config.get_param('google_drive_refresh_token')
                user_is_admin = request.env['res.users'].browse(request.env.user.id)._is_admin()
                if not google_drive_refresh_token:
                    if user_is_admin:
                        dummy, action_id = request.env['ir.model.data'].get_object_reference('base_setup',
                                                                                             'action_general_configuration')
                        msg = _(
                            "You haven't configured 'Authorization Code' generated from google, Please generate and configure it .")
                        raise RedirectWarning(msg, action_id, _('Go to the configuration panel'))
                    else:
                        raise UserError(_("Google Drive is not yet configured. Please contact your administrator."))
            google_drive_client_id = Config.get_param('google_drive_client_id')
            google_drive_client_secret = Config.get_param('google_drive_client_secret')
            access_token = None
            token_expiry = None
            token_uri = 'https://www.googleapis.com/auth/drive.metadata.readonly'

            # GOOGLE_TOKEN_URI = 'https://oauth2.googleapis.com/token'
            token_uri = oauth2client.GOOGLE_TOKEN_URI
            user_agent = 'Python client library'
            revoke_uri = None
            credentials = GoogleCredentials(
                access_token,
                google_drive_client_id,
                google_drive_client_secret,
                google_drive_refresh_token,
                token_expiry,
                token_uri,
                user_agent,
                revoke_uri=revoke_uri
            )
            credentials.scopes = ['https://www.googleapis.com/auth/drive.metadata',
                                  'https://www.googleapis.com/auth/drive.readonly',
                                  'https://www.googleapis.com/auth/drive']
            self.driver_service_singleton = build('drive', 'v3', credentials=credentials)
        return self.driver_service_singleton

    def create_file(self,folder_name):
        file_metadata = {
            'name': folder_name,
            'writersCanShare': False,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        newFile = self._get_driver_service().files().create(body=file_metadata,
                                                            fields='id').execute()
        return newFile

    def create_sub_file(self, parent_id, folder_name):
        file_metadata = {
            'name': folder_name,
            'writersCanShare': False,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        newFile = self._get_driver_service().files().create(body=file_metadata,
                                                            fields='id, parents').execute()
        previous_parents = ",".join(newFile.get('parents'))
        file = self._get_driver_service().files().update(fileId=newFile['id'],
                                                         addParents=parent_id,
                                                         removeParents=previous_parents,
                                                         fields='id, parents').execute()
        return file

    def create_copy(self, source_file_id, parent_file_id, file_name):
        file_metadata = {
            'name': file_name,
            'writersCanShare': False
        }
        newFile = self._get_driver_service().files().copy(fileId=source_file_id, body={},
                                                          fields='id, parents').execute()
        previous_parents = ",".join(newFile.get('parents'))
        file = self._get_driver_service().files().update(fileId=newFile['id'],
                                                         addParents=parent_file_id,
                                                         removeParents=previous_parents,
                                                         fields='id, parents',
                                                         body=file_metadata).execute()
        return file

    def update_file_name(self, file_id, new_name):
        # File's new metadata.
        file_metadata = {
            'name': new_name
        }
        updated_file = self._get_driver_service().files().update(
            fileId=file_id,
            body=file_metadata).execute()
        return updated_file

    def deleteFile(self, file_id):
        # File's new metadata.
        file_metadata = {
            'trashed': True
        }
        updated_file = self._get_driver_service().files().update(
            fileId=file_id,
            body=file_metadata).execute()
        return updated_file

    def drop_file_permission_callback(self, request_id, response, exception):
        if exception:
            raise UserError(_("Something went wrong, please try again"))
        else:
            self.new_permission_id = response['id']

    def _google_file_write_call_back(self, request_id, response, exception):
        if exception:
            raise UserError(_("Something went wrong, please try again"))
        else:
            self.new_permission_id = response['id']

    def create_file_write_permission(self, file_id, email):
        batch = self._get_driver_service().new_batch_http_request(callback=self._google_file_write_call_back)
        user_permission = {
            'type': 'user',
            'role': 'writer',
            'emailAddress': email
        }
        batch.add(self._get_driver_service().permissions().create(
            fileId=file_id,
            body=user_permission,
            fields='id',
        ))
        batch.execute()
        return self.new_permission_id

    def create_file_read_permission(self, file_id, email):
        batch = self._get_driver_service().new_batch_http_request(callback=self._google_file_write_call_back)
        user_permission = {
            'type': 'user',
            'role': 'reader',
            'emailAddress': email
        }
        batch.add(self._get_driver_service().permissions().create(
            fileId=file_id,
            body=user_permission,
            fields='id',
        ))
        batch.execute()
        return self.new_permission_id

    def drop_file_permission(self, file_id, permission_id):
        updated_file = self._get_driver_service().permissions().delete(
            fileId=file_id,
            permissionId=permission_id).execute()
        return updated_file

    # public drive api
    def create_public_file_write_permission(self, file_id):
        batch = self._get_driver_service().new_batch_http_request(callback=self._google_file_write_call_back)
        user_permission = {
            'type': 'anyone',
            'role': 'writer',
        }
        batch.add(self._get_driver_service().permissions().create(
            fileId=file_id,
            body=user_permission,
            fields='id',
        ))
        batch.execute()
        return self.new_permission_id

    def create__public_file_read_permission(self, file_id):
        batch = self._get_driver_service().new_batch_http_request(callback=self._google_file_write_call_back)
        user_permission = {
            'type': 'anyone',
            'role': 'reader',
        }
        batch.add(self._get_driver_service().permissions().create(
            fileId=file_id,
            body=user_permission,
            fields='id',
        ))
        batch.execute()
        return self.new_permission_id

    def create_public_file_comment_permission(self, file_id):
        batch = self._get_driver_service().new_batch_http_request(callback=self._google_file_write_call_back)
        user_permission = {
            'type': 'anyone',
            'role': 'commenter',
        }
        batch.add(self._get_driver_service().permissions().create(
            fileId=file_id,
            body=user_permission,
            fields='id',
        ))
        batch.execute()
        return self.new_permission_id

    def drop_public_file_permission(self, file_id, permission_id):
        updated_file = self._get_driver_service().permissions().delete(
            fileId=file_id,
            permissionId=permission_id).execute()
        return updated_file

    def get_change_start_page_token(self):
        return self._get_driver_service().changes().getStartPageToken().execute()

    def get_change_next_change(self, page_token):
        return self._get_driver_service().changes().list(pageToken=page_token,
                                                         spaces='drive').execute()

    def get_revision_start_page_token(self, file_id):
        return self._get_driver_service().revisions().list(fileId=file_id,
                                                           ).execute()

    def get_revision_detail(self, file_id, revision_id):
        return self._get_driver_service().revisions().get(fileId=file_id, revisionId=revision_id
                                                          ).execute()

    def list_permission(self, file_id):
        permissions = self._get_driver_service().permissions().list(fileId=file_id).execute()
        return permissions.get('permissions', [])

    def detail_permission(self, file_id, permission_id):
        permission = self._get_driver_service().permissions().get(
            fileId=file_id, permissionId=permission_id,
            fields='kind,id,type,emailAddress,domain,role,allowFileDiscovery,displayName,photoLink,expirationTime,teamDrivePermissionDetails,deleted').execute()

        return permission
