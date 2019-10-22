"""Views for the search API for MyakuWeb."""

import logging
import math
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, NamedTuple

import romkan
from django.conf import settings
from django.http import JsonResponse
from django.http.request import HttpRequest

from myaku import utils
from myaku.datastore import DataAccessMode, Query, SearchResult
from myaku.datastore.database import CrawlDb
from myaku.datatypes import JpnArticle
from search import tasks
from search.article_preview import (
    SearchResultArticlePreview,
    convert_sample_text_to_json,
)
from search.request_validation import (
    AllowableValueValidator,
    IntRangeValidator,
    ParamValidator,
    StrLenValidator,
    validate_request_params,
)

_log = logging.getLogger(__name__)

SESSION_USER_ID_KEY = 'user_id'

REQUEST_QUERY_KEY = 'q'
REQUEST_PAGE_NUM_KEY = 'p'
REQUEST_KANA_CONVERT_TYPE_KEY = 'conv'

KANA_CONVERT_TYPE_HIRAGANA = 'hira'
KANA_CONVERT_TYPE_KATAKANA = 'kata'
KANA_CONVERT_TYPE_NONE = 'none'
KANA_CONVERT_TYPES = {
    KANA_CONVERT_TYPE_HIRAGANA,
    KANA_CONVERT_TYPE_KATAKANA,
    KANA_CONVERT_TYPE_NONE,
}

MAX_QUERY_LEN = 120

_ARTICLE_LEN_GROUPS = [
    (700, 'Short length'),
    (1200, 'Medium length'),
    (2000, 'Long length')
]
_ARTICLE_LEN_GROUP_MAX_NAME = 'Very long length'

_VERY_RECENT_DAYS = 7

# Enable logging for both the myaku package and this search package to the same
# files.
utils.toggle_myaku_package_log(filename_base='myakuweb')
utils.toggle_myaku_package_log(filename_base='myakuweb', package='search')


def is_very_recent(dt: datetime) -> bool:
    """Return True if the datetime is considered very recent."""
    days_since_dt = (datetime.utcnow() - dt).days
    return days_since_dt <= _VERY_RECENT_DAYS


def json_serialize_datetime(dt: datetime) -> str:
    """Serialize a naive datetime to a UTC ISO format string."""
    return dt.isoformat(timespec='seconds') + 'Z'


class ResourceLink(NamedTuple):
    """Info for a link to a resource website."""
    resource_name: str
    link: str


@dataclass
class ResourceLinkSet(object):
    """Info for a set of links to a category of resources websites."""
    set_name: str
    resource_links: List[ResourceLink]


@dataclass
class QueryResourceLinks(object):
    """Resource links for a query."""

    @utils.add_debug_logging
    def __init__(self, query_str: str) -> None:
        """Create the resource link sets for the given query."""
        self._query_str = query_str

        self.resource_link_sets: List[ResourceLinkSet] = []
        self.resource_link_sets.append(self._create_jpn_eng_dict_links())
        self.resource_link_sets.append(self._create_sample_sentence_links())
        self.resource_link_sets.append(self._create_jpn_dict_links())

    def json(self) -> Dict[str, Any]:
        """Return the resource link data in a JSON format."""
        link_sets_json = []
        for link_set in self.resource_link_sets:
            link_json = []
            for link in link_set.resource_links:
                link_json.append({
                    'resourceName': link.resource_name,
                    'link': link.link,
                })

            link_sets_json.append({
                'setName': link_set.set_name,
                'resourceLinks': link_json,
            })

        return {
            'convertedQuery': self._query_str,
            'resourceLinkSets': link_sets_json,
        }

    def _create_jpn_eng_dict_links(self) -> ResourceLinkSet:
        """Create link set for Jpn->Eng dictionary sites."""
        link_set = ResourceLinkSet('Jpn-Eng Dictionaries', [])
        link_set.resource_links.append(self._create_jisho_query_link())
        link_set.resource_links.append(self._create_weblio_ejje_query_link())

        return link_set

    def _create_jisho_query_link(self) -> ResourceLink:
        """Create a link to query Jisho.org."""
        return ResourceLink(
            'Jisho.org', f'https://jisho.org/search/{self._query_str}'
        )

    def _create_alc_query_link(self) -> ResourceLink:
        """Create a link to query ALC.

        ALC doesn't support different query types, so match_type is not used.
        """
        return ResourceLink(
            'ALC', 'https://eow.alc.co.jp/search?q={}'.format(self._query_str)
        )

    def _create_weblio_ejje_query_link(self) -> ResourceLink:
        """Create a link to query Weblio's Jpn->Eng dictionary."""
        return ResourceLink(
            'Weblio EJJE', f'https://ejje.weblio.jp/content/{self._query_str}'
        )

    def _create_sample_sentence_links(self) -> ResourceLinkSet:
        """Create link set for Jpn->Eng sample sentence sites."""
        link_set = ResourceLinkSet('Jpn-Eng Sample Sentences', [])
        link_set.resource_links.append(self._create_tatoeba_query_link())
        link_set.resource_links.append(
            self._create_weblio_sentences_query_link()
        )

        return link_set

    def _create_weblio_sentences_query_link(self) -> ResourceLink:
        """Create a link to query Weblio's Jpn->Eng sample sentence search.

        Weblio's sample sentence search doesn't support different query types,
        so match_type is not used.
        """
        return ResourceLink(
            'Weblio EJJE',
            f'https://ejje.weblio.jp/sentence/content/"{self._query_str}"'
        )

    def _create_tatoeba_query_link(self) -> ResourceLink:
        """Create a link to query the Tatoeba sample sentence project."""
        return ResourceLink(
            'Tatoeba',
            f'https://tatoeba.org/eng/sentences/search'
            f'?query=%3D{self._query_str}&from=jpn&to=eng'
        )

    def _create_jpn_dict_links(self) -> ResourceLinkSet:
        """Create link set for Japanese dictionary sites."""
        link_set = ResourceLinkSet('Jpn Dictionaries', [])
        link_set.resource_links.append(self._create_goo_query_link())
        link_set.resource_links.append(self._create_weblio_jpn_query_link())

        return link_set

    def _create_goo_query_link(self) -> ResourceLink:
        """Create a link to query Goo."""
        return ResourceLink(
            'Goo',
            f'https://dictionary.goo.ne.jp/srch/all/{self._query_str}/m1u/'
        )

    def _create_weblio_jpn_query_link(self) -> ResourceLink:
        """Create a link to query Weblio's JPN dictionary."""
        return ResourceLink(
            'Weblio', f'https://www.weblio.jp/content/{self._query_str}'
        )


@utils.add_method_debug_logging
class SearchQueryResult(object):
    """Search query result for a query of the Crawl db."""

    def __init__(self, query: Query) -> None:
        """Query the Crawl db to get the article results for query."""
        with CrawlDb(DataAccessMode.READ) as db:
            result_page = db.search_articles(query)

        self.query = query
        self.total_results = result_page.total_results

        total_pages = math.ceil(
            result_page.total_results / CrawlDb.SEARCH_RESULTS_PAGE_SIZE
        )
        self.max_page_reached = (
            query.page_num >= settings.MAX_SEARCH_RESULT_PAGE
        )
        self.has_next_page = (
            query.page_num < total_pages and not self.max_page_reached
        )

        _log.debug(
            'Creating %d search query article results',
            len(result_page.search_results)
        )
        self.ranked_article_results = [
            SearchQueryArticleResult(r) for r in result_page.search_results
        ]
        _log.debug('Finished creating search query article results')

    def json(self) -> Dict[str, Any]:
        """Get JSON for the search result data."""
        return {
            'convertedQuery': self.query.query_str,
            'totalResults': self.total_results,
            'pageNum': self.query.page_num,
            'hasNextPage': self.has_next_page,
            'maxPageReached': self.max_page_reached,
            'articleResults': [
                r.json() for r in self.ranked_article_results
            ],
        }


class SearchQueryArticleResult(object):
    """A single article result of a search query of the Crawl db."""

    def __init__(self, search_result: SearchResult) -> None:
        """Populate article result data using given search result."""
        article = search_result.article
        self.article_id = article.database_id
        if not article.title or article.title.isspace():
            self.title = '<Untitled article>'
        else:
            self.title = article.title

        self.source_name = article.source_name
        self.source_url = article.source_url
        self.instance_count = len(search_result.found_positions)
        self.tags = self._get_tags(article)

        self.publication_datetime = article.publication_datetime
        self.last_updated_datetime = article.last_updated_datetime

        self.preview = SearchResultArticlePreview(search_result)

    def json(self) -> Dict[str, Any]:
        """Get JSON for the article search result data."""
        main_sample_text = convert_sample_text_to_json(
            self.preview.main_sample_text
        )

        more_sample_texts = []
        for sample_text in self.preview.extra_sample_texts:
            more_sample_texts.append(
                convert_sample_text_to_json(sample_text)
            )

        return {
            'articleId': self.article_id,
            'title': self.title,
            'sourceName': self.source_name,
            'sourceUrl': self.source_url,
            'publicationDatetime':
                json_serialize_datetime(self.publication_datetime),
            'lastUpdatedDatetime':
                json_serialize_datetime(self.last_updated_datetime),
            'instanceCount': self.instance_count,
            'tags': self.tags,
            'mainSampleText': main_sample_text,
            'moreSampleTexts': more_sample_texts,
        }

    def _get_tags(self, article: JpnArticle) -> List[str]:
        """Get the tags applicable for the article."""
        tag_strs = []
        for len_group in _ARTICLE_LEN_GROUPS:
            if article.alnum_count < len_group[0]:
                tag_strs.append(len_group[1])
                break
        else:
            tag_strs.append(_ARTICLE_LEN_GROUP_MAX_NAME)

        if is_very_recent(article.last_updated_datetime):
            tag_strs.append('Very recent')

        if article.has_video:
            tag_strs.append('Video')
        return tag_strs


def get_request_convert_type(request: HttpRequest) -> str:
    """Get the romaji conversion type for the request.

    Updates the request session with the convert type value for the request as
    well.
    """
    convert_type = request.GET[REQUEST_KANA_CONVERT_TYPE_KEY]
    request.session[REQUEST_KANA_CONVERT_TYPE_KEY] = convert_type
    return convert_type


def get_request_query_str(request: HttpRequest) -> str:
    """Get the query string for a request.

    Converts any romaji in the query string to Japanese using the conversion
    method specified in the request.
    """
    query_str = utils.normalize_char_width(request.GET[REQUEST_QUERY_KEY])
    convert_type = get_request_convert_type(request)
    if convert_type == KANA_CONVERT_TYPE_HIRAGANA:
        query_str = romkan.to_hiragana(query_str)
    elif convert_type == KANA_CONVERT_TYPE_KATAKANA:
        query_str = romkan.to_katakana(query_str)

    return query_str


def get_request_page_num(request: HttpRequest) -> int:
    """Get the page number for a request.

    If the page number given in the GET parameters for the request is large
    than MAX_PAGE_NUMBER, will return MAX_PAGE_NUMBER instead.
    """
    page_num = int(request.GET[REQUEST_PAGE_NUM_KEY])
    if page_num > settings.MAX_SEARCH_RESULT_PAGE:
        page_num = settings.MAX_SEARCH_RESULT_PAGE
    return page_num


def get_request_user_id(request: HttpRequest) -> str:
    """Get the user ID from the session for the request.

    Will create the user ID and store it in the session for the request if it
    doesn't exist.
    """
    if SESSION_USER_ID_KEY not in request.session:
        request.session[SESSION_USER_ID_KEY] = uuid.uuid4().hex
    return request.session[SESSION_USER_ID_KEY]


def create_query(request: HttpRequest) -> Query:
    """Create a query object from the request data."""
    return Query(
        query_str=get_request_query_str(request),
        page_num=get_request_page_num(request),
        user_id=get_request_user_id(request)
    )


@validate_request_params([
    ParamValidator(
        REQUEST_QUERY_KEY, True, str,
        [StrLenValidator(1, MAX_QUERY_LEN)]
    ),
    ParamValidator(
        REQUEST_PAGE_NUM_KEY, True, int,
        [IntRangeValidator(1)]
    ),
    ParamValidator(
        REQUEST_KANA_CONVERT_TYPE_KEY, True, str,
        [AllowableValueValidator(KANA_CONVERT_TYPES)]
    ),
])
def search(request: HttpRequest) -> JsonResponse:
    """Handle search API requests.

    Searches the Crawl db for articles using the given query after applying the
    specified romaji->kana conversion, then returns the specified page of the
    query results.
    """
    query = create_query(request)
    query_result = SearchQueryResult(query)

    if query.page_num > 2 or query_result.has_next_page:
        tasks.cache_surrounding_pages.delay(query)

    return JsonResponse(query_result.json())


@validate_request_params([
    ParamValidator(
        REQUEST_QUERY_KEY, True, str,
        [StrLenValidator(1, MAX_QUERY_LEN)]
    ),
    ParamValidator(
        REQUEST_KANA_CONVERT_TYPE_KEY, True, str,
        [AllowableValueValidator(KANA_CONVERT_TYPES)]
    ),
])
def resource_links(request: HttpRequest) -> JsonResponse:
    """Handle resource links API requests.

    Returns sets of resource links for the given query with the specified
    romaji->kana conversion applied to it.
    """
    query_resource_links = QueryResourceLinks(get_request_query_str(request))
    return JsonResponse(query_resource_links.json())


@validate_request_params([])
def session_search_options(request: HttpRequest) -> JsonResponse:
    """Handle session search options API requests.

    Returns the search options currently set for the session. If an option is
    not specified in the session, its value will be null in the response.
    """
    return JsonResponse({
        'kanaConvertType': request.session.get(REQUEST_KANA_CONVERT_TYPE_KEY),
    })
