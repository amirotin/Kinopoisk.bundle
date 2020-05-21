from base import SourceBase


class FanArtSource(SourceBase):
    def __init__(self, app):
        super(FanArtSource, self).__init__(app)

    def update(self, metadata, media, lang, force=False, periodic=False):
        self.l('update from FanArtSource')
        if not metadata['meta_ids'].get('tmdb'):
            return
        json = None
        try:
            json = self.api.JSON.ObjectFromURL(self.conf.movie % metadata['meta_ids'].get('tmdb'), headers=self.conf.headers(''))
        except:
            self.l.Debug('No data from FanArt.tv')

        if json:
            for key, value in json.items():
                if isinstance(value, list) and key in ('moviebackground', 'movieposter'):
                    images = metadata[{'moviebackground': 'backdrops', 'movieposter': 'covers'}[key]]['fanart'] = {}
                    for i, image in enumerate(value, 1):
                        images[image['url']] = (
                            image['url'].replace('/fanart/', '/preview/'),
                            i,
                            image['lang'],
                            image['likes']
                        )
