# -*- coding: utf-8 -*-
from cerberus import Validator, schema_registry
from sentry_sdk import configure_scope
import io, struct

schema_registry.add(
    'staff',
    {
        'staff_type': {'type': 'string', 'allowed': ['directors', 'writers', 'producers', 'roles']},
        'name': {'type': 'string'},
        'photo': {'type': 'string'},
        'role': {'type': 'string'},
    }
)

movie_schema = {
    'id': {'type': 'string'},
    'meta_ids': {'type': 'dict'},
    'title': {'type': 'string'},
    'original_title': {'type': 'string', 'default_setter': lambda doc: doc['title']},
    'year': {'type': 'integer'},
    'originally_available_at': {'type': 'date', 'nullable': True},
    'studio': {'type': 'string'},
    'tagline': {'type': 'string'},
    'summary': {'type': 'string'},
    'trivia': {'type': 'string'},
    'quotes': {'type': 'string'},
    'content_rating': {'type': 'string'},
    'content_rating_age': {'type': 'integer'},
    'writers': {'type': 'dict', 'schema': 'staff'},
    'directors': {'type': 'dict', 'schema': 'staff'},
    'producers': {'type': 'dict', 'schema': 'staff'},
    'roles': {'type': 'dict', 'schema': 'staff'},
    'countries': {'type': 'list', 'valueschema': {'type': 'string'}},
    'genres': {'type': 'list', 'valueschema': {'type': 'string'}},
    'posters': {'type': 'dict', 'default_setter': 'posters'},
    'art': {'type': 'dict', 'default_setter': 'art'},
    'banners': {'type': 'dict'},
    'themes': {'type': 'dict'},
    'chapters': {'type': 'dict'},
    'collections': {'type': 'list', 'valueschema': {'type': 'string'}},
    'reviews': {'type': 'list', 'coerce': 'reviews'},
    'clips': {'type': 'list', 'coerce': 'clips'},
    'similar': {'type': 'list', 'valueschema': {'type': 'string'}},
    'rating': {'type': 'float', 'default_setter': 'rating'},
    'audience_rating': {'type': 'float', 'nullable': True, 'default_setter': 'audience_rating'},
    'rating_image': {'type': 'string', 'nullable': True, 'default_setter': 'rating_image'},
    'audience_rating_image': {'type': 'string', 'nullable': True, 'default_setter': 'audience_rating_image'}
}


def getImageInfo(data):
    data = data
    size = len(data)
    height = width = -1
    content_type = ''

    if (size >= 10) and data[:6] in (b'GIF87a', b'GIF89a'):
        content_type = 'image/gif'
        w, h = struct.unpack(b"<HH", data[6:10])
        width = int(w)
        height = int(h)
    elif ((size >= 24) and data.startswith(b'\211PNG\r\n\032\n')
          and (data[12:16] == b'IHDR')):
        content_type = 'image/png'
        w, h = struct.unpack(b">LL", data[16:24])
        width = int(w)
        height = int(h)
    elif (size >= 16) and data.startswith(b'\211PNG\r\n\032\n'):
        content_type = 'image/png'
        w, h = struct.unpack(b">LL", data[8:16])
        width = int(w)
        height = int(h)
    elif (size >= 2) and data.startswith(b'\377\330'):
        content_type = 'image/jpeg'
        jpeg = io.BytesIO(data)
        jpeg.read(2)
        b = jpeg.read(1)
        w = h = 0
        try:
            while (b and ord(b) != 0xDA):
                while (ord(b) != 0xFF): b = jpeg.read(1)
                while (ord(b) == 0xFF): b = jpeg.read(1)
                if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    jpeg.read(3)
                    h, w = struct.unpack(b">HH", jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack(b">H", jpeg.read(2))[0])-2)
                b = jpeg.read(1)
            width = int(w)
            height = int(h)
        except struct.error:
            pass
        except ValueError:
            pass

    return content_type, width, height


class MovieValidator(Validator):
    def __init__(self, *args, **kwargs):
        self.api = kwargs.get('api', None)
        self.agent_type = kwargs.get('agent_type', None)
        super(MovieValidator, self).__init__(*args, **kwargs)

    def check_img(self, poster, thumb):
        img = w = h = None
        try:
            img, w, h = getImageInfo(self.api.HTTP.Request(
                poster,
                headers={'Range': 'bytes=0-300'}
            ).content)
        except:
            self.api.Log('failed to get image size for url %s', poster)

        return thumb + ((w, h),)

    def _normalize_coerce_clips(self, value):
        extras = []
        pref = self.api.Prefs['trailer_source'].strip()
        try:
            limit = int(self.api.Prefs['trailer_limit'])
        except:
            limit = 5
        self.api.Log('trailers pref = %s', pref)

        if pref == u"Отключено":
            return []
        if pref in [u"Кинопоиск", u"Все"]:
            extras += value.get('kp', [])
        if pref in ["IVA", u"Все"]:
            extras += value.get('iva', [])

        if self.api.Prefs['extra_all']:
            return extras[:limit] if limit > 0 else extras

        extras = filter(lambda x: x['type'] in set(['trailer', 'primary_trailer']), extras)
        return extras[:limit] if limit > 0 else extras

    def _normalize_default_setter_posters(self, document):
        posters = dict(empty={}, local={}, other={})
        result = {}
        lang = {'ru': 'local', '00': 'empty', None: 'empty', 'en': 'other', 'xx': 'other'}
        order_list = ['mm', 'itunes', 'fanart', 'tmdb', 'kp']
        prior_list = ['local', 'empty', 'other']

        priority = self.api.Prefs['poster_priority']
        try:
            limit = int(self.api.Prefs['poster_limit'])
        except:
            limit = 5
        self.api.Log('Приоритет постеров %s, лимит %s', priority, limit)

        cnt = 0
        for source in order_list:
            cnt += len(document['covers'].get(source, {}))

        if cnt < limit:
            for poster, thumb in document['covers'].get('kp', {}).items():
                document['covers']['kp'][poster] = self.check_img(poster, thumb)

        for source in order_list:
            for poster, thumb in sorted(document['covers'].get(source,{}).items(), key=lambda k: (k[1][2], k[1][3]), reverse=True):
                posters[lang.get(thumb[2], 'other')][poster] = (thumb[0], len(posters[lang.get(thumb[2], 'other')])+1)

        if priority == u'Без текста':
            prior_list.remove('empty')
            prior_list.insert(0, 'empty')

        if priority == u'Локализованные':
            prior_list.remove('local')
            prior_list.insert(0, 'local')

        for source in prior_list:
            for poster, thumb in sorted(posters[source].items(), key=lambda k: k[1][1]):
                if len(result) == limit:
                    break
                result[poster] = (thumb[0], len(result)+1)

        if not result:
            result[document['main_poster']['full']] = (document['main_poster']['thumb'], 1)

        return result

    def _normalize_default_setter_art(self, document):
        art = {}
        order_list = ['fanart', 'tmdb', 'kp']
        try:
            limit = int(self.api.Prefs['back_limit'])
        except:
            limit = 5
        for source in order_list:
            for back, thumb in sorted(document['backdrops'].get(source, {}).items(), key=lambda k: k[1][2], reverse=True):
                if len(art) == limit:
                    break
                art[back] = (thumb[0], len(art)+1)
        return art

    def _normalize_coerce_reviews(self, value):
        self.api.Log('reviews normalization')
        source = self.api.Prefs['review_source'].strip()
        if source == 'Отключено':
            return []
        if source == 'Rotten Tomatoes' and value.get('rt'):
            return value.get('rt')
        else:
            return value.get('kp')

    def _normalize_default_setter_audience_rating_image(self, document):
        source = self.api.Prefs['rating_source'].strip()
        if source == 'Rotten Tomatoes':
            return document['ratings'].get('rt', {}).get('audience_rating_image')
        return ''

    def _normalize_default_setter_rating_image(self, document):
        source = self.api.Prefs['rating_source'].strip()
        if source == 'IMDb':
            return 'imdb://image.rating'
        elif source == 'Rotten Tomatoes':
            return document['ratings'].get('rt', {}).get('rating_image')
        return ''

    def _normalize_default_setter_audience_rating(self, document):
        source = self.api.Prefs['rating_source'].strip()
        if source == 'Rotten Tomatoes':
            return document['ratings'].get('rt', {}).get('audience_rating', float(0))
        return float(0)

    def _normalize_default_setter_rating(self, document):
        self.api.Log('rating source = %s', self.api.Prefs['rating_source'])
        source = self.api.Prefs['rating_source'].strip()

        rating_source = {
            'Rotten Tomatoes'   : document['ratings'].get('rt', {}).get('rating'),
            'IMDb'              : document['ratings'].get('imdb'),
            'The Movie Database': document['ratings'].get('tmdb'),
            u'Кинопоиск'         : document['ratings'].get('kp')
        }

        return rating_source[source] \
            or rating_source['Rotten Tomatoes'] \
            or rating_source['IMDb'] \
            or rating_source['The Movie Database'] \
            or rating_source['Kinopoisk']


def parse_meta(metadata_dict, metadata, api):
    try:
        if not metadata or not metadata.attrs:
            return
    except AttributeError:
        api.Log('WARNING: Framework not new enough to use One True Agent')
        return

    for attr_name, attr_obj in metadata.attrs.iteritems():
        if type(attr_obj) == api.Framework.modelling.attributes.SetObject:
            attr_obj.clear()

        if attr_name not in metadata_dict:
            continue

        dict_value = metadata_dict[attr_name]
        try:
            if isinstance(dict_value, list):

                attr_obj.clear()
                for val in dict_value:
                    attr_obj.add(val)

            elif isinstance(dict_value, dict):
                if attr_name in ['posters', 'art', 'themes']:  # Can't access MapObject, so have to write these out

                    for k, v in dict_value.iteritems():
                        if isinstance(v, tuple):
                            try: attr_obj[k] = api.Proxy.Preview(api.HTTP.Request(v[0]).content, sort_order=v[1])
                            except: pass
                        else:
                            try: attr_obj[k] = api.Proxy.Preview(api.HTTP.Request(v[0]).content)
                            except: pass

                    attr_obj.validate_keys(dict_value.keys())

                else:
                    for k, v in dict_value.iteritems():
                        attr_obj[k] = v
            else:
                attr_obj.setcontent(dict_value)
        except:
            api.Log.Error('Error while setting attribute %s with value %s' % (attr_name, dict_value), exc_info=True)


def prepare_meta(metadata_dict, metadata, app):
    v = MovieValidator(api=app.api, agent_type=app.agent_type, allow_unknown=True)
    v.validate(metadata_dict, movie_schema)
    app.trace('#### original metadata = %s', metadata_dict)
    app.trace('#### normalized metadata = %s', v.document)
    app.trace('#### metadata errors = %s', v.errors)

    metadata_dict = v.document

    with configure_scope() as scope:
        scope.set_extra("metadata_dict", metadata_dict)

    parse_meta(metadata_dict, metadata, app.api)

    for extra in metadata_dict.get('clips', []):
        metadata.extras.add(extra['extra'])

    # tv series
    for season_num, season_data in metadata_dict.get('seasons', {}).iteritems():
        for episode_num, episode_data in season_data['episodes'].iteritems():
            episode = metadata.seasons[season_num].episodes[episode_num]
            episode.title = episode_data['title']
            episode.originally_available_at = episode_data['originally_available_at']
            episode.absolute_index = episode_data['absolute_index']

    # staff
    if app.agent_type == 'movie':
        metadata.directors.clear()
        metadata.writers.clear()
        metadata.producers.clear()

    metadata.roles.clear()
    for staff_type, staff_list in metadata_dict.get('staff', {}).items():
        for staff in staff_list:
            if hasattr(metadata, staff_type):
                meta_staff = getattr(metadata, staff_type).new()
                if app.api.Prefs['actors_eng'] and staff.get('nameEN'):
                    meta_staff.name = staff.get('nameEN', '')
                else:
                    meta_staff.name = staff.get('nameRU', '')
                meta_staff.photo = staff.get('photo', '')
                meta_staff.role = staff.get('role', '')

    metadata.reviews.clear()
    for review in metadata_dict.get('reviews', []):
        r = metadata.reviews.new()
        r.author = review.get('author')
        r.source = review.get('source')
        r.image = review.get('image')
        r.link = review.get('link')
        r.text = review.get('text')
