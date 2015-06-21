# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from eve.utils import config
from flask import current_app as app
from bson.objectid import ObjectId

from superdesk.resource import Resource
from superdesk.services import BaseService
import superdesk


def init_app(app):
    endpoint_name = 'groups'
    service = GroupsService(endpoint_name, backend=superdesk.get_backend())
    GroupsResource(endpoint_name, app=app, service=service)

    endpoint_name = 'user_groups'
    service = UserGroupsService(endpoint_name, backend=superdesk.get_backend())
    UserGroupsResource(endpoint_name, app=app, service=service)


superdesk.privilege(name='groups', label='Groups Management', description='User can edit unique name.')


class GroupsResource(Resource):

    schema = {
        'name': {
            'type': 'string',
            'iunique': True,
            'required': True,
        },
        'description': {
            'type': 'string'
        },
        'members': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'user': Resource.rel('users', True)
                }
            }
        }
    }
    datasource = {'default_sort': [('created', -1)]}
    privileges = {'POST': 'groups', 'DELETE': 'groups', 'PATCH': 'groups'}


class GroupsService(BaseService):
    def on_updated(self, updates, original):
        if 'members' in updates:
            app.on_group_update_or_delete(original[config.ID_FIELD])

    def on_deleted(self, doc):
        app.on_group_update_or_delete(doc[config.ID_FIELD], event='delete')


class UserGroupsResource(Resource):
    url = 'users/<regex("[a-f0-9]{24}"):user_id>/groups'
    schema = GroupsResource.schema
    datasource = {'source': 'groups'}
    resource_methods = ['GET']


class UserGroupsService(BaseService):

    def get(self, req, lookup):
        if lookup.get('user_id'):
            lookup["members.user"] = ObjectId(lookup['user_id'])
            del lookup['user_id']
        return super().get(req, lookup)
