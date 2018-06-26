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
    'title': {'type': 'string'},
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
    'countries': {'type': 'dict', 'valueschema': {'type': 'string'}},
    'genres': {'type': 'dict', 'valueschema': {'type': 'string'}},
    'posters': {'type': 'dict', 'schema': 'staff', 'valueschema': {'type': 'string'}},
    'art': {'type': 'dict', 'schema': 'staff', 'valueschema': {'type': 'string'}},
    'banners': {'type': 'dict'},
    'themes': {'type': 'dict'},
    'chapters': {'type': 'dict'},
    'extras': {'type': 'dict', 'valueschema': {'type': 'string'}},
    'similar': {'type': 'dict', 'valueschema': {'type': 'string'}},
    'rating': {'type': 'string'},
    'audience_rating': {'type': 'string'},
    'rating_image': {'type': 'string'},
    'audience_rating_image': {'type': 'string'}
}

class MovieValidator(Validator):
    pass

def check_meta(meta, l):
    v = Validator()
    v.validate(meta, movie_schema)
    l('errors = %s', v.errors)
