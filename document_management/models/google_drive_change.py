from odoo import models, fields


class GoogleDriveChange(models.Model):
    _name = "document.google.drive.change"
    _description = "Manage document drive changes"

    track_start_page_token = fields.Char("Tracking Start Page Token")
    track_end_page_token = fields.Char("Tracking End Page Token")
    response = fields.Char("Response")
