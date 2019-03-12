# -*- coding: utf-8 -*-
from base import SourceBase


class TVDBSource(SourceBase):
    def __init__(self, app):
        super(TVDBSource, self).__init__(app)
        self.jwt = ''

    def get_jwt(self):
        token_data = self.api.JSON.ObjectFromString(self.api.HTTP.Request(
            self.conf.login,
            method='POST',
            data=self.api.JSON.StringFromObject({
                "apikey": "73E00122B158ADF4"}),
            headers={'Content-type': 'application/json'}
        ).content)
        if 'token' in token_data:
            self.jwt = token_data['token']

    def make_request(self, link, lang, *args):
        if not self.jwt:
            self.get_jwt()

        data = {}
        try:
            data = self.api.JSON.ObjectFromURL(
                link % args, headers={
                    'Authorization': 'Bearer %s' % self.jwt,
                    'Accept-Language': lang,
                    'Accept': 'application/json'
                })
        except:
            self.l.Error('Something goes wrong with request', exc_info=True)
        return data

    def _search(self, metadata, media, lang):
        pass

    def update(self, metadata, media, lang, force=False, periodic=False):
        if self.app.agent_type == 'movie':
            return
        self.l('update from TVDBSource')
        source_id = metadata['meta_ids'].get(self.source_name)
        if not source_id:
            source_id = metadata['meta_ids'][self.source_name] = self._search(metadata, media, lang)

        series_resp = self.make_request(self.conf.series, lang, source_id)

        if 'errors' in series_resp and series_resp['errors'].get('invalidLanguage') and lang != 'en':
            series_resp = self.make_request(self.conf.series, 'en', source_id)

        series_data = series_resp.get('data', {})
        if not series_data:
            self.l('no data for tv serie %s' % source_id)
            return

        episodes_data = []
        next_page = 1
        while isinstance(next_page, int) or (isinstance(next_page, basestring) and next_page.isdigit()):
            next_page = int(next_page)
            episode_data_page = self.make_request(self.conf.episodes, lang, source_id, next_page)
            episodes_data.extend(episode_data_page['data'])
            next_page = episode_data_page['links']['next']

