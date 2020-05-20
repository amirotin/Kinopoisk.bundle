from base import SourceBase


class MovieManiaSource(SourceBase):
    def __init__(self, app):
        super(MovieManiaSource, self).__init__(app)

    def update(self, metadata, media, lang, force=False, periodic=False):
        self.l('update from MovieManiaSource')
        if not metadata['meta_ids'].get('tmdb'):
            return
        json = None
        try:
            url = self.conf.base % (self.app.agent_type, metadata['meta_ids'].get('tmdb'))
            req = self.api.HTTP.Request(url)
            if req and req.status_code == 200:
                json = self.api.JSON.ObjectFromString(req.content)
            elif req.status_code == 404:
                self.l('No data from MovieMania.io')
        except Exception, e:
            self.l.Error(e, exc_info=True)

        if json:
            posters = metadata['covers']['mm'] = {}
            for i, poster in enumerate(json.get('posters', []), 1):
                posters[poster['large']] = (poster['preview'], i, None, 0)
