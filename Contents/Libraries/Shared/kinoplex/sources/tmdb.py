# -*- coding: utf-8 -*-
from base import SourceBase
import re, types, unicodedata, hashlib

INITIAL_SCORE = 100 # Starting value for score before deductions are taken.
PERCENTAGE_PENALTY_MAX = 20.0 # Maximum amount to penalize matches with low percentages.
COUNT_PENALTY_THRESHOLD = 500.0 # Items with less than this value are penalized on a scale of 0 to COUNT_PENALTY_MAX.
COUNT_PENALTY_MAX = 10.0 # Maximum amount to penalize matches with low counts.
FUTURE_RELEASE_DATE_PENALTY = 10.0 # How much to penalize movies whose release dates are in the future.
YEAR_PENALTY_MAX = 10.0 # Maximum amount to penalize for mismatched years.
GOOD_SCORE = 97 # Score required to short-circuit matching and stop searching.
SEARCH_RESULT_PERCENTAGE_THRESHOLD = 80 # Minimum 'percentage' value considered credible for PlexMovie results.

ARTWORK_ITEM_LIMIT = 15
POSTER_SCORE_RATIO = .3 # How much weight to give ratings vs. vote counts when picking best posters. 0 means use only ratings.
BACKDROP_SCORE_RATIO = .3


class TMDBSource(SourceBase):
    def __init__(self, app):
        super(TMDBSource, self).__init__(app)

    def update_ext_ids(self, meta, source, ext_id):
        if meta['meta_ids'].get(source) is None and ext_id is not None:
            meta['meta_ids'][source] = ext_id

    def safe_unicode(self, s, encoding='utf-8'):
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
                    elif year_delta > 1 and dist > 0:
                        score_penalty += year_delta * per_year_penalty

            # Store the final score in the result vector.
            matches[key][5] = int(INITIAL_SCORE - dist - score_penalty)

    def get_hash_results(self, meta, matches, search_type='hash', plex_hash='', lang='en'):
        if search_type is 'hash' and plex_hash is not None:
            url = '%s/movie/hash/%s/%s.xml' % (self.conf.hash_base, plex_hash[0:2], plex_hash)
        else:
            if meta.get('original_title'):
                titleyear_guid = self.titleyear_guid(meta['original_title'], meta['year'])
            else:
                titleyear_guid = self.titleyear_guid(meta['title'], meta['year'])
            url = '%s/movie/guid/%s/%s.xml' % (self.conf.hash_base, titleyear_guid[0:2], titleyear_guid)

        try:
            self.d("checking %s search vector: %s" % (search_type, url))
            res = self._fetch_xml(url)
            if res is None:
                return
            xpath = "//match[@lang='%s']" % lang if search_type=='hash' else '//match'
            for match in res.xpath(xpath):
                id    = "tt%s" % match.get('guid')
                name  = self.safe_unicode(match.get('title'))
                year  = self.safe_unicode(match.get('year'))
                count = int(match.get('count', 0))
                pct   = int(match.get('percentage', 0))
                dist  = self.api.Util.LevenshteinDistance(meta.get('original_title', meta['title']), name.encode('utf-8'))
                if pct >= 98 and dist > 5:
                    tmdb_data = self.find_tmdb(id)
                    if tmdb_data:
                        dist_new = self.api.Util.LevenshteinDistance(meta.get('original_title', meta['title']), tmdb_data.get('original_title'))
                        if dist_new < dist:
                            dist = dist_new
                            name = tmdb_data.get('title')
                            if not year:
                                year = tmdb_data.get('release_date', '')[:4]

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
                self.l('vector = %s', vector)

        except Exception, e:
            self.l.Error("freebase/proxy %s lookup failed: %s" % (search_type, str(e)))

    def get_tmdb_search(self, metadata, search_title, search_year, lang):
        tmdb_dict = self._fetch_json(self.conf.api.search(
            self.app.agent_type,
            self.api.String.URLEncode(metadata.get(search_title)),
            search_year,
            lang,
            'true'
        ))

        if isinstance(tmdb_dict, dict) and 'results' in tmdb_dict:
            for i, movie in enumerate(sorted(tmdb_dict['results'], key=lambda k: k['popularity'], reverse=True)):
                score = 100
                if not movie.get('title') and movie.get('name'):
                    movie['title'] = movie['name']
                score = score - abs(self.api.String.LevenshteinDistance(movie['title'].lower(), metadata.get(search_title)))
                score = score - (2 * i)

                if 'release_date' in movie and movie['release_date']:
                    release_year = int(movie['release_date'].split('-')[0])
                else:
                    release_year = -1

                if search_year > 1900 and release_year:
                    per_year_penalty = int(YEAR_PENALTY_MAX / 3)
                    year_delta = abs(int(search_year) - (int(release_year)))
                    if year_delta > 3:
                        score = score - YEAR_PENALTY_MAX
                    else:
                        score = score - year_delta * per_year_penalty
                movie['score'] = score
        return tmdb_dict

    def _search(self, metadata, media, lang):
        self.l('search for TMDB id')
        hash_matches = {}
        title_year_matches = {}
        search_matches = {}
        plexHashes = []
        try:
            for item in media.items:
                for part in item.parts:
                    if part.hash: plexHashes.append(part.hash)
        except:
            try: plexHashes.append(media.hash)
            except: pass

        self.d('HASH CHECK')
        for plex_hash in plexHashes:
            self.get_hash_results(metadata, hash_matches, search_type='hash', plex_hash=plex_hash, lang=lang)
        self.score_hash(metadata, hash_matches)
        for key in hash_matches.keys():
            match = hash_matches[key]
            self.d("Found hash match: %s (%s) score=%d, key=%s" % (match[1], match[2], match[5], key))
            if int(match[5]) >= GOOD_SCORE:
                return key

        self.d('TITLE/YEAR CHECK')
        self.get_hash_results(metadata, title_year_matches, search_type='title/year')
        self.score_hash(metadata, title_year_matches)
        for key in title_year_matches.keys():
            match = title_year_matches[key]
            self.d("Found title/year match: %s (%s) score=%d, key=%s" % (match[1], match[2], match[5], key))
            if int(match[5]) >= GOOD_SCORE:
                return key

        search_year = metadata['year']

        self.d('TITLE SEARCH')
        tmdb_dict = self.get_tmdb_search(metadata, 'title', search_year, lang)
        if isinstance(tmdb_dict, dict) and 'results' in tmdb_dict:
            for m in tmdb_dict.get('results', []):
                self.d("Found title search match: %s (%s) score=%d, key=%s" % (m.get('title'),
                                                                               m.get('release_date'),
                                                                               m.get('score', 0),
                                                                               m.get('id')))
            best_result = max(tmdb_dict.get('results') or [{'score': 0}], key=lambda x: x['score'])
            if best_result['score'] >= GOOD_SCORE:
                return best_result['id']

        if metadata.get('original_title'):
            self.d('ORIGINAL TITLE SEARCH')
            tmdb_dict = self.get_tmdb_search(metadata, 'original_title', search_year, lang)
            if isinstance(tmdb_dict, dict) and 'results' in tmdb_dict:
                for m in tmdb_dict.get('results', []):
                    self.d("Found original title search match: %s (%s) score=%d, key=%s" % (m.get('title'),
                                                                               m.get('release_date'),
                                                                               m.get('score', 0),
                                                                               m.get('id')))
                best_result = max(tmdb_dict.get('results') or [{'score': 0}], key=lambda x: x['score'])
                if best_result['score'] >= GOOD_SCORE:
                    return best_result['id']

        self.d('UMP SEARCH')
        search_title = 'original_title' if metadata.get('original_title') else 'title'
        ump_dict = self._fetch_xml(self.conf.ump_search % (metadata.get(search_title), metadata['year'], ','.join(plexHashes), lang, 0))
        if ump_dict is not None and len(ump_dict):
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
                if search_title == video.get('title'):
                    self.d("Found ump search match: %s (%s) score=%d, key=%s" % (video.get('title'), video.get('year'), score, video_id))
                    if score >= GOOD_SCORE:
                        return video_id

        return None

    def find_tmdb(self, imdb_id):
        resp_data = self._fetch_json(self.conf.api.find(imdb_id))
        if resp_data:
            tmdb_data = resp_data.get('%s_results' % self.app.agent_type, [{}])
            if tmdb_data and tmdb_data[0]:
                return tmdb_data[0]
        return {}

    def update(self, metadata, media, lang, force=False, periodic=False):
        self.l('update from TMDBSource')
        source_id = metadata['meta_ids'].get(self.source_name)
        if not source_id:
            source_id = metadata['meta_ids'][self.source_name] = self._search(metadata, media, lang)
            if source_id and re.match('t*[0-9]{7}', str(source_id)):
                source_id = metadata['meta_ids']['tmdb'] = self.find_tmdb(source_id).get('id')

        if source_id:
            config_dict = self._fetch_json(self.conf.api.config)
            movie_data = self._fetch_json(self.conf.api.data(self.app.agent_type, source_id, lang))
            if not isinstance(movie_data, dict) or 'overview' not in movie_data or movie_data['overview'] is None or movie_data['overview'] == "":
                movie_data = self._fetch_json(self.conf.api.data(self.app.agent_type, source_id, ''))

            ext_ids = movie_data.get('external_ids', {})
            if ext_ids:
                self.update_ext_ids(metadata, 'imdb', ext_ids.get('imdb_id'))
                self.update_ext_ids(metadata, 'tvdb', ext_ids.get('tvdb_id'))

            # Collections.
            if self.api.Prefs['collections_id']:
                metadata['collections'] = []
                if movie_data.get('belongs_to_collection', ''):
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
                metadata['ratings']['tmdb'] = movie_data.get('vote_average', 0)

            movie_images = movie_data.get('images', {})
            posters = metadata['covers']['tmdb'] = {}
            for i, poster in enumerate(movie_images.get('posters', [])):
                poster_url = config_dict['images']['base_url'] + 'original' + poster['file_path']
                thumb_url = config_dict['images']['base_url'] + 'w154' + poster['file_path']
                posters[poster_url] = (thumb_url, i+1, poster['iso_639_1'], poster['vote_average'], poster['vote_count'])

            backdrops = metadata['backdrops']['tmdb'] = {}
            for i, backdrop in enumerate(movie_images.get('backdrops', [])):
                backdrop_url = config_dict['images']['base_url'] + 'original' + backdrop['file_path']
                thumb_url = config_dict['images']['base_url'] + 'w300' + backdrop['file_path']
                backdrops[backdrop_url] = (thumb_url, i+1, backdrop['iso_639_1'], backdrop['vote_average'], backdrop['vote_count'])

