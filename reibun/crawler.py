"""Crawler classes for scraping text articles for the web."""

import logging
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

import reibun.utils as utils
from reibun.datatypes import JpnArticle

_log = logging.getLogger(__name__)


class CannotParseArticleError(Exception):
    """Indicates crawler was unable to parse any article from a page."""
    pass


@utils.add_method_debug_logging
class NhkNewsWebCrawler(object):
    """Crawls and scrapes articles from the NHK News Web website."""
    _SOURCE_NAME = 'NHK News Web'
    _ARTICLE_DATETIME_FORMAT = '%Y-%m-%dT%H:%M'
    _ARTICLE_SECTION_CLASS = 'detail-no-js'
    _ARTICLE_TITLE_CLASS = 'contentTitle'

    _ARTICLE_BODY_IDS = [
        'news_textbody',
        'news_textmore',
    ]
    _ARTICLE_BODY_CLASSES = [
        'news_add',
    ]

    def __init__(self, timeout=10):
        """Initializes the crawler with a timeout for web requests."""
        self.session = None
        self.timeout = timeout

    def __enter__(self):
        """Initializes a requests Session to use for all web requests."""
        self.session = requests.Session()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Closes the requests Session."""
        if self.session:
            self.session.close()

    def _parse_title(self, article_section: Tag) -> Optional[str]:
        """Parses the title from NHK article HTML.

        Args:
            article_section: Tag containing NHK article HTML.

        Returns:
            The parsed title from article_section, or None if the title could
            not be parsed.
        """
        title_spans = article_section.find_all(
            'span', class_=self._ARTICLE_TITLE_CLASS
        )

        if len(title_spans) != 1:
            _log.error(
                f'Found {len(title_spans)} title spans in: '
                f'"{article_section}"'
            )
            return None

        title = utils.parse_valid_child_text(title_spans[0])
        if title is None:
            _log.error(
                f'Unable to determine title from span tag '
                f'"{title_spans[0]}" in: "{article_section}"'
            )
            return None

        return title

    def _parse_publication_datetime(
        self, article_section: Tag
    ) -> Optional[datetime]:
        """Parses the publication datetime from NHK article HTML.

        Args:
            article_section: Tag containing NHK article HTML.

        Returns:
            UTC datetime for the publication datetime parsed from
            article_section, or None if the publication datetime could not be
            parsed.
        """
        time_tags = article_section.find_all('time')

        if len(time_tags) != 1:
            _log.error(
                f'Found {len(time_tags)} time tags in: "{article_section}"'
            )
            return None

        if not time_tags[0].has_attr('datetime'):
            _log.error(
                f'Time tag "{time_tags[0]}" has no datetime attribute in: '
                f'"{article_section}"'
            )
            return None

        try:
            publication_datetime = datetime.strptime(
                time_tags[0]['datetime'], self._ARTICLE_DATETIME_FORMAT
            )
        except ValueError:
            _log.error(
                f'Failed to parse datetime "{time_tags[0]["datetime"]}" of '
                f'"{time_tags[0]}" in: "{article_section}"'
            )
            return None

        return utils.convert_jst_to_utc(publication_datetime)

    def _parse_body_div(self, tag: Tag) -> Optional[str]:
        """Parses the body text from a division of an NHK article.

        Args:
            tag: Tag containing a division of an NHK article.

        Returns:
            The parsed body text from tag, or None if the crawler was unable to
            parse body text from tag.
        """
        section_text = utils.parse_valid_child_text(tag)
        if section_text is not None:
            return section_text

        text_sections = []
        for child in tag.children:
            # Skip text around child tags such as '\n'
            if child.name is None:
                continue

            child_text = utils.parse_valid_child_text(child)
            if child_text is None:
                _log.debug(
                    f'Unable to determine body text from tag: "{child}"'
                )
                continue

            if len(child_text) > 0:
                text_sections.append(child_text)

        return '\n'.join(text_sections) if len(text_sections) > 0 else None

    def _parse_body_text(self, article_section: Tag) -> Optional[str]:
        """Parses the body text from NHK article HTML.

        Args:
            article_section: Tag containing NHK article HTML.

        Returns:
            The parsed body text from article_section, or None if no body text
            could be parsed.
        """
        body_tags = []
        for id_ in self._ARTICLE_BODY_IDS:
            divs = article_section.find_all('div', id=id_)
            _log.debug(f'Found {len(divs)} with id "{id_}"')
            body_tags += divs

        for class_ in self._ARTICLE_BODY_CLASSES:
            divs = article_section.find_all('div', class_=class_)
            _log.debug(f'Found {len(divs)} with class "{class_}"')
            body_tags += divs

        body_text_sections = []
        for tag in body_tags:
            text = self._parse_body_div(tag)
            if text is not None and len(text) > 0:
                body_text_sections.append(text)

        if len(body_text_sections) == 0:
            return None
        else:
            return '\n\n'.join(body_text_sections)

    def _parse_article(
        self, article_section: Tag, url: str
    ) -> JpnArticle:
        """Parses data from NHK article HTML.

        This function is best effort. If the parsing for any data for the
        article fails, the parsing failures will be logged as errors if
        unexpected, and the attribute for that data will be None in the
        returned Article object.

        Args:
            article_section: Tag containing NHK article HTML.
            url: url where article_section was found.

        Returns:
            Article object containing the parsed data from article_section.
        """
        article_data = JpnArticle()
        article_data.scraped_datetime = datetime.utcnow()
        article_data.source_url = url
        article_data.source_name = self._SOURCE_NAME

        article_data.title = self._parse_title(article_section)
        article_data.publication_datetime = (
            self._parse_publication_datetime(article_section)
        )

        body_text = self._parse_body_text(article_section)
        article_data.full_text = f'{article_data.title}\n\n{body_text}'
        article_data.alnum_count = utils.get_alnum_count(
            article_data.full_text
        )

        return article_data

    def scrape_article(self, url: str) -> JpnArticle:
        """Scrapes and parses an NHK News Web article.

        This function is generally best effort. An exception will be raised if
        the page at url can't be reached or if the page format can't be parsed
        at all, but if anything from the page can be parsed, an Article object
        will be returned with whatever the crawler could successfully parse.

        Args:
            url: url to a page containing an NHK News Web article.

        Returns:
            Article object with the parsed data from the article. If an
            attribute is None in the returned object, the crawler was unable to
            parse the data for that attribute from the article.

        Raises:
            HTTPError: An error occurred making a GET request to url.
            CannotParseArticleError: The page at url was not in an expected
                format, so the crawler could not parse any information from it.
        """
        response = utils.get_request_raise_on_error(url, self.session)

        soup = BeautifulSoup(response.content, 'html.parser')
        article_sections = soup.find_all(
            'section', class_=self._ARTICLE_SECTION_CLASS
        )
        if len(article_sections) != 1:
            _log.error(
                f'Found {len(article_sections)} article sections for url '
                f'"{url}"'
            )
            raise CannotParseArticleError(
                f'Page at url "{url}" not in expected article fromat'
            )

        return self._parse_article(article_sections[0], url)
