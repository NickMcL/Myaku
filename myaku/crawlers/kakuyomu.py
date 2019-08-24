"""Crawler for the Kakuyomu website."""

import enum
import logging
import posixpath
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup
from bs4.element import Tag

import myaku.utils as utils
import myaku.utils.html as html
from myaku.crawlers.abc import Crawl, CrawlerABC, CrawlGenerator
from myaku.datatypes import JpnArticle, JpnArticleBlog, JpnArticleMetadata
from myaku.errors import HtmlParsingError

_log = logging.getLogger(__name__)


@enum.unique
class KakuyomuGenre(enum.Enum):
    """The genre categories used by Kakuyomu.

    Kakuyomu has several more genres available than those in this enum, but
    this enum only covers the categories crawled by the KakuyomuCrawler.

    Attributes:
        NONFICTION: Non-fiction articles about any topic.
        CRITICISM: Articles related to criticism of written works.
    """
    NONFICTION = 1
    CRITICISM = 2


@enum.unique
class KakuyomuSortOrder(enum.Enum):
    """The series sort orders available on Kakuyomu.

    Attributes:
        POPULAR: Sorts from most popular series to least popular.
        PUBLISHED_AT: Sorts from most recently started series to oldest started
            series.
        LAST_EPISODE_PUBLISHED_AT: Sorts from most recently updated series to
            least recently updated series.
    """
    POPULAR = 1
    PUBLISHED_AT = 2
    LAST_EPISODE_PUBLISHED_AT = 3


@utils.add_method_debug_logging
class KakuyomuCrawler(CrawlerABC):
    """Crawls articles from the Kakuyomu website.

    Only crawls for articles in the non-fiction and essay sections of Kakuyomu.
    """

    SOURCE_NAME = 'Kakuyomu'
    __SOURCE_BASE_URL = 'https://kakuyomu.jp'

    _SEARCH_PAGE_URL_TEMPLATE = (
        __SOURCE_BASE_URL +
        '/search?genre_name={genre}&order={sort_order}&page={page_num}'
    )

    _EPISODE_SIDEBAR_URL_SUFFIX = 'episode_sidebar'
    _EPISODE_SIDEBAR_LOAD_WAIT_TIME = 2  # In seconds

    _TIME_TAG_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
    _SEARCH_RESULT_DATETIME_FORMAT = '%Y年%m月%d日 %H:%M 更新'

    _EMPTY_SEARCH_RESULTS_CLASS = 'widget-emptyMessage'
    _SEARCH_RESULT_TILE_CLASS = 'widget-work'
    _SEARCH_RESULT_TITLE_CLASS = 'widget-workCard-titleLabel'
    _SEARCH_RESULT_AUTHOR_CLASS = 'widget-workCard-authorLabel'
    _SEARCH_RESULT_LAST_UPDATED_CLASS = 'widget-workCard-dateUpdated'

    _SERIES_TITLE_TAG_ID = 'workTitle'
    _SERIES_AUTHOR_TAG_ID = 'workAuthor-activityName'

    _SERIES_RATING_TAG_ID = 'workPoints'
    _SERIES_RATING_COUNT_CLASS = 'js-review-count-element'

    _SERIES_GENRE_TAG_ID = 'workGenre'
    _SERIES_TAG_DIV_ID = 'workMeta-attentionsAndTags'

    _CATCHPHRASE_TAG_ID = 'catchphrase-body'
    _INTRO_TAG_ID = 'introduction'
    _INTRO_EXPAND_BUTTON_CLASS = 'ui-truncateTextButton-expandButton'

    _SERIES_INFO_LIST_CLASS = 'widget-credit'
    _INFO_LIST_HIDDEN_DATA_STRING = '作者の設定により非表示'

    _START_DATETIME_TERM = '公開日'
    _LAST_UPDATED_DATETIME_TERM = '最終更新日'
    _ARTICLE_COUNT_TERM = 'エピソード'
    _ARTICLE_COUNT_REGEX = re.compile(r'^([0-9,]+)話$')
    _TOTAL_CHAR_COUNT_TERM = '総文字数'
    _TOTAL_CHAR_COUNT_REGEX = re.compile(r'^([0-9,]+)文字$')
    _SERIALIZATION_STATUS_TERM = '執筆状況'
    _IN_SERIALIZATION_STATUS = '連載中'

    _COMMENT_COUNT_TERM = '応援コメント'
    _COMMENT_COUNT_REGEX = re.compile(r'^([0-9,]+)件$')
    _FOLLOWER_COUNT_TERM = '小説フォロー数'
    _FOLLOWER_COUNT_REGEX = re.compile(r'^([0-9,]+)人$')

    _SERIES_EPISODE_TOC_LIST_CLASS = 'widget-toc-items'
    _EPISODE_TOC_TITLE_CLASS = 'widget-toc-episode-titleLabel'
    _SECTION_LI_CLASS = 'widget-toc-chapter'
    _EPISODE_LI_CLASS = 'widget-toc-episode'

    _EPISODE_TITLE_CLASS = 'widget-episodeTitle'
    _EPISODE_TEXT_DIV_CLASS = 'widget-episodeBody'
    _EPISODE_INFO_LIST_ID = 'episodeInfo'

    @property
    def _SOURCE_BASE_URL(self) -> str:
        """The base url for accessing the source."""
        return self.__SOURCE_BASE_URL

    def _create_search_url(
        self, genre: KakuyomuGenre, sort_order: KakuyomuSortOrder,
        page_num: int = 1
    ) -> str:
        """Creates a URL for making a search on the search page.

        Args:
            genre: Series genre to search for.
            sort_order: Sort order to use for the search results.
            page_num: Page of the search results.
        """
        return self._SEARCH_PAGE_URL_TEMPLATE.format(
            genre=genre.name.lower(),
            sort_order=sort_order.name.lower(),
            page_num=page_num
        )

    def _is_empty_search_results_page(self, page_soup: BeautifulSoup) -> bool:
        """Returns True if the page is the empty search results page."""
        return html.descendant_with_class_exists(
            page_soup, self._EMPTY_SEARCH_RESULTS_CLASS
        )

    def _parse_search_result_datetime(self, datetime_str: str) -> datetime:
        """Parses a datetime string from the search results page.

        Raises:
            HtmlParsingError: The datetime string could not be parsed.
        """
        try:
            dt = datetime.strptime(
                datetime_str, self._SEARCH_RESULT_DATETIME_FORMAT
            )
        except ValueError:
            utils.log_and_raise(
                _log, HtmlParsingError,
                'Failed to parse search result datetime string "{}" using '
                'format "{}"'.format(
                    datetime_str, self._SEARCH_RESULT_DATETIME_FORMAT
                )
            )

        # Search result datetime strings do not include seconds, so explicitly
        # set seconds to 0.
        return utils.convert_jst_to_utc(dt.replace(second=0))

    def _parse_search_results_page(
        self, page_soup: BeautifulSoup
    ) -> List[JpnArticleBlog]:
        """Parses the series blog info from a search results page.

        Args:
            page_soup: A BeautifulSoup initialized with the content from a
                search page.

        Returns:
            A list of the series blog info for all of the series listed in the
            search results page.
        """
        series_blogs = []
        series_tiles = html.select_descendants_by_class(
            page_soup, self._SEARCH_RESULT_TILE_CLASS, 'div'
        )
        _log.debug('Found %s series on search results page', len(series_tiles))

        for series_tile in series_tiles:
            series_blog = JpnArticleBlog(source_name=self.SOURCE_NAME)

            title_link_tag = html.select_descendants_by_class(
                series_tile, self._SEARCH_RESULT_TITLE_CLASS, 'a', 1
            )[0]
            series_blog.title = html.parse_valid_child_text(
                title_link_tag
            ).strip()
            series_blog.source_url = title_link_tag['href']

            series_blog.author = html.parse_text_from_descendant_by_class(
                series_tile, self._SEARCH_RESULT_AUTHOR_CLASS, 'a'
            ).strip()

            last_updated_str = html.parse_text_from_descendant_by_class(
                series_tile, self._SEARCH_RESULT_LAST_UPDATED_CLASS, 'span'
            )
            series_blog.last_updated_datetime = (
                self._parse_search_result_datetime(last_updated_str)
            )

            series_blogs.append(series_blog)

        return series_blogs

    @utils.skip_method_debug_logging
    def _parse_count_string(
        self, count_str: str, count_regex: re.Pattern
    ) -> Optional[int]:
        """Parses a data count string for a series into an int.

        Also checks if the count string indicates that the count is hidden by
        preference of the author of the series.

        Args:
            count_str: String containing a count of some data from a Kakuyomu
                series page.
            count_regex: Pattern that the count string should match to be
                valid. The pattern must contain one group that captures the
                count number portion of the count string.

        Returns:
            The parsed count value as an int. If the count string indicates
            that the count is hidden by author preference, returns None
            instead.

        Raises:
            HtmlParsingError: The count string did not match the given pattern
                and was not the string indicating the count is hidden by author
                preference.
        """
        if count_str == self._INFO_LIST_HIDDEN_DATA_STRING:
            return None

        match = re.match(count_regex, count_str)
        if match is None:
            utils.log_and_raise(
                _log, HtmlParsingError,
                'Count string "{}" does not match pattern {}'.format(
                    count_str, count_regex
                )
            )

        return int(match.group(1).replace(',', ''))

    def _parse_series_rating_info(
        self, series_page_soup: BeautifulSoup, series_blog: JpnArticleBlog
    ) -> None:
        """Parses the rating info for a series.

        Args:
            series_page_soup: A BeautifulSoup initialized with the content from
                a series homepage.
            series_blog: The blog object to store the parsed data in.
        """
        rating_str = html.parse_text_from_descendant_by_id(
            series_page_soup, self._SERIES_RATING_TAG_ID
        )
        series_blog.rating = float(re.sub('[^0-9]', '', rating_str))

        rating_count_str = html.parse_text_from_descendant_by_class(
            series_page_soup, self._SERIES_RATING_COUNT_CLASS, 'span'
        )
        series_blog.rating_count = int(re.sub('[^0-9]', '', rating_count_str))

    def _parse_series_tags(
        self, series_page_soup: BeautifulSoup, series_blog: JpnArticleBlog
    ) -> None:
        """Parses the tags for a series.

        Args:
            series_page_soup: A BeautifulSoup initialized with the content from
                a series homepage.
            series_blog: The blog object to store the parsed data in.
        """
        series_blog.tags = []
        genre = html.parse_text_from_descendant_by_id(
            series_page_soup, self._SERIES_GENRE_TAG_ID
        )
        series_blog.tags.append(genre.strip())

        # If a series has no tags set for it, the tag div won't exist on the
        # series page.
        tag_div = series_page_soup.find(id=self._SERIES_TAG_DIV_ID)
        if tag_div is None:
            return

        tag_lists = tag_div.find_all('ul')
        for tag_list in tag_lists:
            for tag_element in tag_list.find_all('li'):
                series_blog.tags.append(
                    html.parse_valid_child_text(tag_element).strip()
                )

        return series_blog.tags

    def _parse_series_intro(
        self, series_page_soup: BeautifulSoup, series_blog: JpnArticleBlog
    ) -> None:
        """Parses the intro and catchphrase for a series.

        Both the intro and catchphrase are optional, so a series might not have
        them set.

        Args:
            series_page_soup: A BeautifulSoup initialized with the content from
                a series homepage.
            series_blog: The blog object to store the parsed data in.
        """
        catchphrase_tag = series_page_soup.find(id=self._CATCHPHRASE_TAG_ID)
        if catchphrase_tag is not None:
            series_blog.catchphrase = html.parse_valid_child_text(
                catchphrase_tag
            )

        intro_tag = series_page_soup.find(id=self._INTRO_TAG_ID)
        if intro_tag is not None:
            # Remove the expand button text from the end of the intro
            expand_button_span = intro_tag.find(
                'span', class_=self._INTRO_EXPAND_BUTTON_CLASS
            )
            if expand_button_span is not None:
                expand_button_span.decompose()

            series_blog.introduction = html.parse_valid_child_text(
                intro_tag
            )

    def _parse_series_meta_info_list(
        self, series_page_soup: BeautifulSoup, series_blog: JpnArticleBlog
    ) -> None:
        """Parses the data in the meta info list for a series.

        Args:
            series_page_soup: A BeautifulSoup initialized with the content from
                a series homepage.
            series_blog: The blog object to store the parsed data in.
        """
        info_lists = html.select_descendants_by_class(
            series_page_soup, self._SERIES_INFO_LIST_CLASS, 'dl', 2
        )
        meta_info_list = info_lists[0]

        start_datetime_dd = html.select_desc_list_data(
            meta_info_list, self._START_DATETIME_TERM
        )
        series_blog.start_datetime = html.parse_time_descendant(
            start_datetime_dd, self._TIME_TAG_DATETIME_FORMAT
        )

        last_updated_datetime_dd = html.select_desc_list_data(
            meta_info_list, self._LAST_UPDATED_DATETIME_TERM
        )
        series_blog.last_updated_datetime = html.parse_time_descendant(
            last_updated_datetime_dd, self._TIME_TAG_DATETIME_FORMAT
        )

        article_count_str = html.parse_desc_list_data_text(
            meta_info_list, self._ARTICLE_COUNT_TERM
        )
        series_blog.article_count = self._parse_count_string(
            article_count_str, self._ARTICLE_COUNT_REGEX
        )

        total_char_count_str = html.parse_desc_list_data_text(
            meta_info_list, self._TOTAL_CHAR_COUNT_TERM
        )
        series_blog.total_char_count = self._parse_count_string(
            total_char_count_str, self._TOTAL_CHAR_COUNT_REGEX
        )

        serialization_status_str = html.parse_desc_list_data_text(
            meta_info_list, self._SERIALIZATION_STATUS_TERM
        )
        series_blog.in_serialization = (
            serialization_status_str == self._IN_SERIALIZATION_STATUS
        )

    def _parse_series_review_info_list(
        self, series_page_soup: BeautifulSoup, series_blog: JpnArticleBlog
    ) -> None:
        """Parses the data in the review info list for a series.

        Args:
            series_page_soup: A BeautifulSoup initialized with the content from
                a series homepage.
            series_blog: The blog object to store the parsed data in.
        """
        info_lists = html.select_descendants_by_class(
            series_page_soup, self._SERIES_INFO_LIST_CLASS, 'dl', 2
        )
        review_info_list = info_lists[1]

        comment_count_str = html.parse_desc_list_data_text(
            review_info_list, self._COMMENT_COUNT_TERM
        )
        series_blog.comment_count = self._parse_count_string(
            comment_count_str, self._COMMENT_COUNT_REGEX
        )

        follower_count_str = html.parse_desc_list_data_text(
            review_info_list, self._FOLLOWER_COUNT_TERM
        )
        series_blog.follower_count = self._parse_count_string(
            follower_count_str, self._FOLLOWER_COUNT_REGEX
        )

    def _parse_series_blog_info(
        self, series_page_soup: BeautifulSoup, series_page_url: str
    ) -> JpnArticleBlog:
        """Parse the blog info for a series from its homepage.

        Args:
            series_page_soup: A BeautifulSoup initialized with the content from
                a series homepage.
            series_page_url: Url for the series page to parse.

        Returns:
            A JpnArticleBlog with the info from the given series homepage.
        """
        series_blog = JpnArticleBlog(
            title=html.parse_text_from_descendant_by_id(
                series_page_soup, self._SERIES_TITLE_TAG_ID
            ).strip(),
            author=html.parse_text_from_descendant_by_id(
                series_page_soup, self._SERIES_AUTHOR_TAG_ID
            ).strip(),
            source_name=self.SOURCE_NAME,
            source_url=series_page_url,
        )

        self._parse_series_rating_info(series_page_soup, series_blog)
        self._parse_series_tags(series_page_soup, series_blog)
        self._parse_series_intro(series_page_soup, series_blog)
        self._parse_series_meta_info_list(series_page_soup, series_blog)
        self._parse_series_review_info_list(series_page_soup, series_blog)

        return series_blog

    def _select_table_of_contents_items(
        self, series_page_soup: BeautifulSoup
    ) -> List[Tag]:
        """Selects the table of contents list items from a series homepage.

        Args:
            series_page_soup: A BeautifulSoup initialized with the content from
                a series homepage.

        Returns:
            The <li> tags from the table of contents list on the series
            homepage.
        """
        table_of_contents_tag = html.select_descendants_by_class(
            series_page_soup, self._SERIES_EPISODE_TOC_LIST_CLASS, 'ol', 1
        )[0]
        table_of_contents_items = html.select_descendants_by_tag(
            table_of_contents_tag, 'li'
        )

        return table_of_contents_items

    @utils.skip_method_debug_logging
    def _is_section_li(self, li_tag: Tag) -> bool:
        """Returns True if the tag is a table of contents section name."""
        if 'class' not in li_tag.attrs or not li_tag.attrs['class']:
            return False
        return self._SECTION_LI_CLASS in li_tag.attrs['class']

    @utils.skip_method_debug_logging
    def _is_episode_li(self, li_tag: Tag) -> bool:
        """Returns True if the tag is a table of contents episode name."""
        if 'class' not in li_tag.attrs or not li_tag.attrs['class']:
            return False
        return self._EPISODE_LI_CLASS in li_tag.attrs['class']

    def _parse_table_of_contents_episode(
        self, episode_li_tag: Tag, series_blog: JpnArticleBlog,
        ep_order_num: int, section_name: str, section_order_num: int,
        section_ep_order_num: int
    ) -> JpnArticleMetadata:
        """Parses the metadata for an episode from a series table of contents.

        Args:
            episode_li_tag: The episode li tag from a series table of contents
                that will be parsed.

        Returns:
            The metadata contained within the episode li tag.
        """
        return JpnArticleMetadata(
            title=html.parse_text_from_descendant_by_class(
                episode_li_tag, self._EPISODE_TOC_TITLE_CLASS, 'span'
            ).strip(),
            author=series_blog.author,
            source_url=html.parse_link_descendant(episode_li_tag),
            source_name=self.SOURCE_NAME,
            blog=series_blog,
            blog_id=series_blog.get_id(),
            blog_article_order_num=ep_order_num,
            blog_section_name=section_name,
            blog_section_order_num=section_order_num,
            blog_section_article_order_num=section_ep_order_num,
            publication_datetime=html.parse_time_descendant(
                episode_li_tag, self._TIME_TAG_DATETIME_FORMAT
            ),
            last_crawled_datetime=datetime.utcnow(),
        )

    def _parse_series_episode_metadatas(
        self, series_page_soup: BeautifulSoup, series_blog: JpnArticleBlog
    ) -> List[JpnArticleMetadata]:
        """Parse the episode metadatas for a series from its homepage.

        Args:
            series_page_soup: A BeautifulSoup initialized with the content from
                a series homepage.
            series_blog: Blog info for this series.

        Returns:
            A list of the metadatas for all episodes listed on the series
            homepage.
        """
        table_of_contents_items = self._select_table_of_contents_items(
            series_page_soup
        )

        metadatas = []
        ep_order_num = 1
        section_order_num = 0
        section_ep_order_num = 1
        section_name = None
        for item in table_of_contents_items:
            if self._is_section_li(item):
                section_order_num += 1
                section_ep_order_num = 1
                section_name = html.parse_valid_child_text(item).strip()
            elif self._is_episode_li(item):
                metadata = self._parse_table_of_contents_episode(
                    item, series_blog, ep_order_num, section_name,
                    section_order_num, section_ep_order_num
                )
                metadatas.append(metadata)
                ep_order_num += 1
                section_ep_order_num += 1
            else:
                utils.log_and_raise(
                    _log, HtmlParsingError,
                    'Unrecognized list item "{}" in table of contents: "{}"',
                    item, series_page_soup
                )

        return metadatas

    def crawl_blog(self, page_url: str) -> CrawlGenerator:
        """Crawls a series homepage.

        Args:
            page_url: Url of the series homepage.

        Returns:
            A generator that will yield a JpnArticle for an episode of the
            series each call.
        """
        page_soup = self._get_url_html_soup(page_url)
        series_blog = self._parse_series_blog_info(page_soup, page_url)
        metadatas = self._parse_series_episode_metadatas(
            page_soup, series_blog
        )

        yield from self._crawl_uncrawled_articles(metadatas)

    def _crawl_search_results_page(
        self, genre: KakuyomuGenre, sort_order: KakuyomuSortOrder,
        page_num: int = 1
    ) -> CrawlGenerator:
        """Crawls a single page of series search results.

        Args:
            genre: Series genre to search for.
            sort_order: Sort order to use for the search results.
            page_num: Page of the search results to crawl.

        Returns:
            A generator that will yield a JpnArticle for an episode of a series
            from the page of search results each call.
        """
        search_url = self._create_search_url(genre, sort_order, page_num)

        page_soup = self._get_url_html_soup(search_url)
        if self._is_empty_search_results_page(page_soup):
            _log.debug('No search results found for url "%s"', search_url)
            return

        series_blogs = self._parse_search_results_page(page_soup)
        yield from self._crawl_updated_blogs(series_blogs)

    def crawl_search_results(
        self, genre: KakuyomuGenre, sort_order: KakuyomuSortOrder,
        pages_to_crawl: int = 1, start_page: int = 1
    ) -> CrawlGenerator:
        """Makes a series search on Kakuyomu and then crawls the results.

        Args:
            genre: Series genre to search for.
            sort_order: Sort order to use for the search results.
            pages_to_crawl: How many pages of the search results to crawl. Each
                page has 20 results.

                Will automatically stop the crawl if a page with no search
                results is reached before crawling the specified number of
                pages.
            start_page: What page of the search results to start the crawl on.

        Returns:
            A generator that will yield a JpnArticle for an episode of a series
            from the search results each call.
        """
        for i in range(start_page, start_page + pages_to_crawl):
            _log.debug(
                'Crawling page %s of search results of genre %s with sort '
                'order %s', i, genre.name, sort_order.name
            )
            yield from self._crawl_search_results_page(genre, sort_order, i)

    def get_crawls_for_most_recent(self) -> List[Crawl]:
        """Gets a list of Crawls for the most recent Kakuyomu articles.

        Only crawls for articles in the non-fiction section of Kakuyomu.
        """
        nonfiction_crawl = Crawl(
            self.SOURCE_NAME, 'Nonfiction most recent',
            self.crawl_search_results(
                KakuyomuGenre.NONFICTION,
                KakuyomuSortOrder.LAST_EPISODE_PUBLISHED_AT, 1, 5
            )
        )
        return [nonfiction_crawl]

    def _parse_episode_text(self, episode_page_soup: BeautifulSoup) -> str:
        """Parses the full text for an episode.

        Args:
            episode_page_soup: A BeautifulSoup initialized with the content
                from an episode page.

        Returns:
            The full text for the episode.
        """
        body_text_list = []
        title = html.parse_text_from_descendant_by_class(
            episode_page_soup, self._EPISODE_TITLE_CLASS, 'p'
        )
        body_text_list.append(title.strip())
        body_text_list.append('')  # Add extra new line after title

        body_text_div = html.select_descendants_by_class(
            episode_page_soup, self._EPISODE_TEXT_DIV_CLASS, 'div', 1
        )[0]
        body_text_paras = html.select_descendants_by_tag(body_text_div, 'p')

        for body_text_para in body_text_paras:
            para_text = html.parse_valid_child_text(body_text_para, False)
            if para_text is None:
                body_text_list.append('')
            else:
                body_text_list.append(para_text)

        return '\n'.join(body_text_list)

    def _parse_episode_last_updated_datetime(
        self, episode_page_soup: BeautifulSoup
    ) -> datetime:
        """Parses the last update time for an episode.

        Args:
            episode_page_soup: A BeautifulSoup initialized with the content
                from an episode page.

        Returns:
            The last update UTC datetime for the episode.
        """
        episode_info_list = html.select_descendant_by_id(
            episode_page_soup, self._EPISODE_INFO_LIST_ID
        )

        last_updated_datetime_dd = html.select_desc_list_data(
            episode_info_list, self._LAST_UPDATED_DATETIME_TERM
        )
        return html.parse_time_descendant(
            last_updated_datetime_dd, self._TIME_TAG_DATETIME_FORMAT
        )

    def _create_episode_sidebar_url(self, episode_url: str) -> str:
        """Creates the url for the sidebar for the given episode."""
        url_split = urlsplit(episode_url)
        return urlunsplit(
            (
                url_split.scheme, url_split.netloc,
                posixpath.join(
                    url_split.path, self._EPISODE_SIDEBAR_URL_SUFFIX
                ),
                url_split.query, url_split.fragment
            )
        )

    def crawl_article(
        self, article_url: str, article_metadata: JpnArticleMetadata
    ) -> JpnArticle:
        """Crawls a Kakuyomu episode article.

        Args:
            article_url: Url to a page containing a Kakuyomu episode.
            article_metadata: Metadata for the article listed on its series
                homepage.

        Returns:
            Article object with the parsed data from the article + the given
            metadata.

        Raises:
            HTTPError: An error occurred making a GET request to url.
            HtmlParsingError: An error occurred while parsing the article.
        """
        episode_page_soup = self._get_url_html_soup(article_url)
        article = JpnArticle(metadata=article_metadata, has_video=False)

        article.full_text = self._parse_episode_text(episode_page_soup)
        article.alnum_count = utils.get_alnum_count(article.full_text)

        sidebar_url = self._create_episode_sidebar_url(article_url)
        episode_sidebar_soup = self._get_url_html_soup(sidebar_url)
        article.metadata.last_updated_datetime = (
            self._parse_episode_last_updated_datetime(episode_sidebar_soup)
        )

        return article
