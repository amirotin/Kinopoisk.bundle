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
            json = self.api.JSON.ObjectFromURL(self.conf.base % (self.app.agent_type, metadata['meta_ids'].get('tmdb')))
        except:
            self.l('No data from MovieMania.io')

        if json:
            posters = metadata['covers']['mm'] = {}
            for i, poster in enumerate(json.get('posters', []), 1):
                posters[poster['large']] = (poster['preview'], i, None, 0)
