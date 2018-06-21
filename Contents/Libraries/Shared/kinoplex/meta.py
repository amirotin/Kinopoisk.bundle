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
            api.Log('Error while setting attribute %s with value %s' % (attr_name, dict_value), exc_info=True)

def prepare_meta(metadata_dict, metadata, api):
    metadata_dict['reviews'] = metadata_dict.get('rotten_reviews')

    if metadata_dict.get('itunes_poster', {}):
        metadata_dict['posters'][metadata_dict['itunes_poster']['poster_url']] = (metadata_dict['itunes_poster']['thumb_url'], 1)

    for poster, thumb in metadata_dict.get('tmdb_posters', {}).iteritems():
        metadata_dict['posters'][poster] = (thumb[0], thumb[1]+1)

    for art, thumb in metadata_dict.get('tmdb_art', {}).iteritems():
        metadata_dict['art'][art] = thumb

    if api.Prefs['ratings'].strip() == 'Rotten Tomatoes' and metadata_dict['rt_raings']:
        metadata_dict.update(metadata_dict['rt_raings'])
    elif api.Prefs['ratings'].strip() == 'IMDb' and metadata_dict['imdb_rating']:
        metadata_dict['rating'] = metadata_dict['imdb_rating']
    elif api.Prefs['ratings'].strip() == 'The Movie Database' and metadata_dict['tmbp_rating']:
        metadata_dict['rating'] = metadata_dict['tmbp_rating']
    else:
        metadata_dict['rating'] = metadata_dict['kp_rating']

    parse_meta(metadata_dict, metadata, api)
    for extra in metadata_dict.get('extra_clips', {}):
        metadata.extras.add(extra['extra'])

    for extra in metadata_dict.get('iva_extras', {}):
        metadata.extras.add(extra['extra'])

    # staff
    metadata.directors.clear()
    metadata.writers.clear()
    metadata.producers.clear()
    metadata.roles.clear()
    for staff_type, staff_list in metadata_dict.get('staff', []).items():
        for staff in staff_list:
            meta_staff = getattr(metadata, staff_type).new()
            meta_staff.name = staff.get('nameRU', '')
            meta_staff.photo = staff.get('photo', '')
            meta_staff.role = staff.get('role', '')