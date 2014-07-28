#!/usr/bin/env python
# Copyright (c) 2014 VMware, Inc. All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import traceback
import webob
import webob.dec

from congress.api.webservice import INTERNAL_ERROR_RESPONSE
from congress.api.webservice import NOT_SUPPORTED_RESPONSE
from congress.openstack.common.gettextutils import _
from congress.openstack.common import log as logging


LOG = logging.getLogger(__name__)


class ApiApplication(object):
    """An API web application that binds REST resources to a wsgi server.

    This indirection between the wsgi server and REST resources facilitates
    binding the same resource tree to multiple endpoints (e.g. HTTP/HTTPS).
    """

    def __init__(self, resource_mgr):
        self.resource_mgr = resource_mgr

    @webob.dec.wsgify(RequestClass=webob.Request)
    def __call__(self, request):
        try:
            handler = self.resource_mgr.get_handler(request)
            if handler:
                msg = _("Handling request '%(meth)s %(path)s' with %(hndlr)s")
                LOG.debug(msg % {"meth": request.method, "path": request.path,
                                 "hndlr": str(handler)})
                response = handler.handle_request(request)
            else:
                response = NOT_SUPPORTED_RESPONSE
        except Exception as e:
            msg = _("Exception caught for request: %s")
            LOG.error(msg % (request))
            LOG.error(traceback.format_exc(e))
            response = INTERNAL_ERROR_RESPONSE
        return response


class ResourceManager(object):
    """A container for REST API resources and underlying data models.

    This container is meant to be called from one or more wsgi servers/ports.

    Attributes:
        handlers: An array of API resource handlers for registered resources.
        models: A dict of {model_id: data_model} for registered data models.
    """

    def __init__(self):
        self.handlers = []
        self.models = {}

    def register_handler(self, handler, search_index=None):
        """Register a new resource handler.

        Args:
            handler: The resource handler to register.
            search_index: Priority of resource handler to resolve cases where
                a request matches multiple handlers.
        """
        if search_index is not None:
            self.handlers.insert(search_index, handler)
        else:
            self.handlers.append(handler)
        msg = _("Registered API handler: %s") % (handler)
        LOG.info(msg)

    def get_handler(self, request):
        """Find a handler for a REST request.

        Args:
           request: A webob request object.

        Returns:
            A handler instance or None.
        """
        for h in self.handlers:
            if h.handles_request(request):
                return h
        return None

    def register_model(self, model_id, model):
        """Register a data model.

        Args:
            model_id: A unique ID for the model.
            model: The model to register.
        """
        if model_id in self.models:
            raise KeyError("Model '%s' already registered" % model_id)
        self.models[model_id] = model

    def get_model(self, model_id):
        return self.models.get(model_id)