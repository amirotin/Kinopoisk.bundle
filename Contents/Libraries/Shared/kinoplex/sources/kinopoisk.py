# -*- coding: utf-8 -*-
from base import SourceBase

import re


class KinopoiskSource(SourceBase):
    def __init__(self, app):
        super(KinopoiskSource, self).__init__(app)
        self.continue_search = True

    def get_name(self, media):
        return self.api.String.Quote(media.name if self.app.agent_type == 'movies' else media.show, False)

    def _plus_search(self, matches, media):
        json = self._fetch_json(
            self.c.kinopoisk.plus.search % (
                'films' if self.app.agent_type == 'movies' else 'series', self.get_name(media)),
            headers=self.c.kinopoisk.plus.headers
        )
        json = json.get('state', {}).get('movies', {})
        cnt = 0
        if json:
            for i, movie in enumerate(
                    sorted(json.values(), key=lambda k: k['ratingData'].get('rating', {}).get('votes', 0),
                           reverse=True)):
                if {'originalTitle', 'title', 'year'} <= set(movie) and int(
                        movie['year'][:4]) <= self.api.Datetime.Now().year:
                    matches[str(movie['id'])] = [movie['title'], movie['originalTitle'], int(movie['year']), i, 0]
                    cnt = cnt + 1
        return cnt

    def _suggest_search(self, matches, media):
        json = self._fetch_json(
            self.c.kinopoisk.main.yasearch % self.get_name(media),
            headers=self.c.kinopoisk.main.headers
        )
        json = json[2] if 2 <= len(json) else []
        cnt = 0
        if json:
            ftype = 'MOVIE' if self.app.agent_type == 'movies' else 'SHOW'
            for i, movie in enumerate(
                    sorted(
                        filter(lambda z: z.get('type', '') == ftype and z.get('title'),
                               map(lambda x: self.api.JSON.ObjectFromString(x), json)),
                        key=lambda k: k.get('rating', {}).get('votes', 0), reverse=True)):
                if {'originalTitle', 'title', 'years'} <= set(movie) \
                        and (len(movie['years']) == 1 and movie['years'][0] <= self.api.Datetime.Now().year):
                    matches[str(movie['entityId'])] = [movie['title'], movie['originalTitle'], movie['years'][0], i, 0]
                cnt = cnt + 1
        return cnt

    def _main_search(self, matches, media):
        json = self._fetch_json(
            self.c.kinopoisk.main.search % self.get_name(media),
            headers=self.c.kinopoisk.main.headers
        )
        cnt = 0
        if json:
            for i, movie in enumerate(json):
                if movie['link'].startswith('/film/') \
                        and (
                            (movie['type'] in ['film', 'first'] and movie.get('is_serial', '') == '')
                            or ('is_serial' in movie and movie['is_serial'] == 'mini')) \
                        and int(movie['year'][:4]) <= self.api.Datetime.Now().year:
                    matches[str(movie['id'])] = [movie['rus'], movie['name'], movie['year'], i,
                                                 5 if movie['type'] == 'first' else 0]
                    cnt = cnt + 1
        return cnt

    def _api_search(self, matches, media):
        json = self._fetch_json(
            self.c.kinopoisk.api.search % self.get_name(media),
            headers=self.c.kinopoisk.api.headers
        )
        json = json.get('data', {}).get('items', {})
        cnt = 0
        if json:
            for i, movie in enumerate(json):
                if {'id', 'nameRU', 'year'} <= set(movie) and movie['type'] == 'KPFilmObject' \
                        and ((self.app.agent_type == 'movies' and u'(сериал)' not in movie['nameRU'])
                             or self.app.agent_type == 'series') \
                        and int(movie['year'][0:4]) <= self.api.Datetime.Now().year:
                    matches[str(movie['id'])] = [movie['nameRU'], movie.get('nameEN', ''), movie['year'], i,
                                                 0 if i > 0 else 5]
                    cnt = cnt + 1
        return cnt

    def find_by_id(self, id):
        movie_data = self.make_request(self.c.kinopoisk.api.film_details, id)
        if movie_data:
            return movie_data['nameRU'], int(movie_data.get('year').split('-', 1)[0] or 0)
        return None, None

    def search(self, results, media, lang, manual=False, primary=True):
        self.l('search from kinopoisk')
        matches = {}
        search_sources = [self._api_search, self._main_search, self._suggest_search]

        if manual and media.name.find('kinopoisk.ru') >= 0:
            self.l('we got kinopoisk url as name')
            id = media.name.split('-')[-1][:-1]
            if id.isdigit():
                (title, year) = self.find_by_id(id)
                if title is not None:
                    results.Append(
                        self.api.MetadataSearchResult(
                            id=id,
                            name=title,
                            lang=lang,
                            score=100,
                            year=year
                        )
                    )
                    self.continue_search = False
                    return
        for s in search_sources:
            s_match = {}
            if manual or self.continue_search:
                cnt = s(matches if manual else s_match, media)
                self.l('%s returned %s results', s.__name__, cnt)
                # if not manual - score each source separate
                if not manual and self.continue_search:
                    self.app.score.score(media, s_match)
                    if s_match.values() and max(s_match.values(), key=lambda m: m[4])[4] >= self.c.score.besthit:
                        self.continue_search = False
                    for i, d in s_match.iteritems():
                        if i in matches:
                            matches[i] = d if d[4] > matches[i][4] else matches[i]
                        else:
                            matches.update(s_match)

        # if manual - score all sources
        if manual:
            self.app.score.score(media, matches)

        for movie_id, movie in matches.items():
            if movie[4] > 0:
                results.Append(
                    self.api.MetadataSearchResult(id=movie_id, name=movie[0], lang=lang, score=movie[4], year=movie[2]))

        if manual:
            for result in results:
                result.thumb = self.c.kinopoisk.thumb % result.id
                self.l(result.thumb)
        results.Sort('score', descending=True)

    def make_request(self, link, kp_id):
        data = {}
        try:
            data = self.api.JSON.ObjectFromURL(
                link % kp_id, headers=self.c.kinopoisk.api.headers)
        except:
            self.l.Error('Something goes wrong with request', exc_info=True)
        finally:
            data = data.get('data', {})

        return data

    def update(self, metadata, media, lang, force=False, periodic=False):
        self.l('update KinopoiskSource')
        self.meta_id = metadata['id']
        self.load_meta(metadata)
        self.load_staff(metadata)
        self.load_similar(metadata)
        self.load_reviews(metadata)
        self.load_gallery(metadata)

    # load main details
    def load_meta(self, metadata):
        movie_data = self.make_request(self.c.kinopoisk.api.film_details, metadata['id'])
        self.l(movie_data)
        if not movie_data:
            return

        # title
        repls = (u' (видео)', u' (ТВ)', u' (мини-сериал)', u' (сериал)')  # remove unnecessary text
        metadata['title'] = reduce(lambda a, kv: a.replace(kv, ''), repls, movie_data['nameRU'])

        # original title
        if 'nameEN' in movie_data and movie_data['nameEN'] != movie_data['nameRU']:
            metadata['original_title'] = movie_data['nameEN']
        else:
            metadata['original_title'] = ''

        # slogan
        metadata['tagline'] = movie_data.get('slogan', '')
        # content rating age
        metadata['content_rating_age'] = int(movie_data.get('ratingAgeLimits') or 0)
        # year
        metadata['year'] = int(movie_data.get('year').split('-', 1)[0] or 0)
        # countries
        metadata['countries'] = []
        if 'country' in movie_data:
            for country in movie_data['country'].split(', '):
                metadata['countries'].append(country)

        # genres
        metadata['genres'] = []
        for genre in movie_data['genre'].split(', '):
            metadata['genres'].append(genre.strip().title())

        # MPAA rating
        metadata['content_rating'] = movie_data.get('ratingMPAA', '')

        # originally available
        metadata['originally_available_at'] = self.api.Datetime.ParseDate(
            # use world premiere date, or russian premiere
            movie_data['rentData'].get('premiereWorld') or movie_data['rentData'].get('premiereRU'), '%d.%m.%Y'
        ).date() if (('rentData' in movie_data) and
                     [i for i in {'premiereWorld', 'premiereRU'} if i in movie_data['rentData']]
                     ) else None

        metadata['kp_rating'] = float(movie_data.get('ratingData', {}).get('rating', 0))
        metadata['imdb_rating'] = float(movie_data.get('ratingData', {}).get('ratingIMDb', 0))

        # summary
        summary_add = ''
        if movie_data.get('ratingData', {}):
            if 'rating' in movie_data['ratingData']:
                summary_add = u'КиноПоиск: ' + movie_data['ratingData'].get('rating').__str__()
                if 'ratingVoteCount' in movie_data['ratingData']:
                    summary_add += ' (' + movie_data['ratingData'].get('ratingVoteCount').__str__() + ')'
                summary_add += '. '

            if 'ratingIMDb' in movie_data['ratingData']:
                summary_add += u'IMDb: ' + movie_data['ratingData'].get('ratingIMDb').__str__()
                if 'ratingIMDbVoteCount' in movie_data['ratingData']:
                    summary_add += ' (' + movie_data['ratingData'].get('ratingIMDbVoteCount').__str__() + ')'
                summary_add += '. '
        metadata['summary'] = summary_add + movie_data.get('description', '')

        # main trailer
        metadata['trailer'] = movie_data.get('videoURL',{}).get('hd','')

    def load_staff(self, metadata):
        self.l('load staff from kinopoisk')
        staff_data = self.make_request(self.c.kinopoisk.api.staff, metadata['id'])

        if not staff_data:
            return

        people = metadata['staff'] = {}
        people['directors'] = []
        people['writers'] = []
        people['producers'] = []
        people['roles'] = []

        type_map = {'actor': 'roles', 'director': 'directors', 'writer': 'writers', 'producer': 'producers'}

        for staff_type in staff_data['creators']:
            for staff in staff_type:
                if type_map.get(staff.get('professionKey'), {}):
                    people[type_map[staff.get('professionKey')]].append(dict(
                        nameRU=staff.get('nameRU'),  # staff name
                        nameEN=staff.get('nameEN'),  # staff name
                        photo=self.c.kinopoisk.actor % staff['id'] if 'posterURL' in staff else None,  # staff photo
                        role=" ".join(re.sub(r'\([^)]*\)', '', staff.get('description', '')).split())  # staff character
                    ))
        del people

    def load_reviews(self, metadata):
        reviews_dict = self.make_request(self.c.kinopoisk.api.film_reviews, metadata['id'])
        if not isinstance(reviews_dict, dict):
            return None

        metadata['kp_reviews'] = []
        for review in reviews_dict.get('reviews', []):
            metadata['kp_reviews'].append({
                'author': review.get('reviewAutor'),
                'source': 'Kinopoisk',
                'text': review.get('reviewDescription').replace(u'\x0b', u'')
            })

    def load_similar(self, metadata):
        self.l('load similar from kinopoisk')
        # hasRelatedFilms, hasSimilarFilms, hasSequelsAndPrequelsFilms
        similar_data = self.make_request(self.c.kinopoisk.api.similar_films, metadata['id'])

        if not similar_data:
            return

        metadata['similar'] = []
        for similar in similar_data.get('items', []):
            metadata['similar'].append(similar['nameRU'])

    def load_gallery(self, metadata):
        self.l('load gallery from kinopoisk')
        gallery_data = self.make_request(self.c.kinopoisk.api.gallery, metadata['id'])

        if not gallery_data:
            return

        self.l('gallery_data = %s', gallery_data)