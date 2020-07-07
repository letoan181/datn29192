import oauth2client
import oauth2client.client
from googleapiclient.discovery import build
from oauth2client.client import GoogleCredentials

from odoo import _
from odoo.exceptions import UserError, RedirectWarning
from odoo.http import request


class GeneralDocumentHelper:
    def update_general_document_permission(self):
        request.env.cr.execute()
        a =0

