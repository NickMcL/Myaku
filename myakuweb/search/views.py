"""Views for the search for Myaku web."""

import functools
import logging
import math
import uuid
from dataclasses import dataclass
from datetime import datetime
from pprint import pformat
from typing import Callable, List, NamedTuple

import romkan
from django.conf import settings
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render

from myaku import utils
from myaku.datastore import DataAccessMode, Query, SearchResult
from myaku.datastore.database import CrawlDb, SearchResultPage
from myaku.datatypes import JpnArticle
from search import tasks
from search.article_preview import SearchResultArticlePreview

DEFAULT_QUERY_CONVERT_TYPE = 'hira'
SESSION_USER_ID_KEY = 'user_id'

_log = logging.getLogger(__name__)

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


def get_day_ordinal_suffix(day: int) -> str:
    """Get the ordinal suffix for a day (e.g. 1 -> st, 2 -> nd, ...)."""
    if not (1 <= day <= 31):
        raise ValueError('Not a valid day of the month: {}'.format(day))

    if 4 <= day <= 20 or 24 <= day <= 30:
        return 'th'
    return ['st', 'nd', 'rd'][(day % 10) - 1]


def humanize_date(dt: datetime) -> str:
    """Convert the datetime to a string with a nice human-readable date.

    Args:
        dt: datetime to convert.

    Returns:
        If the datetime is within a week of now, a string stating how many
        days ago the datetime was (i.e. today, yesterday, 2 days ago, ...).
        If the datetime is not within a week, a formatted date string in the
        form "Jan 1st, 2019".
    """
    days_since_dt = (datetime.utcnow() - dt).days
    if days_since_dt == 0:
        return 'today'
    elif days_since_dt == 1:
        return 'yesterday'
    elif days_since_dt < 7:
        return '{} days ago'.format(days_since_dt)
    else:
        return '{month} {day}{ordinal}, {year}'.format(
            month=dt.strftime('%b'), day=str(dt.day),
            ordinal=get_day_ordinal_suffix(dt.day), year=str(dt.year)
        )


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
    """Manager for all resource links for a query."""

    @utils.add_debug_logging
    def __init__(self, query: Query) -> None:
        """Create the resource link sets for the given query."""
        self._query_str = query.query_str

        self.resource_link_sets: List[ResourceLinkSet] = []
        self.resource_link_sets.append(self._create_jpn_eng_dict_links())
        self.resource_link_sets.append(self._create_sample_sentence_links())
        self.resource_link_sets.append(self._create_jpn_dict_links())

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
class QueryArticleResultSet(object):
    """The set of article results of a query of the Myaku db."""

    def __init__(self, query: Query) -> None:
        """Query the Myaku db to get the article result set for query."""
        with CrawlDb(DataAccessMode.READ) as db:
            result_page = db.search_articles(query)

        self._set_surrounding_page_nums(result_page)
        self.total_results = result_page.total_results

        _log.debug(
            'Creating %d query article results',
            len(result_page.search_results)
        )
        self.ranked_article_results = [
            QueryArticleResult(a) for a in result_page.search_results
        ]
        _log.debug('Finished creating query article results')

    def _set_surrounding_page_nums(
            self, result_page: SearchResultPage
    ) -> None:
        """Set the next and previous page numbers for the result set."""
        total_pages = math.ceil(
            result_page.total_results / CrawlDb.SEARCH_RESULTS_PAGE_SIZE
        )
        if result_page.query.page_num < total_pages:
            self.next_page_num = result_page.query.page_num + 1
        else:
            self.next_page_num = None

        if result_page.query.page_num > 1:
            self.previous_page_num = result_page.query.page_num - 1
        else:
            self.previous_page_num = None


class QueryArticleResult(object):
    """A single article result of a query of the Myaku db."""

    def __init__(self, search_result: SearchResult) -> None:
        """Populate article result data using given search result."""
        self.article = search_result.article
        self.matched_base_forms = search_result.matched_base_forms
        self.quality_score = search_result.quality_score
        self.instance_count = len(search_result.found_positions)
        self.tags = self._get_tags(search_result.article)
        self.preview = SearchResultArticlePreview(search_result)

        self.publication_date_str = humanize_date(
            search_result.article.publication_datetime
        )
        self.last_updated_date_str = humanize_date(
            search_result.article.last_updated_datetime
        )
        self.display_last_updated_date = (
            self._should_display_last_updated_datetime(search_result.article)
        )

    def _should_display_last_updated_datetime(
        self, article: JpnArticle
    ) -> bool:
        """Determine if last updated datetime should be displayed for article.

        The last updated datetime is not worth displaying if it's close to the
        publication date.

        Additionally, if the publication date is older, the amount of time
        between publication and the update must be greater in order for the
        update to be worth displaying.

        Args:
            article: Article to determine if its last updated datetime should
                be displayed.

        Returns:
            True if the last updated datetime should be displayed, or False if
            it shouldn't be displayed.
        """
        days_since_update = (
            (article.last_updated_datetime - article.publication_datetime).days
        )
        days_since_publish = (
            (datetime.utcnow() - article.publication_datetime).days
        )

        if (days_since_update < 1
                or is_very_recent(article.publication_datetime)):
            return False

        if (is_very_recent(article.last_updated_datetime)
                or days_since_publish < 180 and days_since_update > 30
                or days_since_publish < 365 and days_since_update > 90
                or days_since_publish < 365 * 2 and days_since_update > 180
                or days_since_update > 365):
            return True

        return False

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


def log_request_response(func: Callable) -> Callable:
    """Log the request and returned response for a request handler."""
    @functools.wraps(func)
    def log_request_response_wrapper(request, *args, **kwargs):
        _log.info('Handling request: %s', request)
        _log.info('Request meta:\n%s', pformat(request.META))
        response = func(request, *args, **kwargs)
        _log.info('Returning response: %s', response)
        return response

    return log_request_response_wrapper


def get_request_convert_type(request: HttpRequest) -> str:
    """Get the romaji conversion type for the request.

    If no convert_type parameter is in the query parameters for the request,
    tries to use the convert_type from the session instead.

    Will update the request session with the convert_type value for the request
    as well.
    """
    if 'convert_type' in request.GET:
        request.session['convert_type'] = request.GET['convert_type']
        return request.GET['convert_type']
    elif 'convert_type' in request.session:
        return request.session['convert_type']
    else:
        request.session['convert_type'] = DEFAULT_QUERY_CONVERT_TYPE
        return DEFAULT_QUERY_CONVERT_TYPE


@utils.add_debug_logging
def get_request_query(request: HttpRequest) -> str:
    """Get the query for a request.

    Converts any romaji in the query string to Japanese using the conversion
    method (conv) specified in the request.
    """
    query = utils.normalize_char_width(request.GET.get('q', ''))
    convert_type = get_request_convert_type(request)
    if convert_type == 'hira':
        query = romkan.to_hiragana(query)
    elif convert_type == 'kata':
        query = romkan.to_katakana(query)

    return query


def get_request_page_num(request: HttpRequest) -> int:
    """Get the page number for a request.

    If the page number given in the GET parameters for the request is not a
    valid page number, will return 1.

    If the page number given in the GET parameters for the request is large
    than MAX_PAGE_NUMBER, will return MAX_PAGE_NUMBER.
    """
    page_num_str = request.GET.get('p', '1')
    try:
        page_num = int(page_num_str)
    except ValueError:
        page_num = 1

    if page_num < 1:
        page_num = 1
    elif page_num > settings.MAX_PAGE_NUM:
        page_num = settings.MAX_PAGE_NUM

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
        query_str=get_request_query(request),
        page_num=get_request_page_num(request),
        user_id=get_request_user_id(request)
    )


@log_request_response
def index(request: HttpRequest) -> HttpResponse:
    """Search page request handler."""
    convert_type = get_request_convert_type(request)
    if len(request.GET.get('q', '')) == 0:
        return render(
            request, 'search/start.html', {'convert_type': convert_type}
        )

    query = create_query(request)
    query_result_set = QueryArticleResultSet(query)
    resource_links = QueryResourceLinks(query)

    _log.debug('Starting "%s" query page render', query)
    response = render(
        request, 'search/results.html',
        {
            'query': query.query_str,
            'page_num': query.page_num,
            'convert_type': convert_type,
            'max_page_num': settings.MAX_PAGE_NUM,
            'query_result_set': query_result_set,
            'resource_links': resource_links,
        }
    )
    _log.debug('Finished "%s" query page render', query)

    # Async load the surrounding pages into the cache in memory for the current
    # query being made for this session.
    if (query_result_set.next_page_num is not None
            or query_result_set.previous_page_num is not None):
        tasks.cache_surrounding_pages_for_user.delay(query)

    return response
