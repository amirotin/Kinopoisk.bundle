from cerberus import Validator, schema_registry

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
    'originally_available_at': {'type': 'date'},
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
    'reviews': {'type': 'list', 'default_setter': 'reviews'},
    'clips': {'type': 'list', 'default_setter': 'clips'},
    'similar': {'type': 'list', 'valueschema': {'type': 'string'}},
    'rating': {'type': 'float', 'default_setter': 'rating'},
    'audience_rating': {'type': 'string'},
    'rating_image': {'type': 'string'},
    'audience_rating_image': {'type': 'string'}
}

class MovieValidator(Validator):
    def __init__(self, *args, **kwargs):
        super(MovieValidator, self).__init__(*args, **kwargs)
        self.api = kwargs.get('api')

    def _normalize_default_setter_clips(self, document):
        extras = []
        self.api.Log('trailers pref = %s', self.api.Prefs['trailers'].strip())
        if self.api.Prefs['trailers'].strip() == "Kinopoisk" or self.api.Prefs['trailers'].strip() == "All":
            extras += document.get('kp_extras', [])
        if self.api.Prefs['trailers'].strip() == "IVA" or self.api.Prefs['trailers'].strip() == "All":
            extras += document.get('iva_extras', [])

        if self.api.Prefs['extra_all']:
            return extras

        return filter(lambda x: x['type'] in set(['trailer', 'primary_trailer']), extras)

    def _normalize_default_setter_posters(self, document):
        posters = {}
        if document.get('itunes_poster', {}):
            posters[document['itunes_poster']['poster_url']] = (document['itunes_poster']['thumb_url'], 1)

        for image, thumb in document.get('tmdb_posters', {}).iteritems():
            posters[image] = (thumb[0], thumb[1]+1)

        return posters

    def _normalize_default_setter_art(self, document):
        art = {}
        for image, thumb in document.get('tmdb_art', {}).iteritems():
            art[image] = thumb

        return art

    def _normalize_default_setter_reviews(self, document):
        if self.api.Prefs['reviews'].strip() == 'Rotten Tomatoes' and document.get('rotten_reviews'):
            return document.get('rotten_reviews')
        else:
            return document.get('kp_reviews')

    def _normalize_default_setter_rating(self, document):
        rating_source = {
            'Rotten Tomatoes'   : document.get('rt_ratings', {}).get('rating'),
            'IMDb'              : document.get('imdb_rating'),
            'The Movie Database': document.get('tmbp_rating'),
            'Kinopoisk'         : document.get('kp_rating')
        }
        rating = rating_source[self.api.Prefs['ratings'].strip()]
        if rating:
            return rating

        return rating_source['IMDb'] if rating_source['IMDb'] else rating_source['The Movie Database'] if rating_source['The Movie Database'] else rating_source['Kinopoisk']

def parse_meta(metadata_dict, metadata, api):
    try:
        if not metadata or not metadata.attrs:
            return
    except AttributeError:
        api.Log('WARNING: Framework not new enough to use One True Agent')  # TODO: add a more official log message about version number when available
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

def prepare_meta(metadata_dict, metadata, api):
    v = MovieValidator(api=api, allow_unknown = True)
    metadata_dict = v.normalized(metadata_dict, movie_schema, always_return_document=True)
    v.validate(metadata_dict, movie_schema)
    api.Log('normalized metadata = %s', metadata_dict)
    api.Log('metadata errors = %s', v.errors)

    parse_meta(metadata_dict, metadata, api)

    for extra in metadata_dict.get('clips', {}):
        metadata.extras.add(extra['extra'])

    # staff
    metadata.directors.clear()
    metadata.writers.clear()
    metadata.producers.clear()
    metadata.roles.clear()
    for staff_type, staff_list in metadata_dict.get('staff', {}).items():
        for staff in staff_list:
            meta_staff = getattr(metadata, staff_type).new()
            if api.Prefs['actors_eng'] and staff.get('nameEN'):
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
