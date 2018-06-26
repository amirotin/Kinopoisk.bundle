from base import SourceBase

class FanArtSource(SourceBase):
    def __init__(self, app):
        super(FanArtSource, self).__init__(app)

    def update(self, metadata, media, lang, force=False, periodic=False):
        self.l('update from FanArtSource')
        json = None
        try:
            json = self.api.JSON.ObjectFromURL(self.c.fanart.movie % metadata['meta_ids'].get('tmdb'), headers=self.c.fanart.headers(''))
        except:
            self.l('No data from FanArt.tv')
            
        if json:
            metadata['fanart'] = dict(background=[], poster=[])
            for key, value in json.items():
                if isinstance(value, list) and key in ('moviebackground', 'movieposter'):
                    for image in value:
                        metadata['fanart'][key.replace('movie', '')].append({
                            'image': image['url'],
                            'thumb': image['url'].replace('/fanart/', '/preview/'),
                            'lang': image['lang'],
                            'likes': image['likes']
                        })