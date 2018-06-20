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
    'posters': {'type': 'dict'},
    'art': {'type': 'dict'},
    'banners': {'type': 'dict'},
    'themes': {'type': 'dict'},
    'chapters': {'type': 'dict'},
    'extras': {'type': 'dict'},
    'similar': {'type': 'dict', 'valueschema': {'type': 'string'}},
    'rating': {},
    'audience_rating': {},
    'rating_image': {},
    'audience_rating_image': {}
}

class MovieValidator(Validator):
    pass