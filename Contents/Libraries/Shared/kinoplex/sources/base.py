# -*- coding: utf-8 -*-
def memoize(f):
    """ Memoization decorator for a function taking a single argument """
    class memodict(dict):
        def __missing__(self, key):
            ret = f(key)
            if ret: self[key] = ret
            return ret
    return memodict().__getitem__

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

    @property
    def meta_id(self):
        return str(self.app.meta_id)

    @meta_id.setter
    def meta_id(self, value):
        self.app.meta_id = str(value)

    @property
    @memoize
    def source_id(self):
        return self.get_source_id(self.source_name)

    @source_id.setter
    def source_id(self, value):
        self.set_source_id(self.source_name, value)

    def get_source_id(self, source_name):
        self.l('get id for %s', source_name)
        if self.api.Data.Exists(self.meta_id):
            ids = self.api.Data.LoadObject(self.meta_id)
            if isinstance(ids, dict) and source_name in ids:
                return ids[source_name]
        return None

    def set_source_id(self, source_name, source_id):
        self.l('set id for %s', source_name)
        if self.api.Data.Exists(self.meta_id) is False:
            self.api.Data.SaveObject(self.meta_id, {source_name: source_id})
        else:
            ids = self.api.Data.LoadObject(self.meta_id)
            ids[source_name] = source_id
            self.api.Data.SaveObject(self.meta_id, ids)

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
        #self.l.Debug('json = %s', json)
        return json

    def _fetch_xml(self, url, headers={'Accept-Encoding':'gzip'}):
        xml = {}
        try:
            xml = self.api.XML.ElementFromURL(url, headers=headers)
        except:
            self.l.Error('Something goes wrong with request', exc_info=True)
        #self.l.Debug('xml = %s', self.api.XML.StringFromElement(xml))
        return xml