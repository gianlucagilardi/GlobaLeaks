# -*- coding: utf-8 -*-
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import robots
from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.tests import helpers


class TestRobotstxtHandlerHandler(helpers.TestHandler):
    _handler = robots.RobotstxtHandler

    @inlineCallbacks
    def test_get_with_indexing_disabled(self):
        handler = self.request()

        State.tenant_cache[1].allow_indexing = False

        response = yield handler.get()

        self.assertEqual(response, "User-agent: *\n"
                                   "Disallow: *")

    @inlineCallbacks
    def test_get_with_indexing_enabled(self):
        handler = self.request()

        State.tenant_cache[1].allow_indexing = True
        State.tenant_cache[1].hostname = "www.globaleaks.org"

        response = yield handler.get()

        self.assertEqual(response, "User-agent: *\n"
                                   "Allow: /$\n"
                                   "Disallow: *\n"
                                   "Sitemap: https://www.globaleaks.org/sitemap.xml")
