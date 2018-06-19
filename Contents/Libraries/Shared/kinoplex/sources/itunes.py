from base import SourceBase
from urlparse import parse_qs, urlparse
import re

class ITunesSource(SourceBase):
    def __init__(self, app):
        super(ITunesSource, self).__init__(app)
        self.continue_search = False

    def _search(self, metadata):
        self.l('search from ITunesSource')

        # check trakt.tv for itunes link
        try:
            # get trakt url by imdb id
            trakt_url = self.api.HTTP.Request(url=self.c.itunes.trakt_imdb % self.get_source_id('imdb'), method='HEAD', follow_redirects=False)
            # load trakt streaming page for movie
            trakt_page = self.api.HTML.ElementFromURL(self.c.itunes.trakt_streaming % trakt_url.headers.get('location'), headers=self.c.headers.all, cacheTime=0)
            if trakt_page:
                # search for itunes link
                lnk = trakt_page.xpath(self.c.itunes.trakt_re)
                if len(lnk) > 0:
                    # fetch itunes store link from trakt
                    itunes_lnk = self.api.HTTP.Request(url=self.c.itunes.trakt_base % lnk[0], method='HEAD', follow_redirects=False)
                    # parse for id in url
                    id = re.search('(?<=id)[0-9]+', itunes_lnk.headers.get('location')).group(0)
                    return id
        except:
            self.l('No itunes link on trakt.tv page')

        # fast way - check rotten tomatoes
        try:
            omdb = self.api.JSON.ObjectFromURL(self.c.itunes.omdb % self.get_source_id('imdb'))
            if 'tomatoURL' in omdb and omdb['tomatoURL'] != 'N/A':
                page = self.api.HTML.ElementFromURL(omdb['tomatoURL'].replace('http://','https://'), headers=self.c.headers.all, cacheTime=0)
                lnk = page.xpath(self.c.itunes.rt_re)
                if len(lnk) > 0:
                    return re.search('(?<=id)[0-9]+', lnk[0]).group(0)
        except:
            self.l('No itunes link on rottentomatoes')

        # search fan.tv for itunes link
        try:
            page = self.api.HTML.ElementFromURL(self.c.itunes.fantv % self.get_source_id('tmdb'), headers=self.c.headers.all, cacheTime=0)
            lnk = page.xpath(self.c.itunes.fantv_re)
            if len(lnk) > 0:
                params = parse_qs(urlparse(lnk[0]).query)
                if 'id' in params and len(params['id']) > 0:
                    return params['id'][0]
        except:
            self.l('No itunes link on fan.tv page')

        return None

    def update(self, metadata, media, lang, force=False, periodic=False):
        self.l('itunes id = %s',self.source_id)
        if self.source_id is None:
            self.source_id = self._search(metadata)

        self.l('update from ITunesSource')
        if self.source_id:
            movie_data = self.api.JSON.ObjectFromURL(self.c.itunes.lookup % self.source_id)
            if 'resultCount' in movie_data and movie_data['resultCount'] > 0:
                self.l('### iTunes selected title %s', movie_data['results'][0]['trackName'])
                poster_url = movie_data['results'][0]['artworkUrl100'].replace('100x100bb', self.c.itunes.poster)
                thumb_url = movie_data['results'][0]['artworkUrl100'].replace('100x100bb', self.c.itunes.preview)
                metadata['itunes_poster'] = {
                    'poster_url': poster_url,
                    'thumb_url': thumb_url,
                }
