# -*- coding: utf-8 -*-
class SourceBase(object):
    def __init__(self, app):
        self.app = app
        self.api = app.api
        self.l = app.api.Log
        self.c = app.c
        self.source_name = type(self).__name__.replace('Source', '').lower()
        self.conf = self.c[self.source_name]
        self.d('Source "%s" inited', self.source_name)

    @classmethod
    def getAll(cls, *args, **kwargs):
        return [subclass for subclass in cls.__subclasses__()]

    def d(self, *args):
        if self.api.Prefs['trace']:
            args = list(args)
            args[0] = '#### %s' % args[0]
            self.app.trace(*args)

    def search(self, results, media, lang, manual=False, primary=True):
        pass

    def _fetch_json(self, url, headers={'Accept-Encoding': 'gzip'}):
        json = {}
        try:
            req = self.api.HTTP.Request(url, headers=headers)
            if req.status_code == 200:
                json = self.api.JSON.ObjectFromString(req.content)
        except Exception:
            self.l.Error('Something goes wrong with request', exc_info=True)
        if isinstance(json, dict) and json.get('captcha', {}):
            self.l.Warn('Request returned captcha validation')
            return {}
        return json

    def _fetch_xml(self, url, headers={'Accept-Encoding': 'gzip'}):
        xml = {}
        try:
            xml = self.api.XML.ElementFromURL(url, headers=headers)
        except Exception:
            self.l.Error('Something goes wrong with request', exc_info=True)
        return xml