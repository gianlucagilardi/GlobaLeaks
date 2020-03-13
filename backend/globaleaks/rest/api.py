# -*- coding: utf-8
#   API
#   ***
#
#   This file defines the URI mapping for the GlobaLeaks API and its factory

import json
import re

from twisted.internet import defer
from twisted.internet.abstract import isIPAddress, isIPv6Address
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from globaleaks import LANGUAGES_SUPPORTED_CODES
from globaleaks.handlers import custodian, \
                                email_validation, \
                                exception, \
                                file, \
                                receiver, \
                                password_reset, \
                                public, \
                                submission, \
                                rtip, wbtip, \
                                attachment, authentication, token, \
                                export, l10n, wizard,\
                                user, \
                                redirect, \
                                robots, \
                                signup, \
                                site, \
                                sitemap, \
                                staticfile

from globaleaks.handlers.admin import context as admin_context
from globaleaks.handlers.admin import field as admin_field
from globaleaks.handlers.admin import file as admin_file
from globaleaks.handlers.admin import https
from globaleaks.handlers.admin import l10n as admin_l10n
from globaleaks.handlers.admin import manifest as admin_manifest
from globaleaks.handlers.admin import modelimgs as admin_modelimgs
from globaleaks.handlers.admin import node as admin_node
from globaleaks.handlers.admin import notification as admin_notification
from globaleaks.handlers.admin import operation as admin_operation
from globaleaks.handlers.admin import questionnaire as admin_questionnaire
from globaleaks.handlers.admin import redirect as admin_redirect
from globaleaks.handlers.admin import statistics as admin_statistics
from globaleaks.handlers.admin import step as admin_step
from globaleaks.handlers.admin import tenant as admin_tenant
from globaleaks.handlers.admin import user as admin_user
from globaleaks.handlers.admin import submission_statuses as admin_submission_statuses
from globaleaks.rest import decorators, requests, errors
from globaleaks.settings import Settings
from globaleaks.state import State, extract_exception_traceback_and_schedule_email

tid_regexp = r'([0-9]+)'
uuid_regexp = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
key_regexp = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}|[a-z_]{0,100})'

api_spec = [
    (r'/exception', exception.ExceptionHandler),

    # Authentication Handlers
    (r'/authentication', authentication.AuthenticationHandler),
    (r'/tokenauth', authentication.TokenAuthHandler),
    (r'/receiptauth', authentication.ReceiptAuthHandler),
    (r'/session', authentication.SessionHandler),
    (r'/tenantauthswitch/' + tid_regexp, authentication.TenantAuthSwitchHandler),

    # Public API
    (r'/public', public.PublicResource),

    # Sites API
    (r'/sites', site.SiteCollection),

    # User Preferences Handler
    (r'/preferences', user.UserInstance),
    (r'/user/operations', user.UserOperationHandler),

    # Token Handlers
    (r'/token', token.TokenCreate),
    (r'/token/' + requests.token_regexp, token.TokenInstance),

    # Submission Handlers
    (r'/submission/' + requests.token_regexp, submission.SubmissionInstance),
    (r'/submission/' + requests.token_regexp + r'/file', attachment.SubmissionAttachment),

    # Receiver Tip Handlers
    (r'/rtip/' + uuid_regexp, rtip.RTipInstance),
    (r'/rtip/' + uuid_regexp + r'/comments', rtip.RTipCommentCollection),
    (r'/rtip/' + uuid_regexp + r'/messages', rtip.ReceiverMsgCollection),
    (r'/rtip/' + uuid_regexp + r'/identityaccessrequests', rtip.IdentityAccessRequestsCollection),
    (r'/rtip/' + uuid_regexp + r'/export', export.ExportHandler),
    (r'/rtip/' + uuid_regexp + r'/wbfile', rtip.WhistleblowerFileHandler),
    (r'/rtip/rfile/' + uuid_regexp, rtip.ReceiverFileDownload),
    (r'/rtip/wbfile/' + uuid_regexp, rtip.RTipWBFileHandler),

    # Whistleblower Tip Handlers
    (r'/wbtip', wbtip.WBTipInstance),
    (r'/wbtip/comments', wbtip.WBTipCommentCollection),
    (r'/wbtip/messages/' + uuid_regexp, wbtip.WBTipMessageCollection),
    (r'/wbtip/rfile', attachment.PostSubmissionAttachment),
    (r'/wbtip/wbfile/' + uuid_regexp, wbtip.WBTipWBFileHandler),
    (r'/wbtip/' + uuid_regexp + r'/provideidentityinformation', wbtip.WBTipIdentityHandler),
    (r'/wbtip/' + uuid_regexp + r'/update', wbtip.WBTipAdditionalQuestionnaire),

    # Receiver Handlers
    (r'/recipient/reports', receiver.TipsCollection),
    (r'/rtip/operations', receiver.TipsOperations),

    (r'/custodian/identityaccessrequests', custodian.IdentityAccessRequestsCollection),
    (r'/custodian/identityaccessrequest/' + uuid_regexp, custodian.IdentityAccessRequestInstance),

    # Email Validation Handler
    (r'/email/validation/(.+)', email_validation.EmailValidation),

    # Reset Password Handler
    (r'/reset/password', password_reset.PasswordResetHandler),
    (r'/reset/password/(.+)', password_reset.PasswordResetHandler),

    # Admin Handlers
    (r'/admin/node', admin_node.NodeInstance),
    (r'/admin/users', admin_user.UsersCollection),
    (r'/admin/users/' + uuid_regexp, admin_user.UserInstance),
    (r'/admin/contexts', admin_context.ContextsCollection),
    (r'/admin/contexts/' + uuid_regexp, admin_context.ContextInstance),
    (r'/admin/(users|contexts)/' + uuid_regexp + r'/img', admin_modelimgs.ModelImgInstance),
    (r'/admin/questionnaires', admin_questionnaire.QuestionnairesCollection),
    (r'/admin/questionnaires/duplicate', admin_questionnaire.QuestionnareDuplication),
    (r'/admin/questionnaires/' + key_regexp, admin_questionnaire.QuestionnaireInstance),
    (r'/admin/notification', admin_notification.NotificationInstance),
    (r'/admin/fields', admin_field.FieldsCollection),
    (r'/admin/fields/' + key_regexp, admin_field.FieldInstance),
    (r'/admin/steps', admin_step.StepCollection),
    (r'/admin/steps/' + uuid_regexp, admin_step.StepInstance),
    (r'/admin/fieldtemplates', admin_field.FieldTemplatesCollection),
    (r'/admin/fieldtemplates/' + key_regexp, admin_field.FieldTemplateInstance),
    (r'/admin/redirects', admin_redirect.RedirectCollection),
    (r'/admin/redirects/' + uuid_regexp, admin_redirect.RedirectInstance),
    (r'/admin/stats/(\d+)', admin_statistics.StatsCollection),
    (r'/admin/activities/(summary|details)', admin_statistics.RecentEventsCollection),
    (r'/admin/anomalies', admin_statistics.AnomalyCollection),
    (r'/admin/jobs', admin_statistics.JobsTiming),
    (r'/admin/l10n/(' + '|'.join(LANGUAGES_SUPPORTED_CODES) + ')', admin_l10n.AdminL10NHandler),
    (r'/admin/files/(logo|favicon|css|script)', admin_file.FileInstance),
    (r'/admin/config', admin_operation.AdminOperationHandler),
    (r'/admin/config/tls', https.ConfigHandler),
    (r'/admin/config/tls/files/(csr)', https.CSRFileHandler),
    (r'/admin/config/tls/files/(cert|chain|priv_key)', https.FileHandler),
    (r'/admin/files$', admin_file.FileCollection),
    (r'/admin/files/(.+)', admin_file.FileInstance),
    (r'/admin/tenants', admin_tenant.TenantCollection),
    (r'/admin/tenants/' + '([0-9]{1,20})', admin_tenant.TenantInstance),
    (r'/admin/manifest', admin_manifest.ManifestHandler),
    (r'/admin/submission_statuses', admin_submission_statuses.SubmissionStatusCollection),
    (r'/admin/submission_statuses/' + r'(closed)' + r'/substatuses', admin_submission_statuses.SubmissionSubStatusCollection),
    (r'/admin/submission_statuses/' + uuid_regexp, admin_submission_statuses.SubmissionStatusInstance),
    (r'/admin/submission_statuses/' + uuid_regexp + r'/substatuses', admin_submission_statuses.SubmissionSubStatusCollection),
    (r'/admin/submission_statuses/' + r'(closed)' + r'/substatuses/' + uuid_regexp, admin_submission_statuses.SubmissionSubStatusInstance),
    (r'/admin/submission_statuses/' + uuid_regexp + r'/substatuses/' + uuid_regexp, admin_submission_statuses.SubmissionSubStatusInstance),

    (r'/wizard', wizard.Wizard),
    (r'/signup', signup.Signup),
    (r'/signup/([a-zA-Z0-9_\-]{32})', signup.SignupActivation),

    (r'/admin/config/acme/run', https.AcmeHandler),
    (r'/.well-known/acme-challenge/([a-zA-Z0-9_\-]{42,44})', https.AcmeChallengeHandler),

    # Special Files Handlers
    (r'/robots.txt', robots.RobotstxtHandler),
    (r'/sitemap.xml', sitemap.SitemapHandler),
    (r'/s/(.+)', file.FileHandler),
    (r'/l10n/(' + '|'.join(LANGUAGES_SUPPORTED_CODES) + ')', l10n.L10NHandler),

    (r'^(/admin|/login|/submission)$', redirect.SpecialRedirectHandler),

    # This handler attempts to route all non routed get requests
    (r'/([a-zA-Z0-9_\-\/\.\@]*)', staticfile.StaticFileHandler, {'path': Settings.client_path})
]


class APIResourceWrapper(Resource):
    _registry = None
    isLeaf = True
    method_map = {'head': 200, 'get': 200, 'post': 201, 'put': 202, 'delete': 200}

    def __init__(self):
        Resource.__init__(self)
        self._registry = []
        self.handler = None

        for tup in api_spec:
            args = {}
            if len(tup) == 2:
                pattern, handler = tup
            else:
                pattern, handler, args = tup

            if not pattern.startswith("^"):
                pattern = "^" + pattern

            if not pattern.endswith("$"):
                pattern += "$"

            if not hasattr(handler, '_decorated'):
                handler._decorated = True
                for m in ['head', 'get', 'put', 'post', 'delete']:
                    if hasattr(handler, m):
                        decorators.decorate_method(handler, m)

            self._registry.append((re.compile(pattern), handler, args))

    def should_redirect_https(self, request):
        if State.tenant_cache[request.tid].https_enabled and \
           request.client_proto == b'http' and \
           request.client_ip not in Settings.local_hosts:
            return True

        return False

    def should_redirect_tor(self, request):
        if len(State.tenant_cache[request.tid].onionnames) and \
           request.client_using_tor and \
           request.hostname not in [b'127.0.0.1'] + State.tenant_cache[request.tid].onionnames:
            return True

        return False

    def redirect_https(self, request):
        request.redirect(b'https://' + State.tenant_cache[request.tid].hostname.encode() + request.path)

    def redirect_tor(self, request):
        request.redirect(b'http://' + State.tenant_cache[request.tid].onionnames[0] + request.path)

    def handle_exception(self, e, request):
        """
        handle_exception is a callback that decorators all deferreds in render

        It responds to properly handled GL Exceptions by pushing the error msgs
        to the client and it spools a mail in the case the exception is unknown
        and unhandled.

        :param e: A `Twisted.python.Failure` instance that wraps a `GLException`
                  or a normal `Exception`
        :param request: A `twisted.web.Request`
        """
        if isinstance(e, errors.GLException):
            pass
        elif isinstance(e.value, errors.GLException):
            e = e.value
        else:
            e.tid = request.tid
            e.url = request.client_proto + b'://' + request.hostname + request.path
            extract_exception_traceback_and_schedule_email(e)
            e = errors.InternalServerError('Unexpected')

        request.setResponseCode(e.status_code)
        request.setHeader(b'content-type', b'application/json')

        response = json.dumps({
            'error_message': e.reason,
            'error_code': e.error_code,
            'arguments': getattr(e, 'arguments', [])
        })

        request.write(response.encode())

    def preprocess(self, request):
        request.headers = request.getAllHeaders()
        request.hostname = request.getRequestHostname()
        request.port = request.getHost().port

        if (not State.tenant_cache[1].wizard_done or
            request.hostname == b'localhost' or
            isIPAddress(request.hostname) or
            isIPv6Address(request.hostname)):
            request.tid = 1
        else:
            request.tid = State.tenant_hostname_id_map.get(request.hostname, None)

        if request.tid == 1:
            match = re.match(b'^/t/([0-9]+)(/.*)', request.path)
        else:
            match = re.match(b'^/t/(1)(/.*)', request.path)

        if match is not None:
            groups = match.groups()
            tid = int(groups[0])
            if tid in State.tenant_cache:
                request.tid, request.path = tid, groups[1]

        request.client_ip = request.getClientIP()
        request.client_proto = b'https' if request.port in [443, 8443] else b'http'

        request.client_using_tor = request.client_ip in State.tor_exit_set or \
                                   request.port == 8083

        if isinstance(request.client_ip, bytes):
            request.client_ip = request.client_ip.decode()

        if 'x-tor2web' in request.headers:
            request.client_using_tor = False

        request.client_ua = request.headers.get(b'user-agent', b'')

        request.client_mobile = re.match(b'Mobi|Android', request.client_ua, re.IGNORECASE) is not None

        request.language = self.detect_language(request)
        if b'multilang' in request.args:
            request.language = None

    def render(self, request):
        """
        :param request: `twisted.web.Request`

        :return: empty `str` or `NOT_DONE_YET`
        """
        request_finished = [False]

        def _finish(ret):
            request_finished[0] = True

        request.notifyFinish().addBoth(_finish)

        self.preprocess(request)

        if request.tid is None:
            request.tid = 1
            self.set_headers(request)
            request.setResponseCode(400)
            return b''

        self.set_headers(request)

        if self.should_redirect_tor(request):
            self.redirect_tor(request)
            return b''

        if self.should_redirect_https(request):
            self.redirect_https(request)
            return b''

        request_path = request.path.decode()

        if request_path in State.tenant_cache[request.tid]['redirects']:
            request.redirect(State.tenant_cache[request.tid]['redirects'][request_path])
            return b''

        match = None
        for regexp, handler, args in self._registry:
            try:
                match = regexp.match(request_path)
            except UnicodeDecodeError:
                match = None
            if match:
                break

        if match is None:
            self.handle_exception(errors.ResourceNotFound(), request)
            return b''

        method = request.method.lower().decode()

        if method == 'head':
            method = 'get'

        if method not in self.method_map.keys() or not hasattr(handler, method):
            self.handle_exception(errors.MethodNotImplemented(), request)
            return b''

        f = getattr(handler, method)
        groups = match.groups()

        self.handler = handler(State, request, **args)

        request.setResponseCode(self.method_map[method])

        if self.handler.root_tenant_only and request.tid != 1:
            self.handle_exception(errors.ForbiddenOperation(), request)
            return b''

        if self.handler.upload_handler and method == 'post':
            self.handler.process_file_upload()
            if self.handler.uploaded_file is None:
                return b''

        @defer.inlineCallbacks
        def concludeHandlerFailure(err):
            yield self.handler.execution_check()

            self.handle_exception(err, request)

            if not request_finished[0]:
                request.finish()

        @defer.inlineCallbacks
        def concludeHandlerSuccess(ret):
            """
            Concludes successful execution of a `BaseHandler` instance

            :param ret: A `dict`, `list`, `str`, `None` or something unexpected
            """
            yield self.handler.execution_check()

            if not request_finished[0]:
                if ret is not None:
                    if isinstance(ret, (dict, list)):
                        ret = json.dumps(ret, separators=(',', ':'))
                        request.setHeader(b'content-type', b'application/json')

                    if isinstance(ret, str):
                        ret = ret.encode()

                    request.write(ret)

                request.finish()

        defer.maybeDeferred(f, self.handler, *groups).addCallbacks(concludeHandlerSuccess, concludeHandlerFailure)

        return NOT_DONE_YET

    def set_headers(self, request):
        request.setHeader(b'Server', b'Globaleaks')

        if request.client_proto == b'https':
            if State.tenant_cache[request.tid].https_preload:
                request.setHeader(b'Strict-Transport-Security',
                                  b'max-age=31536000; includeSubDomains; preload')
            else:
                request.setHeader(b'Strict-Transport-Security',
                                  b'max-age=31536000; includeSubDomains')

        if Settings.enable_csp:
            csp = "default-src 'none';" \
                  "script-src 'self';" \
                  "connect-src 'self';" \
                  "style-src 'self';" \
                  "img-src 'self' data:;" \
                  "font-src 'self' data:;" \
                  "media-src 'self';"

            if State.tenant_cache[request.tid].frame_ancestors:
                csp += "frame-ancestors " + State.tenant_cache[request.tid].frame_ancestors + ";"
            else:
                csp += "frame-ancestors 'none';"

            request.setHeader(b'Content-Security-Policy', csp)
            request.setHeader(b'X-Frame-Options', b'deny')

            # Disable features that could be used to deanonymize the user
            request.setHeader(b'Feature-Policy', b"camera 'none';"
                                                 b"display-capture 'none';"
                                                 b"document-domain 'none';"
                                                 b"fullscreen 'none';"
                                                 b"geolocation 'none';"
                                                 b"microphone 'none';"
                                                 b"speaker 'none';")

        # Reduce possibility for XSS attacks.
        request.setHeader(b'X-Content-Type-Options', b'nosniff')
        request.setHeader(b'X-XSS-Protection', b'1; mode=block')

        # Disable caching
        request.setHeader(b'Cache-control', b'no-cache, no-store, must-revalidate')
        request.setHeader(b'Pragma', b'no-cache')
        request.setHeader(b'Expires', b'-1')

        # Avoid information leakage via referrer
        request.setHeader(b'Referrer-Policy', b'no-referrer')

        # to avoid Robots spidering, indexing, caching
        if not State.tenant_cache[request.tid].allow_indexing:
            request.setHeader(b'X-Robots-Tag', b'noindex')

        if request.client_using_tor is True:
            request.setHeader(b'X-Check-Tor', b'True')
        else:
            request.setHeader(b'X-Check-Tor', b'False')

        request.setHeader(b'Content-Language', request.language)

    def parse_accept_language_header(self, request):
        if b'accept-language' in request.headers:
            languages = request.headers[b'accept-language'].decode().split(",")
            locales = []
            for language in languages:
                parts = language.strip().split(";")
                if len(parts) > 1 and parts[1].startswith("q="):
                    try:
                        score = float(parts[1][2:])
                    except (ValueError, TypeError):
                        score = 0.0
                else:
                    score = 1.0
                locales.append((parts[0], score))

            if locales:
                locales.sort(key=lambda pair: pair[1], reverse=True)
                return [l[0] for l in locales]

        return State.tenant_cache[request.tid].default_language

    def detect_language(self, request):
        if request.tid is None:
            return 'en'

        language = request.headers.get(b'gl-language')
        if language is None:
            for l in self.parse_accept_language_header(request):
                if l in State.tenant_cache[request.tid].languages_enabled:
                    language = l
                    break
        else:
            language = language.decode()

        if language is None or language not in State.tenant_cache[request.tid].languages_enabled:
            language = State.tenant_cache[request.tid].default_language

        return language
