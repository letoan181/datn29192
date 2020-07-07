from odoo import models, fields


class GoogleDriveRevisionDetail(models.Model):
    _name = "document.google.drive.file"
    _description = "Manage document drive files"

    file_id = fields.Char()
    file_name = fields.Char()
    track_start_page_token = fields.Char("Tracking Start Page Token")
    need_update = fields.Boolean(required=True, default=False)
    status = fields.Char()

    _sql_constraints = [
        ('file_id_uniq', 'unique (file_id)', "File_id already exists !"),
    ]


class GoogleDriveRevision(models.Model):
    _name = "document.google.drive.revision"
    _description = "Manage document drive revisions"

    file_id = fields.Char()
    revision_id = fields.Integer()
    status = fields.Char()
    track_start_page_token = fields.Char("Tracking Start Page Token")

    _sql_constraints = [
        ('file_id_uniq', 'unique (file_id, revision_id)', "File_id already exists !"),
    ]
