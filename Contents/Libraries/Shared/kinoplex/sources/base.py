# -*- coding: utf-8 -*-
class SourceBase(object):
    def __init__(self, app):
        self.app = app
        self.api = app.api
        self.l = app.api.Log
        self.c = app.c
        self.source_name = type(self).__name__.replace('Source','').lower()
        self.l('Source "%s" inited', self.source_name)

    @classmethod
    def getAll(cls, *args, **kwargs):
        return [subclass for subclass in cls.__subclasses__()]

    def get_source_id(self, meta_id, source_name=None):
        if not source_name:
            source_name = self.source_name
        self.l('get id for %s', source_name)
        if self.api.Data.Exists(meta_id):
            ids = self.api.Data.LoadObject(meta_id)
            if isinstance(ids, dict) and source_name in ids:
                return ids[source_name]
        return None

    def set_source_id(self, source_id, meta_id, source_name=None):
        if not source_name:
            source_name = self.source_name
        self.l('set id for %s', source_name)
        if self.api.Data.Exists(meta_id) is False:
            self.api.Data.SaveObject(meta_id, {source_name: source_id})
        else:
            ids = self.api.Data.LoadObject(meta_id)
            ids[source_name] = source_id
            self.api.Data.SaveObject(meta_id, ids)
        return source_id

    def search(self, results, media, lang, manual=False, primary=True):
        pass

    def _fetch_json(self, url, headers={'Accept-Encoding':'gzip'}):
        json = {}
        try:
            json = self.api.JSON.ObjectFromURL(url, headers=headers)
        except:
            self.l.Error('Something goes wrong with request', exc_info=True)
        if isinstance(json, dict) and json.get('captcha', {}):
            self.l.Warn('Request returned captcha validation')
            return {}
        return json

    def _fetch_xml(self, url, headers={'Accept-Encoding':'gzip'}):
        xml = {}
        try:
            xml = self.api.XML.ElementFromURL(url, headers=headers)
        except:
            self.l.Error('Something goes wrong with request', exc_info=True)
        return xml