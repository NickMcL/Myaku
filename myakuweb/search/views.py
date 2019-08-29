"""Views for the search for Myaku web."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, NamedTuple

from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render

import myaku
from myaku.database import (DbAccessMode, JpnArticleQueryType,
                            JpnArticleSearchResult, MyakuCrawlDb)
from myaku.datatypes import JpnArticle, LexicalItemTextPosition

# If a found article for a query has many instances of the query in its text,
# the max number of instance sentences to show on the results page for that
# article.
_MAX_ARTICLE_INSTANCE_SAMPLES = 3

_ARTICLE_LEN_GROUPS = [
    (700, 'Short length'),
    (1200, 'Medium length'),
    (2000, 'Long length')
]
_ARTICLE_LEN_GROUP_MAX_NAME = 'Very long length'

_VERY_RECENT_DAYS = 7

myaku.utils.toggle_myaku_package_log()


def is_very_recent(dt: datetime) -> bool:
    """Returns True if the datetime is considered very recent."""
    days_since_dt = (datetime.utcnow() - dt).days
    return days_since_dt <= _VERY_RECENT_DAYS


def get_day_ordinal_suffix(day: int) -> str:
    """Gets the ordinal suffix for a day (e.g. 1 -> st, 2 -> nd, ...)."""
    if not (1 <= day <= 31):
        raise ValueError('Not a valid day of the month: {}'.format(day))

    if 4 <= day <= 20 or 24 <= day <= 30:
        return 'th'
    return ['st', 'nd', 'rd'][(day % 10) - 1]


def humanize_date(dt: datetime) -> str:
    """Converts the datetime to a string with a nice human-readable date.

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


class QueryMatchType(Enum):
    """Possible match types to use for a query."""
    EXACT_MATCH = 1
    STARTS_WITH = 2
    ENDS_WITH = 3


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
class SearchResultMatchingSentenceSegment(object):
    """A single segment of a sample sentence for an article search result.

    Attributes:
        is_match_segment: True if the text of this segment matches the searched
            query, and False otherwise.
        segment_text: Text for this segment of the sample sentence.
    """
    is_query_match: bool
    segment_text: str


@dataclass
class SearchResultMatchingSentence(object):
    """Data for a sample sentence for an article search result.

    Attributes:
        sentence_len: Total length of the sample sentence.
        article_pos_humanized: Human-readable string of the position of the
            matching sentence in the article.
        match_instance_count: How many instances of the searched query are in
            this sample sentence.
        segments: Segments that make up the sample sentence.
    """
    sentence_len: int
    article_pos_humanized: str
    match_instance_count: int
    segments: List[SearchResultMatchingSentenceSegment]

    def trim_whitespace(self):
        """Strips surrounding whitespace from the edge segments."""
        self.segments[0].segment_text = (
            self.segments[0].segment_text.lstrip()
        )
        self.segments[-1].segment_text = (
            self.segments[-1].segment_text.rstrip()
        )


class QueryResourceLinks(object):
    """Creates and manages all resource links for a query."""

    def __init__(self, query: str) -> None:
        """Creates the resource link sets for the given query."""
        self._query = query
        self._match_type = QueryMatchType.EXACT_MATCH

        self.resource_link_sets = []
        self.resource_link_sets.append(self._create_jpn_eng_dict_links())
        self.resource_link_sets.append(self._create_sample_sentence_links())
        self.resource_link_sets.append(self._create_jpn_dict_links())

    def _create_jpn_eng_dict_links(self) -> ResourceLinkSet:
        """Creates link set for Jpn->Eng dictionary sites."""
        link_set = ResourceLinkSet('Jpn-Eng Dictionaries', [])
        link_set.resource_links.append(self._create_jisho_query_link())
        link_set.resource_links.append(self._create_weblio_ejje_query_link())

        return link_set

    def _create_jisho_query_link(self) -> ResourceLink:
        """Creates a link to query Jisho.org."""
        website_name = 'Jisho.org'
        template_url = 'https://jisho.org/search/{}'

        if self._match_type == QueryMatchType.ENDS_WITH:
            return ResourceLink(
                website_name, template_url.format('*' + self._query)
            )
        return ResourceLink(website_name, template_url.format(self._query))

    def _create_alc_query_link(self) -> ResourceLink:
        """Creates a link to query ALC.

        ALC doesn't support different query types, so match_type is not used.
        """
        return ResourceLink(
            'ALC',
            'https://eow.alc.co.jp/search?q={}'.format(self._query)
        )

    def _create_weblio_ejje_query_link(self) -> ResourceLink:
        """Creates a link to query Weblio's Jpn->Eng dictionary."""
        website_name = 'Weblio EJJE'
        template_url = 'https://ejje.weblio.jp/content{{}}/{}'.format(
            self._query
        )

        if self._match_type == QueryMatchType.EXACT_MATCH:
            return ResourceLink(website_name, template_url.format(''))
        elif self._match_type == QueryMatchType.STARTS_WITH:
            return ResourceLink(
                website_name, template_url.format('_find/prefix/0')
            )
        else:
            return ResourceLink(
                website_name, template_url.format('_find/suffix/0')
            )

    def _create_sample_sentence_links(self) -> ResourceLinkSet:
        """Creates link set for Jpn->Eng sample sentence sites."""
        link_set = ResourceLinkSet('Jpn-Eng Sample Sentences', [])
        link_set.resource_links.append(self._create_tatoeba_query_link())
        link_set.resource_links.append(
            self._create_weblio_sentences_query_link()
        )

        return link_set

    def _create_weblio_sentences_query_link(self) -> ResourceLink:
        """Creates a link to query Weblio's Jpn->Eng sample sentence search.

        Weblio's sample sentence search doesn't support different query types,
        so match_type is not used.
        """
        return ResourceLink(
            'Weblio EJJE',
            'https://ejje.weblio.jp/sentence/content/"{}"'.format(self._query)
        )

    def _create_tatoeba_query_link(self) -> ResourceLink:
        """Creates a link to query the Tatoeba sample sentence project."""
        website_name = 'Tatoeba'
        template_url = (
            'https://tatoeba.org/eng/sentences/search?query={}'
            '&from=jpn&to=eng'
        )

        if self._match_type == QueryMatchType.EXACT_MATCH:
            return ResourceLink(
                website_name, template_url.format('%3D' + self._query)
            )
        elif self._match_type == QueryMatchType.STARTS_WITH:
            return ResourceLink(
                website_name, template_url.format(self._query + '*')
            )
        else:
            return ResourceLink(
                website_name, template_url.format('*' + self._query)
            )

    def _create_jpn_dict_links(self) -> List[ResourceLink]:
        """Creates link set for Japanese dictionary sites."""
        link_set = ResourceLinkSet('Jpn Dictionaries', [])
        link_set.resource_links.append(self._create_goo_query_link())
        link_set.resource_links.append(self._create_weblio_jpn_query_link())

        return link_set

    def _create_goo_query_link(self) -> ResourceLink:
        """Creates a link to query Goo."""
        website_name = 'Goo'
        template_url = 'https://dictionary.goo.ne.jp/srch/all/{}/{{}}/'.format(
            self._query
        )
        if self._match_type == QueryMatchType.STARTS_WITH:
            return ResourceLink(website_name, template_url.format('m0u'))
        elif self._match_type == QueryMatchType.EXACT_MATCH:
            return ResourceLink(website_name, template_url.format('m1u'))
        else:
            return ResourceLink(website_name, template_url.format('m2u'))

    def _create_weblio_jpn_query_link(self) -> ResourceLink:
        """Creates a link to query Weblio's JPN dictionary."""
        website_name = 'Weblio'
        template_url = 'https://www.weblio.jp/content{{}}/{}'.format(
            self._query
        )

        if self._match_type == QueryMatchType.EXACT_MATCH:
            return ResourceLink(website_name, template_url.format(''))
        elif self._match_type == QueryMatchType.STARTS_WITH:
            return ResourceLink(
                website_name, template_url.format('_find/prefix/0')
            )
        else:
            return ResourceLink(
                website_name, template_url.format('_find/suffix/0')
            )


class QueryArticleResultSet(object):
    """The set of article results of a query of the Myaku db."""

    def __init__(self, query: str, match_type: JpnArticleQueryType) -> None:
        """Queries the Myaku db to get the article result set for query."""
        if query:
            with MyakuCrawlDb(DbAccessMode.READ) as db:
                self._result_articles = db.search_articles(
                    query, match_type, 0, 20
                )
        else:
            self._result_articles = []

        self.article_count = len(self._result_articles)
        self.instance_count = sum(
            len(a.found_positions) for a in self._result_articles
        )

        self.ranked_article_results = [
            QueryArticleResult(a) for a in self._result_articles
        ]


class QueryArticleResult(object):
    """A single article result of a query of the Myaku db."""

    def __init__(self, search_result: JpnArticleSearchResult) -> None:
        """Populates article result data using given search result."""
        self.article = search_result.article
        self.matched_base_forms = search_result.matched_base_forms
        self.quality_score = search_result.quality_score
        self.instance_count = len(search_result.found_positions)
        self.publication_date_str = humanize_date(
            search_result.article.publication_datetime
        )
        self.last_updated_date_str = humanize_date(
            search_result.article.last_updated_datetime
        )
        self.display_last_updated_date = (
            self._should_display_last_updated_datetime(search_result.article)
        )
        self.tags = self._get_tags(search_result.article)

        matching_sentences = self._get_result_matching_sentences(
            search_result, _MAX_ARTICLE_INSTANCE_SAMPLES
        )
        self.main_matching_sentence = matching_sentences[0]
        self.more_matching_sentences = matching_sentences[
            1:_MAX_ARTICLE_INSTANCE_SAMPLES
        ]

    def _should_display_last_updated_datetime(
        self, article: JpnArticle
    ) -> bool:
        """Determines if last updated datetime should be displayed for article.

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

    def _humanize_index_position(self, index: int, article: JpnArticle) -> str:
        """Gets a human-readable string of an index position in the article."""
        if index < len(article.title):
            return 'Article title'

        percent_pos = round((index / len(article.full_text)) * 100)
        return '{}% into article'.format(percent_pos)

    def _create_matching_sentence(
        self, article: JpnArticle, sentence_start_index: int,
        sentence_end_index: int, found_positions: LexicalItemTextPosition
    ) -> SearchResultMatchingSentence:
        """Creates a matching sentence object from article and sentence data.

        Args:
            article: Article containing the sentence
            sentence_text: Full text of the matching sentence.
            sentence_start_index: Starting index of the matching sentence in
                the article text.
            found_positions: Positions where the text matching the search was
                found in the article.

        Returns:
            A SearchResultMatchingSentence object created from the given data.
        """
        matching_sentence = SearchResultMatchingSentence(
            sentence_start_index - sentence_end_index + 1,
            self._humanize_index_position(sentence_start_index, article),
            len(found_positions),
            []
        )

        last_end_index = sentence_start_index - 1
        for pos in found_positions:
            if last_end_index != pos.index - 1:
                segment_text = article.full_text[last_end_index + 1:pos.index]
                matching_sentence.segments.append(
                    SearchResultMatchingSentenceSegment(False, segment_text)
                )
                last_end_index += len(segment_text)
            match_text = article.full_text[pos.slice()]
            matching_sentence.segments.append(
                SearchResultMatchingSentenceSegment(True, match_text)
            )
            last_end_index += pos.len

        end_text = article.full_text[
            last_end_index + 1: sentence_end_index + 1
        ]
        if len(end_text) > 0:
            matching_sentence.segments.append(
                SearchResultMatchingSentenceSegment(False, end_text)
            )

        matching_sentence.trim_whitespace()
        return matching_sentence

    def _get_result_matching_sentences(
        self, result: JpnArticleSearchResult, max_count: int
    ) -> List[SearchResultMatchingSentence]:
        """Gets a list of the matching sentences for the search result.

        Args:
            search_result: The search result to get the matching sentences for.
            max_count: Maximum number of matching sentences to return.

        Returns:
            A ranked list by sentence length of the matching sentences of the
            article for the search result.
        """
        sentence_groups = result.article.group_text_positions_by_sentence(
            result.found_positions
        )

        # Sort by sentence length (end_index - start_index + 1)
        sorted_groups = sorted(
            sentence_groups, key=lambda t: t[1] - t[0] + 1, reverse=True
        )

        matching_sentences = []
        for sentence_group in sorted_groups[:max_count]:
            matching_sentences.append(self._create_matching_sentence(
                result.article, *sentence_group
            ))

        return matching_sentences

    def _get_tags(self, article: JpnArticle) -> List[str]:
        """Gets the tags applicable for the article."""
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


def index(request: HttpRequest) -> HttpResponse:
    """Search page handler."""
    if len(request.GET.get('q', '')) == 0:
        return render(request, 'search/start.html', {})

    query = request.GET['q']
    match_type = JpnArticleQueryType.EXACT
    query_result_set = QueryArticleResultSet(query, match_type)
    resource_links = QueryResourceLinks(query)

    return render(
        request, 'search/results.html',
        {
            'query': query,
            'query_result_set': query_result_set,
            'resource_links': resource_links,
        }
    )
