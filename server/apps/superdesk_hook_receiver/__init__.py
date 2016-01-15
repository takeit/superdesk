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
from superdesk.errors import SuperdeskApiError
from superdesk import get_resource_service
from flask import request, current_app as app

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
    """
    logger.critical([
        (item["_id"], item["source"]) for item in
        get_resource_service("ingest_providers").get(req=None, lookup={})
    ])
    """
    logger.critical(list(
        get_resource_service("ingest_providers").get(req=None, lookup={})
    ))

    ingest_provider = get_resource_service("ingest_providers").find_one(
        req=None, _id=hook_id, feeding_service='webhook'
    )
    if not ingest_provider:
        raise SuperdeskApiError.notFoundError('Hook is not registered.')

    response = app.response_class(
        '{"_status": "OK"}',
        direct_passthrough=True)
    response.make_conditional(request)
    return response
