# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""HookReceiver module"""
import logging
import superdesk
from eve.utils import config
from superdesk.errors import SuperdeskApiError
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk import get_resource_service
from flask import url_for, request, current_app as app
from superdesk.media.renditions import generate_renditions, delete_file_on_error
from superdesk.media.media_operations import (
    download_file_from_url, process_file_from_stream,
    crop_image, decode_metadata, download_file_from_encoded_str
)

from . import feeding_provider  # NOQA


bp = superdesk.Blueprint('hook_receiver_raw', __name__)
superdesk.blueprint(bp)
logger = logging.getLogger(__name__)


# @TODO: leave this
@bp.route('/hook_receiver/<path:hook_id>', methods=['GET', 'POST'])
def get_hook_receiver_as_data_uri(hook_id):
    data = request.json
    if not data:
        data = list(request.form.items())

    # logger.critical(dir(request))
    logger.critical(hook_id)
    logger.critical(data)
    logger.critical([
        (item["_id"], item["source"]) for item in
        get_resource_service("ingest_providers").get(req=None, lookup={})
    ])

    ingest_provider = get_resource_service("ingest_providers").find_one(req=None, _id=hook_id)
    if ingest_provider:
        data = '{"_status": "OK"}'
        response = app.response_class(
            data,
            direct_passthrough=True)
        response.make_conditional(request)
        return response
    raise SuperdeskApiError.notFoundError('Hook is not registered.')


def url_for_media(media_id):
    return app.media.url_for_media(media_id)


def hook_receiver_url(media_id):
    return url_for('hook_receiver_raw.get_hook_receiver_as_data_uri', media_id=media_id,
                   _external=True, _schema=app.config.get('URL_PROTOCOL'))


# @TODO: leave this
def init_app(app):
    endpoint_name = 'hook_receiver'
    service = HookReceiverService(endpoint_name, backend=superdesk.get_backend())
    HookReceiverResource(endpoint_name, app=app, service=service)


# @TODO: change this
class HookReceiverResource(Resource):
    schema = {
        'media': {'type': 'file'},
        'CropLeft': {'type': 'integer'},
        'CropRight': {'type': 'integer'},
        'CropTop': {'type': 'integer'},
        'CropBottom': {'type': 'integer'},
        'URL': {'type': 'string'},
        'mimetype': {'type': 'string'},
        'filemeta': {'type': 'dict'}
    }
    extra_response_fields = ['renditions']
    datasource = {
        'projection': {
            'mimetype': 1,
            'filemeta': 1,
            '_created': 1,
            '_updated': 1,
            '_etag': 1,
            'media': 1,
            'renditions': 1,
        }
    }
    item_methods = ['GET', 'DELETE']
    resource_methods = ['GET', 'POST']
    privileges = {'POST': 'ingest', 'DELETE': 'ingest'}


# @TODO: change this
class HookReceiverService(BaseService):

    def on_create(self, docs):
        for doc in docs:
            if doc.get('URL') and doc.get('media'):
                message = 'HookReceivering file by URL and file stream in the same time is not supported.'
                raise SuperdeskApiError.badRequestError(message)

            content = None
            filename = None
            content_type = None
            if doc.get('media'):
                content = doc['media']
                filename = content.filename
                content_type = content.mimetype
            elif doc.get('URL'):
                content, filename, content_type = self.download_file(doc)

            self.crop_and_store_file(doc, content, filename, content_type)

    def crop_and_store_file(self, doc, content, filename, content_type):
        # retrieve file name and metadata from file
        file_name, content_type, metadata = process_file_from_stream(content, content_type=content_type)
        # crop the file if needed, can change the image size
        was_cropped, out = crop_image(content, filename, doc)
        # the length in metadata could be updated if it was cropped
        if was_cropped:
            file_name, content_type, metadata_after_cropped = process_file_from_stream(out, content_type=content_type)
            # when cropped, metadata are reseted. Then we update the previous metadata variable
            metadata['length'] = metadata_after_cropped['length']
        try:
            logger.debug('Going to save media file with %s ' % file_name)
            out.seek(0)
            file_id = app.media.put(out, filename=file_name, content_type=content_type,
                                    resource=self.datasource, metadata=metadata)
            doc['media'] = file_id
            doc['mimetype'] = content_type
            doc['filemeta'] = decode_metadata(metadata)
            inserted = [doc['media']]
            file_type = content_type.split('/')[0]
            rendition_spec = config.RENDITIONS['avatar']
            renditions = generate_renditions(out, file_id, inserted, file_type,
                                             content_type, rendition_spec, url_for_media)
            doc['renditions'] = renditions
        except Exception as io:
            logger.exception(io)
            for file_id in inserted:
                delete_file_on_error(doc, file_id)
            raise SuperdeskApiError.internalError('Generating renditions failed')

    def download_file(self, doc):
        url = doc.get('URL')
        if not url:
            return
        if url.startswith('data'):
            return download_file_from_encoded_str(url)
        else:
            return download_file_from_url(url)
