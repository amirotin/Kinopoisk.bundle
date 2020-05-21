# -*- coding: utf-8 -*-
import os, time, logging, urllib, sentry_sdk, socket

from sentry_sdk.integrations.logging import LoggingIntegration
from requests import Session, Response, exceptions
from requests.adapters import HTTPAdapter
from requests.structures import CaseInsensitiveDict
from requests.utils import get_encoding_from_headers
from requests.cookies import extract_cookies_to_jar
from requests.packages.urllib3.util.retry import Retry

from sentry_sdk import configure_scope

from kinoplex.const import config, tree
from kinoplex.agent import KinoPlex
from kinoplex.meta import prepare_meta

from collections import namedtuple
from datetime import datetime
from types import MethodType

TRACE_LEVEL_NUM = 15
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")


class PlexResponse(Response):
    def __str__(self):
        return self.content

class PlexHTTPAdapter(HTTPAdapter):
    def build_response(self, req, resp):
        response = PlexResponse()
        response.status_code = getattr(resp, 'status', None)
        response.headers = CaseInsensitiveDict(getattr(resp, 'headers', {}))
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason
        if isinstance(req.url, bytes):
            response.url = req.url.decode('utf-8')
        else:
            response.url = req.url
        extract_cookies_to_jar(response.cookies, req, resp)
        response.request = req
        response.connection = self
        return response


def getVersionInfo(core):
    from kinoplex import __version__
    branch = str(__version__[-1]).upper()
    version = '.'.join(str(i) for i in __version__[:-1])
    current_version = '%s-v%s' % (branch, version)
    current_mtime = 0
    version_path = core.storage.join_path(core.bundle_path, 'Contents', 'VERSION')
    if core.storage.file_exists(version_path):
        current_version = core.storage.load(version_path)
        current_mtime = core.storage.last_modified(version_path)
    return current_version, current_mtime


# implement http_request using requests
def requests_http_request(self, url, values=None, headers={}, cacheTime=None, encoding=None, errors=None, timeout=0, immediate=False, sleep=0, data=None, opener=None, sandbox=None, follow_redirects=True, basic_auth=None, method=None):
    def _content_type_allowed(content_type):
        for t in ['html', 'xml', 'json', 'javascript']:
            if t in content_type:
                return True
        return False

    if cacheTime == None: cacheTime = self.cache_time
    pos = url.rfind('#')
    if pos > 0:
        url = url[:pos]

    if values and not data:
        data = urllib.urlencode(values)

    if data:
        cacheTime = 0
        immediate = True

    url_cache = None
    if self._http_caching_enabled:
        if cacheTime > 0:
            cache_mgr = self._cache_mgr
            if cache_mgr.item_count > self._core.config.http_cache_max_items + self._core.config.http_cache_max_items_grace:
                cache_mgr.trim(self._core.config.http_cache_max_size, self._core.config.http_cache_max_items)
            url_cache = cache_mgr[url]
            url_cache.set_expiry_interval(cacheTime)
        else:
            del self._cache_mgr[url]

    if url_cache != None and url_cache['content'] and not url_cache.expired:
        content_type = url_cache.headers.get('Content-Type', '')
        if self._core.plugin_class == 'Agent' and not _content_type_allowed(content_type):
            self._core.log.debug("Removing cached data for '%s' (content type '%s' not cacheable in Agent plug-ins)", url, content_type)
            manager = url_cache._manager
            del manager[url]
        else:
            self._core.log.debug("Fetching '%s' from the HTTP cache", url)
            res = PlexResponse()
            res.content = url_cache['content']
            res.headers = url_cache.headers
            return res

    h = dict(self.default_headers)
    h.update({'connection': 'keep-alive'})
    if sandbox:
        h.update(sandbox.custom_headers)
    h.update(headers)

    self._core.log.debug("Requesting '%s'", url)

    if 'PLEXTOKEN' in os.environ and len(os.environ['PLEXTOKEN']) > 0 and h is not None and url.find('http://127.0.0.1') == 0:
        h['X-Plex-Token'] = os.environ['PLEXTOKEN']

    if basic_auth != None:
        h['Authorization'] = self.generate_basic_auth_header(*basic_auth)

    if url.startswith(config.kinopoisk.api.base[:-2]):
        h.update({'clientDate': datetime.now().strftime("%H:%M %d.%m.%Y"), 'x-timestamp': str(int(round(time.time() * 1000)))})
        h.update({'x-signature': self._core.data.hashing.md5(url[len(config.kinopoisk.api.base[:-2]):]+h.get('x-timestamp')+config.kinopoisk.api.hash)})

    req = None
    try:
        req = self.session.request(method or 'GET', url, headers=h, allow_redirects=follow_redirects, data=data)
    except exceptions.RequestException as e:
        self._core.log.error("Failed request %s: %s", url, e)

    if url_cache != None:
        content_type = req.headers.get('Content-Type', '')
        if self._core.plugin_class == 'Agent' and not _content_type_allowed(content_type):
            self._core.log.debug("Not caching '%s' (content type '%s' not cacheable in Agent plug-ins)", url, content_type)
        else:
            url_cache['content'] = req.data
            url_cache.headers = dict(req.headers)
    return req


def setup_sentry(core, platform, prefs):
    core.log.debug('sentry install')
    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )

    def before_send(event, hint):
        if 'exc_info' in hint:
            exc_type, exc_value, tb = hint['exc_info']
            if exc_type == socket.error:
                return None

        if 'location' in event and event.get('location', '').startswith('tornado'):
            return None

        message = event.get('message') or event.get('logentry', {}).get('message')
        if message and message.startswith((
            'Cannot read model from',
            'Unable to deserialize object at',
            'Exception when constructing media object',
            "Exception in thread named '_handle_request'",
            'Exception in I/O handler for fd %d',
            'We seem to be missing the hash for media item',
        )):
            return None

        core.log.debug('sentry error event = %s, hint = %s', event, hint)
        return event

    # Если включено автообновление и источник указан как amirotin, то все ошибки отправляем в проект KinoPlex AutoUpdate
    if prefs['update_channel'] != 'none' and prefs['update_repo'] == "amirotin":
        dsn = "https://2904103227024e22adb745fc6b56332e@sentry.letsnova.ru/3"
    # Иначе отправляем в проект KinoPlex Legacy
    else:
        dsn = "https://93cb49b9aac14aa181b1cb5210ee6cf1@sentry.letsnova.ru/4"

    sentry_sdk.init(
        dsn=dsn,
        integrations=[sentry_logging],
        environment='develop',
        before_send=before_send
    )

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag('os', platform.OS,)
        scope.set_tag('plexname', core.get_server_attribute('friendlyName'))
        scope.set_tag('osversion', platform.OSVersion)
        scope.set_tag('cpu', platform.CPU)
        scope.set_tag('serverversion', platform.ServerVersion)
        scope.set_tag('pluginversion', getVersionInfo(core)[0])
        scope.user = {'id': platform.MachineIdentifier}


def setup_network(core, prefs):
    core.log.debug('requests install')
    core.networking.session = Session()
    retry = Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=0.5,
        status_forcelist=(500, 502, 504),
    )
    core.networking.session.mount('https://', PlexHTTPAdapter(max_retries=retry))
    core.networking.session.mount('http://', PlexHTTPAdapter(max_retries=retry))
    core.networking.http_request = MethodType(requests_http_request, core.networking)


def search_event(self, results, media, lang, manual=False, version=0, primary=True):
    with configure_scope() as scope:
        scope.set_extra("media", media.__dict__)
    try:
        self.quick_search(results, media, lang, manual, primary)
        self.fire('search', results, media, lang, manual, primary)
    except Exception, e:
        self.api.Log.Error(e, exc_info=True)


def update_event(self, metadata, media, lang, force=False, version=0, periodic=False):
    with configure_scope() as scope:
        scope.set_extra("media", media.__dict__)
    try:
        ids = {}
        if self.api.Data.Exists(media.id):
            ids = self.api.Data.LoadObject(media.id)
            if not ids.get('kp'):
                ids['kp'] = metadata.id
        metadict = dict(id=metadata.id, meta_ids=ids, ratings={}, reviews={}, covers={}, backdrops={}, clips={}, seasons=tree())
        self.fire('update', metadict, media, lang, force, periodic)
        prepare_meta(metadict, metadata, self)
        self.api.Data.SaveObject(media.id, metadict['meta_ids'])
    except Exception, e:
        self.api.Log.Error(e, exc_info=True)


def log_trace(self, message, *args):
    if self.api.Prefs['trace']:
        self.api.Core.log.log(TRACE_LEVEL_NUM, message, *args)


def init_class(cls_name, cls_base, gl, version=0):
    g = dict((k, v) for k, v in gl.items() if not k.startswith("_"))
    d = {
        'name': u'Кинопоиск 2.0',
        'api': namedtuple('Struct', g.keys())(*g.values()),
        'agent_type': 'movie' if cls_base.__name__ == 'Movies' else 'tv',
        'primary_provider': True,
        'languages': ['ru', 'en'],
        'accepts_from': ['com.plexapp.agents.localmedia'],
        'contributes_to': config.get('contrib', {}).get(cls_base.__name__,[]),
        'c': config,
        'trace': log_trace,
        'search': search_event,
        'update': update_event,
        'version': version
    }
    return d.get('__metaclass__', type)(cls_name, (KinoPlex, cls_base,), d)