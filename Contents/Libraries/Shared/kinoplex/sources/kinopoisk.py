# -*- coding: utf-8 -*-
from base import SourceBase

import re
from guessit import guessit

KP_REGEXP = re.compile(r'(kinopoisk|kp)-(\d+)')

class KinopoiskSource(SourceBase):
    def __init__(self, app):
        super(KinopoiskSource, self).__init__(app)

    @staticmethod
    def clear_text(text):
        text = re.sub(r'[\x0b-\x0c]', '', (re.sub(r'[^\x00-\x7f]+', '', text)))
        text = text.replace(u'\u2014', u'--').replace(u'\u2013', u'-')
        return text

    def _get_name(self, media):
        return media.name if self.app.agent_type == 'movie' else media.show

    def get_name(self, media):
        _name = self._get_name(media)
        if _name:
            return self.api.String.Quote(_name, False)

    def _suggest_search(self, matches, media_name):
        page = 1
        json = self._fetch_json(
            self.conf.main.yasearch % media_name % page,
            headers=self.conf.main.headers()
        )
        json = json[2] if 2 <= len(json) else []
        cnt = 0
        if json:
            ftype = 'MOVIE' if self.app.agent_type == 'movie' else 'SHOW'
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

    def _main_search(self, matches, media_name):
        page = 1
        json = self._fetch_json(
            self.conf.main.search % (media_name , page),
            headers=self.conf.main.headers()
        )
        cnt = 0
        pagesCount = 0

        if json:
            for i, movie in enumerate(json['films']):
                if movie['year'].isdigit():
                    _year = movie['year'][:4]
                if _year:
                    _year = int(_year)
                if ((movie['type'] in ['FILM', 'FIRST', 'VIDEO'] and (movie.get('nameRu')))
                            or ('is_serial' in movie and movie['is_serial'] in ('serial', 'mini', 'TV'))) \
                        and _year <= self.api.Datetime.Now().year:
                    matches[str(movie['filmId'])] = [movie['nameRu'] if 'nameRu' in movie else movie['nameEn'], movie['nameEn'] if 'nameEn' in movie else movie['nameRu'], movie['year'], i,
                                                5 if movie['type'] == 'first' else 0]
                    cnt = cnt + 1
            page = page + 1

            if json.get('pagesCount'):
                pagesCount = int(json.get('pagesCount'))
                while page <= pagesCount and pagesCount < 21: 
                    json = self._fetch_json(
                        self.conf.main.search % (media_name , page),
                        headers=self.conf.main.headers()
                    )
                    for i, movie in enumerate(json['films']):
                        if movie['year'].isdigit():
                            _year = movie['year'][:4]
                        if _year:
                            _year = int(_year)
                        if ((movie['type'] in ['FILM', 'FIRST', 'VIDEO'] and (movie.get('nameRu')))
                                    or ('is_serial' in movie and movie['is_serial'] in ('serial', 'mini', 'TV'))) \
                                and _year <= self.api.Datetime.Now().year:
                            matches[str(movie['filmId'])] = [movie['nameRu'] if 'nameRu' in movie else movie['nameEn'], movie['nameEn'] if 'nameEn' in movie else movie['nameRu'], movie['year'], i,
                                                        5 if movie['type'] == 'first' else 0]
                            cnt = cnt + 1
                    page = page + 1
        return cnt

    def _api_search(self, matches, media_name):
        return self._main_search(matches, media_name)

        json = self._fetch_json(
            self.conf.api.search % media_name,
            headers=self.conf.api.headers
        )
        json = json.get('data', {}).get('items', {})
        cnt = 0
        if json:
            for i, movie in enumerate(json):
                if {'id', 'nameRU', 'year'} <= set(movie) and movie['type'] == 'KPFilmObject' \
                        and ((self.app.agent_type == 'movie' and u'(сериал)' not in movie['nameRU'])
                             or self.app.agent_type == 'tv') \
                        and int(movie['year'][0:4]) <= self.api.Datetime.Now().year:
                    matches[str(movie['id'])] = [movie['nameRU'], movie.get('nameEN', ''), movie['year'], i,
                                                 0 if i > 0 else 5]
                    cnt = cnt + 1
        return cnt

    def find_by_id(self, movie_id):
        movie_data = self.make_request(self.conf.api.film_details, movie_id)
        if movie_data:
            return movie_data['nameRU'], int(movie_data.get('year').split('-', 1)[0] or 0)
        return None, None

    def search(self, results, media, lang, manual=False, primary=True):
        continue_search = True
        matches = {}

        if self.api.Prefs['lookup_by_kinopoisk_id']:
            # Ищем маркер kp- или kinopoisk- в пути
            kinopoisk_ids = []
            _title = self._get_name(media)
            if _title:
                kinopoisk_ids = [m[1] for m in KP_REGEXP.findall(_title)]
            # При первом сканировании скорее всего будут отсутствовать
            elif media and media.tree and media.tree.items:
                _parts = [p.file for mi in media.tree.items for p in mi.parts]
                kinopoisk_ids = [m[0] for fn in _parts for m in KP_REGEXP.findall(fn)]

            # Если есть путь к файлу
            if media.filename:
                _filename = self.api.String.Unquote(media.filename)
                kinopoisk_ids += [m[1] for m in KP_REGEXP.findall(_filename)]

            if kinopoisk_ids:
                kinopoisk_ids = set(kinopoisk_ids)

                if len(kinopoisk_ids) > 1:
                    self.d('WARNING: Found more than one Kinopoisk ID: %s' % kinopoisk_ids)
                movie_id = next(iter(kinopoisk_ids))
                self.d('Found Kinopoisk ID: %s. Getting from Kinopoisk.ru' % movie_id)
                (title, year) = self.find_by_id(movie_id)
                if title is not None:
                    results.Append(
                        self.api.MetadataSearchResult(
                            id=movie_id,
                            name=title,
                            lang=lang,
                            score=100,
                            year=year
                        )
                    )
                    return
                else:
                    self.d('For Kinopoisk ID: %s. Media not found :(' % movie_id)

        search_sources = [self._main_search, self._api_search]

        if manual and self.api.Data.Exists(media.id):
            self.d('manual search - remove matched ids')
            self.api.Data.Remove(media.id)

        media_name = self.get_name(media)
        if manual and media_name.find('kinopoisk.ru') >= 0:
            self.d('manual search - link passed as name (%s)', media_name)
            if media_name.find('-') >= 0:
                movie_id = media_name.split('-')[-1][:-1]
            else:
                movie_id = media_name.split('/')[-2]

            if movie_id.isdigit():
                (title, year) = self.find_by_id(movie_id)
                if title is not None:
                    results.Append(
                        self.api.MetadataSearchResult(
                            id=movie_id,
                            name=title,
                            lang=lang,
                            score=100,
                            year=year
                        )
                    )
                    return

        if (media.year is None or not media_name) and media.filename:
            self.d('no year, try guessit parse')
            try:
                guessit_results = guessit(self.api.String.Unquote(media.filename), {'no_user_config': True})
                if 'title' in guessit_results:
                        media.name = guessit_results['title']
                if 'year' in guessit_results:
                    media.year = guessit_results['year']
            except Exception, e:
                self.l.Error(e, exc_info=True)

        for s in search_sources:
            s_match = {}
            if manual or continue_search:
                _media_name = self.get_name(media)
                cnt = s(matches if manual else s_match, _media_name)
                self.d('%s returned %s results for query %s', s.__name__, cnt, _media_name)

                if media.tree and media.tree.title and media.tree.title != _media_name:
                    cnt = s(matches if manual else s_match, self.api.String.Quote(media.tree.title, False))
                    self.d('%s returned %s results for query %s', s.__name__, cnt, media.tree.title)
                if not manual and continue_search:
                    self.app.score.score(media, s_match)
                    if s_match.values() and max(s_match.values(), key=lambda m: m[4])[4] >= 95:
                        continue_search = False
                    for i, d in s_match.iteritems():
                        if i in matches:
                            matches[i] = d if d[4] > matches[i][4] else matches[i]
                        else:
                            matches.update(s_match)

        if manual:
            self.app.score.score(media, matches)

        for movie_id, movie in matches.items():
            if movie[4] > 0 or (manual and not self.api.Prefs['manual_search_scoring']):
                results.Append(
                    self.api.MetadataSearchResult(id=movie_id, name=movie[0], lang=lang, score=movie[4], year=movie[2]))

        if manual:
            for result in results:
                result.thumb = self.conf.thumb % result.id
                #self.l(result)
        results.Sort('score', descending=True)

    def make_request(self, link, *args):
        data = {}
        try:
            data = self.api.JSON.ObjectFromURL(
                link % args, headers=self.conf.api.headers)            
        except:
            self.l.Error('Something goes wrong with request', exc_info=True)
        finally:
            if not (isinstance(data, list)):        
                if data.get('data'):
                    data = data.get('data', {})
        return data

    def update(self, metadata, media, lang, force=False, periodic=False):
        self.l('update KinopoiskSource')
        self.load_meta(metadata)
        self.load_distribution(metadata)
        self.load_staff(metadata)
        self.load_reviews(metadata)
        self.load_similar(metadata)    
        self.load_gallery(metadata)    

        if self.app.agent_type == 'tv':
            self.load_series(metadata, media)

        

    def load_meta(self, metadata):
        movie_data = self.make_request(self.conf.api.film_details, metadata['id'])

        if not movie_data:
            return

        if movie_data.get('imdbId'):
            metadata['meta_ids']['imdb'] = movie_data.get('imdbId');  
        
        repls = (u' (видео)', u' (ТВ)', u' (мини-сериал)', u' (сериал)')
        metadata['title'] = reduce(lambda a, kv: a.replace(kv, ''), repls, movie_data['nameRu'])

        if 'nameOriginal' in movie_data and movie_data['nameOriginal'] != movie_data['nameRu']:
            metadata['original_title'] = movie_data['nameOriginal']

        metadata['tagline'] = movie_data.get('slogan', '')
        metadata['content_rating_age'] = int(movie_data.get('ratingAgeLimits').replace('age', '') or 0)
        try:
            metadata['year'] = int(movie_data.get('year', ''))
        except:
            self.l('error converting year (%s) to int', movie_data.get('year'))

        metadata['countries'] = []
        if 'countries' in movie_data:
            for country in movie_data.get('countries', []):
                metadata['countries'].append(country['country'])

        metadata['genres'] = []
        for genre in movie_data.get('genres', []):
            metadata['genres'].append(genre['genre'])

        if self.api.Prefs['content_rating'] == "MPAA" and movie_data.get('ratingMpaa'):
            metadata['content_rating'] = movie_data.get('ratingMpaa', '').upper()
        elif self.api.Prefs['content_rating'] == "Возраст" and movie_data.get('ratingAgeLimits'):
            metadata['content_rating'] = '%s+' % movie_data.get('ratingAgeLimits')

        if movie_data.get('premiereWorld'):
            metadata['originally_available_at'] = self.api.Datetime.ParseDate(
                (
                    movie_data['rentData'].get('premiereWorld') or movie_data['rentData'].get('premiereRU')
                ).replace('00.', '01.'), '%d.%m.%Y'
            ).date() if (('rentData' in movie_data) and
                        [i for i in {'premiereWorld', 'premiereRU'} if
                        i in movie_data['rentData'] and len(movie_data['rentData'][i]) == 10]
                        ) else None

        if movie_data.get('ratingKinopoisk'):            
            metadata['ratings']['kp'] = float(movie_data.get('ratingKinopoisk', 0))

        if movie_data.get('ratingImdb'):   
            metadata['ratings']['imdb'] = float(movie_data.get('ratingImdb', 0))

        summary_add = ''
        if self.api.Prefs['desc_show_slogan'] and movie_data.get('slogan'):
            summary_add += '%s\n' % movie_data.get('slogan')

        if self.api.Prefs['desc_rating_kp'] and movie_data.get('ratingKinopoisk'):
            summary_add += u'КиноПоиск: %s' % movie_data.get('ratingKinopoisk')
            if self.api.Prefs['desc_rating_vote_count'] and movie_data.get('ratingKinopoiskVoteCount'):
                summary_add += ' (%s)' % movie_data.get('ratingKinopoiskVoteCount')
            summary_add += '\n' if self.api.Prefs['desc_rating_newline'] else '. '

        if self.api.Prefs['desc_rating_imdb'] and movie_data.get('ratingImdb'):
            summary_add += u'IMDB: %s' % movie_data.get('ratingImdb')
            if self.api.Prefs['desc_rating_vote_count'] and movie_data.get('ratingImdbVoteCount'):
                summary_add += ' (%s)' % movie_data.get('ratingImdbVoteCount')
            summary_add += '\n' if self.api.Prefs['desc_rating_newline'] else '. '
        metadata['summary'] = summary_add + movie_data.get('description', '')
        
        metadata['main_poster'] = {
            'full': movie_data.get('posterUrl'),
            'thumb': movie_data.get('posterUrlPreview')
        }

        if 'itunes' in movie_data:
            metadata['meta_ids']['itunes'] = movie_data['itunes']['resourceId']

        metadata['has_pre_sequel'] = movie_data.get('hasSequelsAndPrequelsFilms', 0)
        metadata['has_similar'] = movie_data.get('hasSimilarFilms', 0)
        metadata['seriesInfo'] = movie_data.get('seriesInfo', {})

    def load_distribution(self, metadata):
        self.l('load distribution from kinopoisk')
        distribution_data = self.make_request(self.conf.api.distributions, metadata['id'])

        if not distribution_data:
            return

        if not distribution_data.get('items'):
            return

        for distr in distribution_data.get('items', []):
            if distr.get('type') == 'WORLD_PREMIER':
                metadata['originally_available_at'] = self.api.Datetime.ParseDate((distr.get('date')).replace('00.', '01.'), '%Y-%m-%d').date()     

    def load_staff(self, metadata):
        self.l('load staff from kinopoisk')
        staff_data = self.make_request(self.conf.api.staff, metadata['id'])

        if not staff_data:
            return

        people = metadata['staff'] = {}
        people['directors'] = []
        people['writers'] = []
        people['producers'] = []
        people['roles'] = []

        type_map = {'actor': 'roles', 'director': 'directors', 'writer': 'writers', 'producer': 'producers'}

        for staff in staff_data:
            if type_map.get(staff.get('professionKey').lower(), {}):
                people[type_map[staff.get('professionKey').lower()]].append(dict(
                    nameRU=staff.get('nameRu'),  # staff name
                    nameEN=staff.get('nameEn'),  # staff name
                    photo=staff.get('posterUrl') if 'posterUrl' in staff else None,
                    role=staff.get('description', '')
                ))
        del people

    def load_reviews(self, metadata):
        reviews_dict = self.make_request(self.conf.api.film_reviews, metadata['id'])
        if not reviews_dict:
            return None

        reviews = metadata['reviews']['kp'] = []
        for review in reviews_dict.get('reviews', []):
            image = ''
            if review.get('reviewType') == 'NEGATIVE':
                image = 'rottentomatoes://image.review.rotten'
            if review.get('reviewType') == 'POSITIVE':
                image = 'rottentomatoes://image.review.fresh'     
            reviews.append({
                'author': review.get('reviewAutor'),
                'source': 'Kinopoisk',
                'image': image,
                'text': re.sub(r'[\x00-\x08\x0b\x0c\x0e]', '', review.get('reviewDescription'))
            })
        del reviews

    def load_similar(self, metadata):
        self.l('load similar from kinopoisk')
        similar_data = self.make_request(self.conf.api.similars, metadata['id'])

        if not similar_data:
            return

        metadata['similar'] = []
        for similar in similar_data.get('items', []):
            if similar.get('nameRu'):
                metadata['similar'].append(similar['nameRu'])

    def load_sequel(self, metadata):
        self.l('load sequel from kinopoisk')
        sequel_data = self.make_request(self.conf.api.list_films, metadata['id'], 'kp_sequels_and_prequels_films')

        if not sequel_data:
            return

        metadata['sequel'] = []
        self.d('sequel_data = %s', sequel_data)

    def load_gallery(self, metadata):
        self.l('load gallery from kinopoisk')
        gallery_data = self.make_request(self.conf.api.gallery, metadata['id'])

        posters = metadata['covers']['kp'] = {}
        posters[self.conf.poster % metadata.get('id')] = (
            self.conf.thumb % metadata.get('id'),
            1,
            'ru',
            1000000
        )
        del posters

        if not gallery_data or 'frames' not in gallery_data:
            return

        backdrops = metadata['backdrops']['kp'] = {}
        for i, kadr in enumerate(gallery_data.get('frames', [])):
            backdrops[kadr['image']] = (
                kadr['preview'],
                i,
                'ru',
                0
            )
        del backdrops

    def load_series(self, metadata, media):
        self.l('load series from kinopoisk')
        if not metadata['seriesInfo']:
            return

        episodes_list = []
        for i in range(1, int(metadata['seriesInfo'].get('totalSeasons', 1))):
            if i not in media.seasons:
                continue
            season_data = self.make_request(self.conf.api.series, metadata['id'], i, 1)
            episodes_list.extend(season_data.get('items', []))
            last_id = (episodes_list or [{}])[-1].get('positionInSeason', 0)
            series_count = int(season_data.get('seasonSeriesCount', 0))

            if season_data.get('pagesCount', 1) > 1 \
                    and [x for x in range(int(last_id)+1, series_count+1) if x in media.seasons[i].episodes]:
                for j in range(2, int(season_data.get('pagesCount', 1))+1):
                    season_data = self.make_request(self.conf.api.series, metadata['id'], i, j)
                    episodes_list.extend(season_data.get('items', []))

        for serie in episodes_list:
            if serie['positionInSeason'] not in media.seasons[serie['seasonNumber']].episodes:
                continue
            episode = metadata['seasons'][serie['seasonNumber']].episodes[serie['positionInSeason']]
            episode.title = serie['nameRU'] or serie['nameEN']
            episode.originally_available_at = self.api.Datetime.ParseDate(serie['premiereDate'], '%d.%m.%Y') if serie['premiereDate'] else None
            episode.absolute_index = int(serie['globalPosition'])
