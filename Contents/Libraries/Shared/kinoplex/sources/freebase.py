from base import SourceBase

class FreebaseSource(SourceBase):
    def __init__(self, app):
        super(FreebaseSource, self).__init__(app)
        self.continue_search = False
        
    def update(self, metadata, media, lang, force=False, periodic=False):
        self.l('update from FreebaseSource')
        freebase = self._fetch_xml(self.c.freebase.base % (self.get_source_id('imdb')[2:], lang))

        TYPE_MAP = {'primary_trailer': self.api.TrailerObject,
                    'trailer': self.api.TrailerObject,
                    'interview': self.api.InterviewObject,
                    'behind_the_scenes': self.api.BehindTheScenesObject,
                    'scene_or_sample': self.api.SceneOrSampleObject}

        extras = []
        if freebase:
            self.l('Parsing IVA extras')
            for extra in freebase.xpath('//extra'):
                avail = self.api.Datetime.ParseDate(extra.get('originally_available_at'))
                lang_code = int(extra.get('lang_code')) if extra.get('lang_code') else -1
                subtitle_lang_code = int(extra.get('subtitle_lang_code')) if extra.get('subtitle_lang_code') else -1
                include = True
                
                # Exclude non-primary trailers and scenes.
                extra_type = 'primary_trailer' if extra.get('primary') == 'true' else extra.get('type')
                if extra_type == 'trailer' or extra_type == 'scene_or_sample':
                    include = False

                # Don't include anything besides trailers if pref is set.
                #if extra_type != 'primary_trailer' and Prefs['only_trailers']:
                #    include = False

                if include:

                    bitrates = extra.get('bitrates') or ''
                    duration = int(extra.get('duration') or 0)
                    adaptive = 1 if extra.get('adaptive') == 'true' else 0
                    dts = 1 if extra.get('dts') == 'true' else 0

                    # Remember the title if this is the primary trailer.
                    if extra_type == 'primary_trailer':
                        media_title = extra.get('title')

                    if extra_type in TYPE_MAP:
                        extras.append({ 'type' : extra_type,
                                        'lang' : 0,
                                        'extra' : TYPE_MAP[extra_type](url=self.c.freebase.assets % (extra.get('iva_id'), 0, bitrates, duration, adaptive, dts),
                                                                    title=extra.get('title'),
                                                                    year=avail.year,
                                                                    originally_available_at=avail,
                                                                    thumb=extra.get('thumb') or '')})
        metadata['iva_extras'] = extras

        try:
            # Ratings.
            if freebase.xpath('rating') is not None:

                rating_image_identifiers = {
                    'Certified Fresh': 'rottentomatoes://image.rating.certified',
                    'Fresh': 'rottentomatoes://image.rating.ripe',
                    'Ripe': 'rottentomatoes://image.rating.ripe',
                    'Rotten': 'rottentomatoes://image.rating.rotten',
                    None: ''
                }
                audience_rating_image_identifiers = {
                    'Upright': 'rottentomatoes://image.rating.upright',
                    'Spilled': 'rottentomatoes://image.rating.spilled',
                    None: ''
                }

                ratings = freebase.xpath('//ratings')
                rt_ratings = metadata['rt_raings'] = {}
                if ratings:
                    ratings = ratings[0]
                    try:
                        rt_ratings['rating'] = float(ratings.get('critics_score', 0.0)) / 10
                    except TypeError:
                        rt_ratings['rating'] = 0.0

                    try:
                        rt_ratings['audience_rating'] = float(ratings.get('audience_score', 0.0)) / 10
                    except:
                        rt_ratings['audience_rating'] = 0.0

                    try:
                        rt_ratings['rating_image'] = rating_image_identifiers[ratings.get('critics_rating', None)]
                    except KeyError:
                        rt_ratings['rating_image'] = ''

                    try:
                        rt_ratings['audience_rating_image'] = audience_rating_image_identifiers[ratings.get('audience_rating', None)]
                    except KeyError:
                        rt_ratings['audience_rating_image'] = ''

            metadata['rotten_reviews'] = []
            for review in freebase.xpath('//review'):
                if review.text not in [None, False, '']:
                    metadata['rotten_reviews'].append({
                        'author': review.get('critic'),
                        'source': review.get('publication'),
                        'image': 'rottentomatoes://image.review.fresh' if review.get('freshness') == 'fresh' else 'rottentomatoes://image.review.rotten',
                        'link': review.get('link'),
                        'text': review.text
                    })
        except Exception, e:
            self.l('Error obtaining Rotten tomato data for %s: %s' % (self.get_source_id('imdb'), str(e)))