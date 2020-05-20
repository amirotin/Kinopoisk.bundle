from base import SourceBase

import re

class FreebaseSource(SourceBase):
    def __init__(self, app):
        super(FreebaseSource, self).__init__(app)

    def scrub_extra(self, extra, media_title):

        e = extra['extra']

        # Remove the "Movie Title: " from non-trailer extra titles.
        if media_title is not None:
            r = re.compile(media_title + ': ', re.IGNORECASE)
            e.title = r.sub('', e.title)

        # Remove the "Movie Title Scene: " from SceneOrSample extra titles.
        if media_title is not None:
            r = re.compile(media_title + ' Scene: ', re.IGNORECASE)
            e.title = r.sub('', e.title)

        # Capitalise UK correctly.
        e.title = e.title.replace('Uk', 'UK')

        return extra

    def update(self, metadata, media, lang, force=False, periodic=False):
        self.l('update from FreebaseSource')
        freebase = None
        media_title = None
        TYPE_MAP = {'primary_trailer': self.api.TrailerObject,
                    'trailer': self.api.TrailerObject,
                    'interview': self.api.InterviewObject,
                    'behind_the_scenes': self.api.BehindTheScenesObject,
                    'scene_or_sample': self.api.SceneOrSampleObject}

        if metadata['meta_ids'].get('imdb'):
            freebase = self._fetch_xml(self.conf.base % (metadata['meta_ids'].get('imdb')[2:], lang))

        if freebase is not None and len(freebase):
            extras = []
            self.l('Parsing IVA extras')
            for extra in freebase.xpath('//extra'):
                avail = self.api.Datetime.ParseDate(extra.get('originally_available_at'))
                extra_type = 'primary_trailer' if extra.get('primary') == 'true' else extra.get('type')
                bitrates = extra.get('bitrates') or ''
                duration = int(extra.get('duration') or 0)
                adaptive = 1 if extra.get('adaptive') == 'true' else 0
                dts = 1 if extra.get('dts') == 'true' else 0

                if extra_type == 'primary_trailer':
                    media_title = extra.get('title')

                if extra_type in TYPE_MAP:
                    extras.append({ 'type' : extra_type,
                                    'lang' : 0,
                                    'extra' : TYPE_MAP[extra_type](url=self.conf.assets % (extra.get('iva_id'), 0, bitrates, duration, adaptive, dts),
                                                                   title=extra.get('title'),
                                                                   year=avail.year,
                                                                   originally_available_at=avail,
                                                                   thumb=extra.get('thumb') or '')})

            metadata['clips']['iva'] = [self.scrub_extra(extra, media_title) for extra in extras]

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
                    rt_ratings = metadata['ratings']['rt'] = {}
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

                reviews = metadata['reviews']['rt'] = []
                for review in freebase.xpath('//review'):
                    if review.text not in [None, False, '']:
                        reviews.append({
                            'author': review.get('critic'),
                            'source': review.get('publication'),
                            'image': 'rottentomatoes://image.review.fresh' if review.get('freshness') == 'fresh' else 'rottentomatoes://image.review.rotten',
                            'link': review.get('link'),
                            'text': review.text
                        })
                del reviews
            except Exception, e:
                self.l('Error obtaining Rotten tomato data for %s: %s' % (metadata['meta_ids'].get('imdb'), str(e)))