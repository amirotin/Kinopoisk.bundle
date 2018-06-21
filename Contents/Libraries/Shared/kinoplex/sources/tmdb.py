# -*- coding: utf-8 -*-
from base import SourceBase
import re, types, unicodedata, hashlib

INITIAL_SCORE = 100 # Starting value for score before deductions are taken.
PERCENTAGE_PENALTY_MAX = 20.0 # Maximum amount to penalize matches with low percentages.
COUNT_PENALTY_THRESHOLD = 500.0 # Items with less than this value are penalized on a scale of 0 to COUNT_PENALTY_MAX.
COUNT_PENALTY_MAX = 10.0 # Maximum amount to penalize matches with low counts.
FUTURE_RELEASE_DATE_PENALTY = 10.0 # How much to penalize movies whose release dates are in the future.
YEAR_PENALTY_MAX = 10.0 # Maximum amount to penalize for mismatched years.
GOOD_SCORE = 98 # Score required to short-circuit matching and stop searching.
SEARCH_RESULT_PERCENTAGE_THRESHOLD = 80 # Minimum 'percentage' value considered credible for PlexMovie results.

ARTWORK_ITEM_LIMIT = 15
POSTER_SCORE_RATIO = .3 # How much weight to give ratings vs. vote counts when picking best posters. 0 means use only ratings.
BACKDROP_SCORE_RATIO = .3

class TMDBSource(SourceBase):
    def __init__(self, app):
        super(TMDBSource, self).__init__(app)

    def safe_unicode(self, s,encoding='utf-8'):
        if s is None:
            return None
        if isinstance(s, basestring):
            if isinstance(s, types.UnicodeType):
                return s
            else:
                return s.decode(encoding)
        else:
            return str(s).decode(encoding)

    def identifierize(self, string):
        string = re.sub( r"\s+", " ", string.strip())
        string = unicodedata.normalize('NFKD', self.safe_unicode(string))
        string = re.sub(r"['\"!?@#$&%^*\(\)_+\.,;:/]","", string)
        string = re.sub(r"[_ ]+","_", string)
        string = string.strip('_')
        return string.strip().lower()

    def guidize(self, string):
        hash = hashlib.sha1()
        hash.update(string.encode('utf-8'))
        return hash.hexdigest()

    def titleyear_guid(self, title, year):
        if title is None:
            title = ''

        if year == '' or year is None or not year:
            string = "%s" % self.identifierize(title)
        else:
            string = "%s_%s" % (self.identifierize(title).lower(), year)
        return self.guidize("%s" % string)

    def score_hash(self, metadata, matches):
        for key in matches.keys():
            match = matches[key]

            dist = match[0]
            name = match[1]
            year = match[2]
            total_pct = match[3]
            total_cnt = match[4]

            # Compute score penalty for percentage/count.
            score_penalty = (100 - total_pct) * (PERCENTAGE_PENALTY_MAX / 100)
            if total_cnt < COUNT_PENALTY_THRESHOLD:
                score_penalty += (COUNT_PENALTY_THRESHOLD - total_cnt) / COUNT_PENALTY_THRESHOLD * COUNT_PENALTY_MAX

            # Year penalty/bonus.
            if year and year.isdigit():
                if int(year) > self.api.Datetime.Now().year:
                    score_penalty += FUTURE_RELEASE_DATE_PENALTY

                if metadata['year'] and year:
                    per_year_penalty = int(YEAR_PENALTY_MAX / 3)
                    year_delta = abs(int(metadata['year']) - (int(year)))
                if year_delta > 3:
                    score_penalty += YEAR_PENALTY_MAX
                else:
                    score_penalty += year_delta * per_year_penalty

            # Store the final score in the result vector.
            matches[key][5] = int(INITIAL_SCORE - dist - score_penalty)

    def get_hash_results(self, meta, matches, search_type='hash', plex_hash=''):
        if search_type is 'hash' and plex_hash is not None:
            url = '%s/movie/hash/%s/%s.xml' % (self.c.tmdb.hash_base, plex_hash[0:2], plex_hash)
        else:
            if meta.get('original_title'):
                titleyear_guid = self.titleyear_guid(meta['original_title'], meta['year'])
            else:
                titleyear_guid = self.titleyear_guid(meta['title'], meta['year'])
            url = '%s/movie/guid/%s/%s.xml' % (self.c.tmdb.hash_base, titleyear_guid[0:2], titleyear_guid)

        try:
            self.l("checking %s search vector: %s" % (search_type, url))
            res = self._fetch_xml(url)

            for match in res.xpath('//match'):
                id    = "tt%s" % match.get('guid')
                name  = self.safe_unicode(match.get('title'))
                year  = self.safe_unicode(match.get('year'))
                count = int(match.get('count', 0))
                pct   = int(match.get('percentage', 0))
                dist  = self.api.Util.LevenshteinDistance(meta['original_title'], name.encode('utf-8'))

                # Intialize.
                if not matches.has_key(id):
                    matches[id] = [1000, '', None, 0, 0, 0]

                # Tally.
                vector = matches[id]
                vector[3] = vector[3] + pct
                vector[4] = vector[4] + count

                # See if a better name.
                if dist < vector[0]:
                    vector[0] = dist
                    vector[1] = name
                    vector[2] = year

        except Exception, e:
            self.l("freebase/proxy %s lookup failed: %s" % (search_type, str(e)))

    def _search(self, metadata, media, lang):
        self.l('search for TMDB id')

        result_id = None
        hash_matches = {}
        title_year_matches = {}
        api_matches = {}
        movies_data = {}
        plexHashes = []
        try:
            for item in media.items:
                for part in item.parts:
                    if part.hash: plexHashes.append(part.hash)
        except:
            try: plexHashes.append(media.hash)
            except: pass

        for plex_hash in plexHashes:
            self.get_hash_results(metadata, hash_matches, search_type='hash', plex_hash=plex_hash)
        if hash_matches:
            self.score_hash(metadata, hash_matches)
        for key in hash_matches.keys():
            match = hash_matches[key]
            if int(match[5]) >= GOOD_SCORE:
                return key

        self.get_hash_results(metadata, title_year_matches, search_type='title/year')
        self.score_hash(metadata, title_year_matches)
        self.l('title_year_matches = %s', title_year_matches)
        for key in title_year_matches.keys():
            match = title_year_matches[key]
            if int(match[5]) >= GOOD_SCORE:
                return key

        search_title = 'original_title' if metadata.get('original_title') else 'title'
        tmdb_dict = self._fetch_json(self.c.tmdb.search(self.api.String.URLEncode(metadata.get(search_title)), metadata['year'], lang, 'true'))
        if isinstance(tmdb_dict, dict) and 'results' in tmdb_dict:
            for i, movie in enumerate(sorted(tmdb_dict['results'], key=lambda k: k['popularity'], reverse=True)):
                score = 100
                score = score - abs(self.api.String.LevenshteinDistance(movie[search_title].lower(), metadata.get(search_title)))
                score = score - (5 * i)

                if 'release_date' in movie and movie['release_date']:
                    release_year = int(movie['release_date'].split('-')[0])
                else:
                    release_year = -1

                if metadata['year'] > 1900 and release_year:
                    per_year_penalty = int(YEAR_PENALTY_MAX / 3)
                    year_delta = abs(int(metadata['year']) - (int(release_year)))
                    if year_delta > 3:
                        score = score - YEAR_PENALTY_MAX
                    else:
                        score = score - year_delta * per_year_penalty
                movie['score'] = score
            best_result = max(tmdb_dict.get('results') or [{'score':0}], key=lambda x:x['score'])
            if best_result['score'] >= GOOD_SCORE:
                self.l('best_result = %s', best_result)
                return best_result['id']


        ump_dict = self._fetch_xml(self.c.tmdb.ump_search % (metadata.get(search_title), metadata['year'], ','.join(plexHashes), lang, 0))
        for video in ump_dict.xpath('//Video'):
            try:
                video_id = video.get('ratingKey')[video.get('ratingKey').rfind('/') + 1:]
                score = int(video.get('score'))
            except Exception, e:
                continue

                # Make sure ID looks like an IMDb ID
            if not re.match('t*[0-9]{7}', video_id):
                continue

                # Deal with year
            year = None
            try: year = int(video.get('year'))
            except: pass
            if score >= GOOD_SCORE:
                return video_id


    def update(self, metadata, media, lang, force=False, periodic=False):
        self.l('update from TMDBSource')
        if self.source_id is None:
            self.source_id = self._search(metadata, media, lang)

        config_dict = self._fetch_json(self.c.tmdb.config)
        movie_data = self._fetch_json(self.c.tmdb.movie(self.source_id, lang))
        if not isinstance(movie_data, dict) or 'overview' not in movie_data or movie_data['overview'] is None or movie_data['overview'] == "":
            movie_data = self._fetch_json(self.c.tmdb.movie(self.source_id, ''))

        if re.match('t*[0-9]{7}', str(self.source_id)):
            self.source_id = movie_data.get('id')

        if self.get_source_id('imdb') is None and movie_data.get('imdb_id') is not None:
            self.set_source_id('imdb', movie_data.get('imdb_id'))

            # Collections.
        metadata['collections'] = []
        if movie_data.get('belongs_to_collection',''):
            metadata['collections'].append(movie_data['belongs_to_collection']['name'].replace(' Collection', ''))

        # Studio.
        if 'production_companies' in movie_data and len(movie_data['production_companies']) > 0:
            index = movie_data['production_companies'][0]['id']
            company = None
            for studio in movie_data['production_companies']:
                if studio['id'] <= index:
                    index = studio['id']
                    company = studio['name'].strip()
            metadata['studio'] = company
        else:
            metadata['studio'] = None

        if movie_data.get('vote_count', 0) > 3:
            metadata['tmbp_rating'] = movie_data.get('vote_average', 0)

        valid_names = list()
        metadata['tmdb_posters'] = {}
        movie_images = movie_data.get('images', {})
        if movie_images.get('posters'):
            max_average = max([(lambda p: p['vote_average'] or 5)(p) for p in movie_images['posters']])
            max_count = max([(lambda p: p['vote_count'])(p) for p in movie_images['posters']]) or 1
        
            for i, poster in enumerate(movie_images['posters']):
        
                score = (poster['vote_average'] / max_average) * POSTER_SCORE_RATIO
                score += (poster['vote_count'] / max_count) * (1 - POSTER_SCORE_RATIO)
                movie_images['posters'][i]['score'] = score
        
                # Discount score for foreign posters.
                if poster['iso_639_1'] != lang and poster['iso_639_1'] is not None and poster['iso_639_1'] != 'en':
                    movie_images['posters'][i]['score'] = poster['score'] - 1
        
            for i, poster in enumerate(sorted(movie_images['posters'], key=lambda k: k['score'], reverse=True)):
                if i > ARTWORK_ITEM_LIMIT:
                    break
                else:
                    poster_url = config_dict['images']['base_url'] + 'original' + poster['file_path']
                    thumb_url = config_dict['images']['base_url'] + 'w154' + poster['file_path']
                    valid_names.append(poster_url)
        
                    if poster_url not in metadata['tmdb_posters']:
                        try: metadata['tmdb_posters'][poster_url] = (thumb_url, i+1)
                        except: pass
        
        # Backdrops.
        valid_names = list()
        metadata['tmdb_art'] = {}
        if movie_images.get('backdrops'):
            max_average = max([(lambda p: p['vote_average'] or 5)(p) for p in movie_images['backdrops']])
            max_count = max([(lambda p: p['vote_count'])(p) for p in movie_images['backdrops']]) or 1
        
            for i, backdrop in enumerate(movie_images['backdrops']):
        
                score = (backdrop['vote_average'] / max_average) * BACKDROP_SCORE_RATIO
                score += (backdrop['vote_count'] / max_count) * (1 - BACKDROP_SCORE_RATIO)
                movie_images['backdrops'][i]['score'] = score
        
                # For backdrops, we prefer "No Language" since they're intended to sit behind text.
                if backdrop['iso_639_1'] == 'xx' or backdrop['iso_639_1'] == 'none':
                    movie_images['backdrops'][i]['score'] = float(backdrop['score']) + 2

                # Discount score for foreign art.
                if backdrop['iso_639_1'] != lang and backdrop['iso_639_1'] is not None and backdrop['iso_639_1'] != 'en':
                    movie_images['backdrops'][i]['score'] = float(backdrop['score']) - 1
        
            for i, backdrop in enumerate(sorted(movie_images['backdrops'], key=lambda k: k['score'], reverse=True)):
                if i > ARTWORK_ITEM_LIMIT:
                    break
                else:
                    backdrop_url = config_dict['images']['base_url'] + 'original' + backdrop['file_path']
                    thumb_url = config_dict['images']['base_url'] + 'w300' + backdrop['file_path']
                    valid_names.append(backdrop_url)
        
                    if backdrop_url not in metadata['tmdb_art']:
                        try: metadata['tmdb_art'][backdrop_url] = (thumb_url, i+1)
                        except: pass