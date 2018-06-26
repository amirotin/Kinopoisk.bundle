from collections import defaultdict
from user_agent import generate_user_agent
import urllib

class mydict(defaultdict):
    def __getattr__(self, attr):
        return self[attr]
    def __setattr__(self, attr, val):
        self[attr] = val

tree = lambda: mydict(tree)
config = tree()

# agent config section
config['contrib']['Movies'] = ['com.plexapp.agents.kinopoiskru', 'com.plexapp.agents.themoviedb', 'com.plexapp.agents.imdb']
config['contrib']['TV_Shows'] = ['com.plexapp.agents.themoviedb', 'com.plexapp.agents.thetvdb']

# sources section
# kinopoisk api
config['kinopoisk']['api']['base'] = 'https://ext.kinopoisk.ru/ios/5.0.0/%s'
config['kinopoisk']['api']['search'] = config.kinopoisk.api.base % 'getKPLiveSearch?keyword=%s'
config['kinopoisk']['api']['film_details'] = config.kinopoisk.api.base % 'getKPFilmDetailView?filmID=%s&still_limit=50&sr=1'
config['kinopoisk']['api']['similar_films'] = config.kinopoisk.api.base % 'getKPFilmsList?filmID=%s&type=kp_similar_films'   #kp_sequels_and_prequels_films, kp_related_films
config['kinopoisk']['api']['staff'] = config.kinopoisk.api.base % 'getStaffList?filmID=%s&type=all'
config['kinopoisk']['api']['film_reviews'] = config.kinopoisk.api.base % 'getKPReviews?filmID=%s&type=0&sortType=0'
config['kinopoisk']['api']['gallery'] = config.kinopoisk.api.base % 'getGallery?filmID=%s'
config['kinopoisk']['api']['series'] = config.kinopoisk.api.base % 'getKPSeriesList?serialID=%s'
config['kinopoisk']['api']['hash'] = 'IDATevHDS7'
config['kinopoisk']['api']['hash_headers'] = ['x-signature','x-timestamp']
config['kinopoisk']['api']['headers'] = {
    'Image-Scale': '3',
    'countryID': '2',
    'cityID': '1',
    'ClientId': '55decdcf6d4cd1bcaa1b3856',
    'Accept': 'application/json',
    'device': 'android',
    'Android-Api-Version': '22',
    'User-Agent': 'Android client (4.4 / api22),ru.kinopoisk/4.2.1 (52)'
}

config['kinopoisk']['main']['search'] = 'https://www.kinopoisk.ru/search/suggest/?q=%s&topsuggest=true&ajax=1'
config['kinopoisk']['main']['headers'] = lambda:{
    'Host': 'www.kinopoisk.ru',
    'Accept': 'text/html, application/xhtml+xml, image/jxr, */*',
    'Accept-Encoding':'gzip, deflate',
    'Accept-Language':'en-US,en;q=0.8,ru;q=0.7,uk;q=0.5,de-DE;q=0.3,de;q=0.2',
    'User-agent': generate_user_agent()
}

config['kinopoisk']['main']['yasearch'] = 'https://suggest-kinopoisk.yandex.net/suggest-kinopoisk?srv=kinopoisk&part=%s&nocookiesupport=yes'

config['kinopoisk']['extras']['base'] = 'https://www.kinopoisk.ru/film/%s/video/'
config['kinopoisk']['extras']['re'] = "//table[ancestor::table[2]]//div[descendant::div]/a[@class='all']"
config['kinopoisk']['extras']['url'] = 'https://widgets.kinopoisk.ru/discovery/api/trailers?params=%s'
config['kinopoisk']['extras']['headers'] = lambda:{
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': '*/*',
    'Accept-Encoding':'gzip, deflate, br',
    'Accept-Language':'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'User-Agent': generate_user_agent(),
    'DNT':'1'
}
config['kinopoisk']['extras']['clip_url'] = '//video.kinopoisk.ru/iframe/kinopoisk-trailers/%s'


#config['kinopoisk']['extras']['re']['tr'] = "//table[ancestor::table[2]]//tr[*//a[@onclick] and (*//div[contains(@class,'flag2')] or not(*//div[contains(@class,'flag') and span]))]"
#config['kinopoisk']['extras']['re']['title'] = ".//div/a[not(@onclick)]/text()"
#config['kinopoisk']['extras']['re']['views'] = ".//div//td[5]/text()"
#config['kinopoisk']['extras']['re']['img'] = './/following-sibling::tr[1]//div[@class="listTrailerShare"]/attribute::data-url'
#config['kinopoisk']['extras']['re']['qual'] = ".//following-sibling::tr[2]//tr[*/a[contains(@href,'kp.cdn.yandex.net')]]"




#config['kinopoisk']['plus']['base'] = 'https://plus.kinopoisk.ru/%s'
#config['kinopoisk']['plus']['search'] = config.kinopoisk.plus.base % 'search/%s/?text=%s&nocookiesupport=yes'

#config['kinopoisk']['plus']['headers'] = {
#    'X-Requested-With': 'XMLHttpRequest',
#    'Accept': '*/*',
#    'Accept-Encoding':'gzip, deflate, br',
#    'Accept-Language':'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
#    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36',
#    'DNT':'1'
#}
#config['kinopoisk']['plus']['extras']['base'] = 'https://plus.kinopoisk.ru/film/%s/details/art/trailer/'
#config['kinopoisk']['plus']['extras']['list'] = 'https://plus.kinopoisk.ru/film/%s/get-gallery/trailer/%s/'
#config['kinopoisk']['plus']['extras']['files'] = 'https://static.video.yandex.net/get/kinopoisk-trailers/%s/0h.xml'


config['kinopoisk']['actor'] = 'https://st.kp.yandex.net/images/actor_iphone/iphone360_%s.jpg'
config['kinopoisk']['thumb'] = 'https://st.kp.yandex.net/images/film_iphone/iphone360_%s.jpg'

config['score']['penalty']['year'] = 20
config['score']['penalty']['rating'] = 5
config['score']['besthit'] = 95

config['tmdb']['hash_base'] = 'https://meta.plex.tv'
config['tmdb']['base'] = 'http://127.0.0.1:32400/services/tmdb?uri=%s'
config['tmdb']['config'] = config.tmdb.base % urllib.quote_plus('/configuration')
# Movies
config['tmdb']['search'] = lambda *x: config.tmdb.base % urllib.quote_plus('/search/movie?query=%s&year=%s&language=%s&include_adult=%s' % x)
config['tmdb']['movie'] = lambda *x: config.tmdb.base % urllib.quote_plus('/movie/%s?append_to_response=releases,credits,created_by,production_companies,images,alternative_titles&language=%s&include_image_language=en,ru,null' % x)
config['tmdb']['recom'] = lambda *x: config.tmdb.base % urllib.quote_plus('/movie/%s/recommendations' % x)
config['tmdb']['images'] = lambda *x: config.tmdb.base % urllib.quote_plus('/movie/%s/images' % x)
config['tmdb']['ump_base'] = 'http://127.0.0.1:32400/services/ump/matches?%s'
config['tmdb']['ump_search'] = config.tmdb.ump_base % 'type=1&title=%s&year=%s&plexHash=%s&lang=%s&manual=%s'

config['tmdb']['api']['base'] = 'https://api.themoviedb.org/3%s'
config['tmdb']['api']['key'] = ('190bcf1a7c7cbbf8074ad962ec8c8776',)
config['tmdb']['api']['config'] = config.tmdb.api.base % '/configuration?api_key=%s' % config.tmdb.api.key
config['tmdb']['api']['search'] = lambda *x: config.tmdb.api.base % '/search/movie?query=%s&year=%s&language=%s&include_adult=%s&api_key=%s' % (x+config.tmdb.api.key)
config['tmdb']['api']['movie'] = lambda *x: config.tmdb.api.base % '/movie/%s?append_to_response=releases,credits,created_by,production_companies,images,alternative_titles&language=%s&include_image_language=en,ru,null&api_key=%s' % (x+config.tmdb.api.key)
config['tmdb']['api']['recom'] = lambda *x: config.tmdb.api.base % '/movie/%s/recommendations?api_key=%s' % (x+config.tmdb.api.key)
config['tmdb']['api']['images'] = lambda *x: config.tmdb.api.base % '/movie/%s/images?api_key=%s' % (x+config.tmdb.api.key)


config['itunes']['base'] = 'http://ax.itunes.apple.com/WebObjects/MZStoreServices.woa/wa/%s'
config['itunes']['lookup'] = config.itunes.base % 'wsLookup?id=%s'
config['itunes']['poster'] = '2100x2100bb-92'
config['itunes']['preview'] = '320x480bb-92'

config['itunes']['trakt_base'] = 'https://trakt.tv/%s'
config['itunes']['trakt_imdb'] = config.itunes.trakt_base % '/search/imdb/%s'
config['itunes']['trakt_re_search'] = "//div[@data-type='movie']/meta[@itemprop='url']/attribute::content"
config['itunes']['trakt_streaming'] = '%s/streaming_links'
config['itunes']['trakt_re_lnk'] = "//a[contains(@data-source,'itunes')]/attribute::href"

config['itunes']['omdb'] = 'http://www.omdbapi.com/?i=%s&apikey=58909a96&tomatoes=true'
config['itunes']['rt_re'] = "//section[@id='watch-it-now']//a[div/@id='itunesAffiliates']/attribute::href"

config['fanart']['movie'] = 'http://webservice.fanart.tv/v3/movies/%s'
config['fanart']['headers'] = lambda x : {'api-key':'060835d7ce393492157f135cfc25c050', 'client-key': x}

config['freebase']['base'] = 'https://meta.plex.tv/m/%s?lang=%s&ratings=1&reviews=1&extras=1'
config['freebase']['assets'] = 'iva://api.internetvideoarchive.com/2.0/DataService/VideoAssets(%s)?lang=%s&bitrates=%s&duration=%s&adaptive=%d&dts=%d'