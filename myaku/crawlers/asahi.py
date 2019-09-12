"""Crawler for the Asahi Shinbun website."""

import logging
import re
from datetime import date
from typing import List, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

from myaku import utils
from myaku.crawlers.base import Crawl, CrawlerABC, CrawlGenerator
from myaku.datatypes import JpnArticle
from myaku.utils import html

_log = logging.getLogger(__name__)


@utils.add_method_debug_logging
class AsahiCrawler(CrawlerABC):
    """Crawler for articles from the Asahi Shinbun website."""

    SOURCE_NAME = 'Asahi Shinbun'
    __SOURCE_BASE_URL = 'https://www.asahi.com'

    _NEWS_MOST_RECENT_URL = __SOURCE_BASE_URL + '/news/'
    _COLUMN_MOST_RECENT_URL = __SOURCE_BASE_URL + '/rensai/featurelist.html'
    _EDITORIAL_ARCHIVE_URL = __SOURCE_BASE_URL + '/news/editorial.html'

    _DAILY_NEWS_URL_TEMPLATE = __SOURCE_BASE_URL + '/news/daily/%m%d.html'

    _EDITORIAL_ARCHIVE_MONTH_TAB_IDS = [
        'CurrentMonth',
        'LastMonth',
        'TwoMonthsAgo',
        'ThreeMonthsAgo'
    ]

    _ARTICLE_LIST_CLASS = 'List'
    _ARTICLE_LI_ID_REGEX = re.compile('^g_')
    _ARTICLE_LI_VIDEO_CLASS = 'Movie'

    _PAYWALL_LIST_CLASS_REGEX = re.compile('^Key(Gold|Silver)$')
    _PAYWALL_TITLE_CLASS_REGEX = re.compile('^TagMember(Gold|Silver)$')

    _ARTICLE_DATETIME_FORMAT = '%Y-%m-%dT%H:%M'

    _ARTICLE_TITLE_DIV_CLASS = 'ArticleTitle'
    _ARTICLE_TAG_LIST_CLASS = 'Tag'
    _ARTICLE_BODY_TEXT_DIV_CLASS = 'ArticleText'
    _ARTICLE_BODY_TEXT_TAGS = ['p', 'h2']

    @property
    def _SOURCE_BASE_URL(self) -> str:
        """Return the base url for accessing the source."""
        return self.__SOURCE_BASE_URL

    @utils.skip_method_debug_logging
    def _parse_most_recent_article_list_li(
        self, li_tag: Tag, check_ids: bool
    ) -> Optional[JpnArticle]:
        """Parse the article metadata from a li tag from a most recent list.

        Does not parse the article metadata from the li if the article is
        marked as being behind a paywall.

        Args:
            li_tag: li tag from a summary page article list.
            check_ids: If True, will check the id attr of each li to make sure
                it matches the pattern used for article li ids.

        Returns:
            If the article metadata could be parsed from the li, returns an
            article object with source_url, source_name, and has_video set.
            If the article metadata could not be parsed due to being a paywall
            article or the li not being for an article, returns None instead.
        """
        li_id = li_tag.get('id', '')
        if check_ids and not re.match(self._ARTICLE_LI_ID_REGEX, li_id):
            _log.debug(
                'Skipped article li because it has non-article id "%s": "%s"',
                li_tag.get('id'), li_tag
            )
            return None

        paywall_span = li_tag.find(class_=self._PAYWALL_LIST_CLASS_REGEX)
        if paywall_span is not None:
            _log.debug(
                'Skipped article li because it is a paywall article: "%s"',
                li_tag
            )
            return None

        return JpnArticle(
            source_url=utils.strip_url_query_and_frag(
                html.parse_link_descendant(li_tag)
            ),
            source_name=self.SOURCE_NAME,
            has_video=html.descendant_with_class_exists(
                li_tag, self._ARTICLE_LI_VIDEO_CLASS
            )
        )

    def _crawl_most_recent_page(
        self, url: str, uses_li_ids: bool
    ) -> CrawlGenerator:
        """Crawl all not yet crawled articles from a most recent page.

        Args:
            url: Url for a summary page.
            uses_li_ids: Should be given as True if the li tags in the article
                list for the summary page have their id attr set to the article
                id pattern.

        Returns:
            A generator that will yield the data for a not previously crawled
            article from the most recent page each call.
        """
        soup = self._get_url_html_soup(url)
        article_ul = html.select_descendants_by_class(
            soup, self._ARTICLE_LIST_CLASS, 'ul'
        )[0]

        article_metas = []
        article_li_tags = html.select_descendants_by_tag(article_ul, 'li')
        for li_tag in article_li_tags:
            article_meta = self._parse_most_recent_article_list_li(
                li_tag, uses_li_ids
            )
            if article_meta is None:
                continue

            _log.debug(
                'Parsed article link "%s" with has_video=%s',
                article_meta.source_url, article_meta.has_video
            )
            article_metas.append(article_meta)

        yield from self._crawl_uncrawled_articles(article_metas)

    @utils.skip_method_debug_logging
    def _parse_editorial_list_dd(
        self, dd_tag: Tag,
    ) -> Optional[JpnArticle]:
        """Parse the article metadata from a dd tag from an editorial list.

        Does not parse the article metadata from the dd tag if the article is
        marked as being behind a paywall.

        Args:
            dd_tag: dd tag from the editorial summary page article list.

        Returns:
            If the article metadata could be parsed from the li, returns an
            article object with source_url, source_name, and has_video set.
            If the article metadata could not be parsed due to being a paywall
            article, returns None instead.
        """
        paywall_span = dd_tag.find(class_=self._PAYWALL_LIST_CLASS_REGEX)
        if paywall_span is not None:
            _log.debug(
                'Skipped editorial dd because it is a paywall article: "%s"',
                dd_tag
            )
            return None

        return JpnArticle(
            source_url=utils.strip_url_query_and_frag(
                html.parse_link_descendant(dd_tag)
            ),
            source_name=self.SOURCE_NAME,
            has_video=False
        )

    def _parse_editorial_archive_tab(
        self, page_soup: BeautifulSoup, tab_id: str
    ) -> List[JpnArticle]:
        """Parse the article metas from a tab of the editorial archive page.

        Args:
            page_soup: BeautifulSoup of the editorial summary page.
            tab_id: The id of the tab whose editorial article list to parse.

        Returns:
            Article objects with the metadata parsed from the editorial article
            list for the specified tab.
        """
        month_tab_div = html.select_descendant_by_id(page_soup, tab_id)

        # Sometimes a monthly tab is present with no articles listed under it.
        # In this case, there will be no li tags in the month tab div.
        if month_tab_div.find('li') is None:
            return []

        tab_article_metas = []
        article_dd_tags = html.select_descendants_by_tag(month_tab_div, 'dd')
        for dd_tag in article_dd_tags:
            article_meta = self._parse_editorial_list_dd(dd_tag)
            if article_meta is None:
                continue

            _log.debug(
                'Parsed editorial article link "%s"', article_meta.source_url
            )
            tab_article_metas.append(article_meta)

        return tab_article_metas

    def crawl_editorial_archive(self) -> CrawlGenerator:
        """Crawl not yet crawled articles from the editorial archive page.

        Returns:
            A generator that will yield the data for a not previously crawled
            article from the editorial archive page each call.
        """
        soup = self._get_url_html_soup(self._EDITORIAL_ARCHIVE_URL)

        article_metas = []
        for tab_id in self._EDITORIAL_ARCHIVE_MONTH_TAB_IDS:
            tab_article_metas = self._parse_editorial_archive_tab(soup, tab_id)
            article_metas.extend(tab_article_metas)

        yield from self._crawl_uncrawled_articles(article_metas)

    def crawl_column_most_recent(self) -> CrawlGenerator:
        """Crawl not yet crawled articles from the column most recent page.

        Returns:
            A generator that will yield the data for a not previously crawled
            article from the column most recent page each call.
        """
        yield from self._crawl_most_recent_page(
            self._COLUMN_MOST_RECENT_URL, False
        )

    def crawl_news_daily(self, news_date: date) -> CrawlGenerator:
        """Crawl not yet crawled articles from a daily news page.

        Args:
            date: Date of the daily news page to crawl. Only considers the
                month and day values. Ignores the year.

        Returns:
            A generator that will yield the data for a not previously crawled
            article from the daily news page each call.
        """
        yield from self._crawl_most_recent_page(
            news_date.strftime(self._DAILY_NEWS_URL_TEMPLATE), True
        )

    def crawl_news_most_recent(self) -> CrawlGenerator:
        """Crawl not yet crawled articles from the news most recent page.

        Returns:
            A generator that will yield the data for a not previously crawled
            article from the news most recent page each call.
        """
        yield from self._crawl_most_recent_page(
            self._NEWS_MOST_RECENT_URL, True
        )

    def get_crawls_for_most_recent(self) -> List[Crawl]:
        """Get a list of Crawls for the most recent Asahi articles."""
        crawls = []
        news_most_recent_crawl = Crawl(
            self.SOURCE_NAME, 'News most recent', self.crawl_news_most_recent()
        )
        crawls.append(news_most_recent_crawl)

        column_most_recent_crawl = Crawl(
            self.SOURCE_NAME, 'Column most recent',
            self.crawl_column_most_recent()
        )
        crawls.append(column_most_recent_crawl)

        editorial_archive_crawl = Crawl(
            self.SOURCE_NAME, 'Editorial archive',
            self.crawl_editorial_archive()
        )
        crawls.append(editorial_archive_crawl)

        return crawls

    def _is_paywall_article_page(self, page_soup: BeautifulSoup) -> bool:
        """Return True if the given page is a paywall article page."""
        title_div = html.select_one_descendant_by_class(
            page_soup, self._ARTICLE_TITLE_DIV_CLASS, 'div'
        )
        paywall_tag = title_div.find(class_=self._PAYWALL_TITLE_CLASS_REGEX)

        if paywall_tag is not None:
            _log.debug(
                'Found paywall tag "%s" in: "%s"', paywall_tag, title_div
            )
            return True
        return False

    def _parse_article_title_div(
        self, page_soup: BeautifulSoup, article: JpnArticle
    ) -> None:
        """Parse the title and datetime for the article from its title div.

        Args:
            page_soup: BeautifulSoup of an article page.
            article: Article object to store the title and datetime parsed from
                the article page in.
        """
        title_div = html.select_one_descendant_by_class(
            page_soup, self._ARTICLE_TITLE_DIV_CLASS, 'div'
        )
        article.title = html.parse_text_from_descendant_by_tag(title_div, 'h1')
        article.title = article.title.strip()

        article.publication_datetime = html.parse_time_descendant(
            title_div, self._ARTICLE_DATETIME_FORMAT, True
        )
        article.last_updated_datetime = article.publication_datetime

    def _parse_article_tags(
        self, page_soup: BeautifulSoup, article: JpnArticle
    ) -> None:
        """Parse the tags for the article from an article page.

        Args:
            page_soup: BeautifulSoup of an article page.
            article: Article object to store the tag data parsed from the
                article page in.
        """
        if page_soup.find('ul', class_=self._ARTICLE_TAG_LIST_CLASS) is None:
            return

        tags_ul = html.select_one_descendant_by_class(
            page_soup, self._ARTICLE_TAG_LIST_CLASS, 'ul'
        )
        tags_li_tags = html.select_descendants_by_tag(tags_ul, 'li')

        article.tags = []
        for tags_li_tag in tags_li_tags:
            article.tags.append(html.parse_valid_child_text(tags_li_tag))

    def _parse_article_body_text(
        self, page_soup: BeautifulSoup, article: JpnArticle
    ) -> None:
        """Parse the body text for the article from an article page.

        Assumes the title attr is already set on the given article object.

        Args:
            page_soup: BeautifulSoup of an article page.
            article: Article object to store the body text data parsed from the
                article page in.
        """
        body_text_div = html.select_one_descendant_by_class(
            page_soup, self._ARTICLE_BODY_TEXT_DIV_CLASS, 'div'
        )

        body_text_strs = [article.title]
        for body_text_tag in body_text_div.children:
            if body_text_tag.name not in self._ARTICLE_BODY_TEXT_TAGS:
                if body_text_tag.name is not None:
                    _log.debug(
                        'Skipping body text "%s" tag: "%s"',
                        body_text_tag.name, body_text_tag
                    )
                continue

            tag_text = html.parse_valid_child_text(body_text_tag, False)
            if tag_text:
                body_text_strs.append(tag_text)

        article.full_text = '\n\n'.join(body_text_strs)
        article.alnum_count = utils.get_alnum_count(article.full_text)

    def crawl_article(
        self, article_url: str, article_meta: JpnArticle
    ) -> Optional[JpnArticle]:
        """Crawl an Asahi article page.

        If the page is partially behind a paywall, will not parse the page and
        returns None.

        Args:
            article_url: Url to an Asahi article page..
            article_meta: Metadata for the article from outside of the article
                page.

        Returns:
            If the page was not partially behind a paywall, returns the given
            article object with the parsed data from the article added to it.
            If the page was partially behind a paywall, returns None instead.

        Raises:
            HTTPError: An error occurred making a GET request to url.
            HtmlParsingError: An error occurred while parsing the article.
        """
        page_soup = self._get_url_html_soup(article_url, raise_on_404=False)

        if page_soup is None or self._is_paywall_article_page(page_soup):
            return None

        article = article_meta
        self._parse_article_title_div(page_soup, article)
        self._parse_article_tags(page_soup, article)
        self._parse_article_body_text(page_soup, article)
        return article
