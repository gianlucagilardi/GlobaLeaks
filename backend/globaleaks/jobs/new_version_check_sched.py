# -*- encoding: utf-8 -*-
from debian import deb822
from distutils.version import StrictVersion as v

from twisted.internet.defer import inlineCallbacks

from globaleaks.settings import GLSettings
from globaleaks.jobs.base import LoopingJob
from globaleaks.utils.agent import get_page


class NewVerCheckJob(LoopingJob):
    name = "New Version Check"
    interval = 60*60*24

    def operation(self):
        self._operation()

    @inlineCallbacks
    def _operation(self):
        net_agent = GLSettings.get_agent()

        r = yield get_page(net_agent, 'https://deb.globaleaks.org/xenial/Packages')
        packages = []
        for package in deb822.Deb822.iter_paragraphs(r):
            packages.append(package)

        vers = [v(p['Version']) for p in packages]
        new = sorted(packages, key=lambda x: v(x['Version']), reverse=True)

        GLSettings.state.latest_version = v(new[0]['Version'])
