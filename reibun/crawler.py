import functools
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime

import pytz
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.DEBUG)


def add_debug_logging(func):
    """Logs on func entrance and exit"""
    @functools.wraps(func)
    def wrapper_add_debug_logging(*args, **kwargs):
        args_repr = [repr(arg)[:100] for arg in args]
        kwargs_repr = [f'{k}={v!r}'[:100] for k, v in kwargs.items()]
        func_args = ', '.join(args_repr + kwargs_repr)
        logging.debug(f'Calling {func.__name__}({func_args})')
        try:
            value = func(*args, *kwargs)
        except BaseException:
            logging.debug(
                f'{func.__name__} raised exception: %s',
                sys.exc_info()[0]
            )
            raise

        logging.debug(f'{func.__name__} returned {value!r}')
        return value
    return wrapper_add_debug_logging


def add_method_debug_logging(cls):
    """Applys the add_debug_logging decorator to all methods in class"""
    for attr_name in cls.__dict__:
        attr = getattr(cls, attr_name)
        if callable(attr) and not isinstance(attr, type):
            setattr(cls, attr_name, add_debug_logging(attr))
    return cls


class MalformedPageError(Exception):
    pass


@dataclass
class ArticleMetadata:
    """Contains the metadata for an article.

    Does not contain the actual full text of the article.
    """
    title: str = None
    character_count: int = None
    source_url: str = None
    source_name: str = None
    creation_datetime: datetime = None
    scraped_datetime: datetime = None


@dataclass
class Article:
    """In addition to metadata, contains the full text of an article"""
    metadata: ArticleMetadata = ArticleMetadata()
    body_text: str = None


@add_method_debug_logging
class Crawler:
    """Crawls and scrapes articles for the web"""
    SOURCE_NAME = 'NHK News Web'
    ARTICLE_DATETIME_FORMAT = '%Y-%m-%dT%H:%M'
    ARTICLE_SECTION_CLASS = 'detail-no-js'
    ARTICLE_TITLE_CLASS = 'contentTitle'

    ARTICLE_BODY_IDS = [
        'news_textbody',
        'news_textmore',
    ]
    ARTICLE_BODY_CLASSES = [
        'news_add',
    ]

    ALLOWABLE_TAGS_IN_TEXT = {
        'a', 'b', 'blockquote', 'br', 'em', 'strong', 'sup'
    }

    HTML_TAG_REGEX = re.compile(r'<.*?>')

    JAPAN_TIMEZONE = pytz.timezone('Japan')

    def __init__(self, timeout=10):
        self.session = None
        self.timeout = timeout

    def __enter__(self):
        self.session = requests.Session()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.session:
            self.session.close()

    def _contains_valid_child_text(self, tag):
        for descendant in tag.descendants:
            if (descendant.name is not None and
                    descendant.name not in self.ALLOWABLE_TAGS_IN_TEXT):
                logging.debug(
                    f'Child text contains invalid {descendant.name} tag: %s',
                    str(tag)
                )
                return False
        return True

    def _get_valid_child_text(self, tag):
        if not self._contains_valid_child_text(tag):
            return None

        return re.sub(self.HTML_TAG_REGEX, '', str(tag))

    def _get_article_title(self, article_section):
        title_spans = article_section.find_all(
            'span', class_=self.ARTICLE_TITLE_CLASS
        )

        if len(title_spans) != 1:
            logging.error(f'Found {len(title_spans)} title spans')
            return None

        title = self._get_valid_child_text(title_spans[0])
        if title is None:
            logging.error(
                'Unable to determine title from span tag: %s',
                str(title_spans[0])
            )
            return None

        return title

    def _get_article_creation_datetime(self, article_section):
        time_tags = article_section.find_all('time')

        if len(time_tags) != 1:
            logging.error(f'Found {len(time_tags)} time tags')
            return None

        if not time_tags[0].has_attr('datetime'):
            logging.error(
                'Time tag has no datetime attribute: %s',
                str(time_tags[0])
            )
            return None

        try:
            creation_datetime = datetime.strptime(
                time_tags[0]['datetime'], self.ARTICLE_DATETIME_FORMAT
            )
        except ValueError:
            logging.error(
                'Failed to parse datetime: %s', time_tags[0]['datetime']
            )
            return None

        local_creation_datetime = self.JAPAN_TIMEZONE.localize(
            creation_datetime, is_dst=None
        )
        return local_creation_datetime.astimezone(pytz.utc)

    def _get_body_section_text(self, tag):
        section_text = self._get_valid_child_text(tag)
        if section_text is not None:
            return section_text

        text_sections = []
        for child in tag.children:
            # Skip text around child tags such as '\n'
            if child.name is None:
                continue

            child_text = self._get_valid_child_text(child)
            if child_text is None:
                logging.error(
                    f'Unable to determine body text from tag: %s',
                    str(child)
                )
                continue

            text_sections.append(child_text)

        return '\n'.join(text_sections) if len(text_sections) > 0 else None

    def _get_article_body_text(self, article_section):
        body_tags = []
        for id_ in self.ARTICLE_BODY_IDS:
            divs = article_section.find_all('div', id=id_)
            logging.debug(f'Found {len(divs)} with id {id_}')
            body_tags += divs

        for class_ in self.ARTICLE_BODY_CLASSES:
            divs = article_section.find_all('div', class_=class_)
            logging.debug(f'Found {len(divs)} with class {class_}')
            body_tags += divs

        body_text_sections = []
        for tag in body_tags:
            text = self._get_body_section_text(tag)
            if text is not None:
                body_text_sections.append(text)

        return '\n\n'.join(body_text_sections)

    def _get_article_data(self, article_section, url):
        article_data = Article()
        article_data.metadata.scraped_datetime = datetime.utcnow()
        article_data.metadata.source_url = url
        article_data.metadata.source_name = self.SOURCE_NAME

        article_data.metadata.title = self._get_article_title(article_section)
        article_data.metadata.creation_datetime = (
            self._get_article_creation_datetime(article_section)
        )

        article_data.body_text = self._get_article_body_text(article_section)
        article_data.metadata.character_count = (
            sum(c.isalnum() for c in article_data.metadata.title) +
            sum(c.isalnum() for c in article_data.body_text)
        )

        return article_data

    def scrape_article(self, url):
        logging.info(f'Navigating to {url}')
        response = requests.get(url, timeout=self.timeout)
        logging.info(f'Response received with status {response.status_code}')
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        article_sections = soup.find_all(
            'section', class_=self.ARTICLE_SECTION_CLASS
        )
        if len(article_sections) != 1:
            logging.error(f'Found {len(article_sections)} for {url}')
            raise MalformedPageError()

        return self._get_article_data(article_sections[0], url)
