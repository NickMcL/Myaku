"""Classes for holding data used across the Reibun project."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

import jaconv

import reibun.utils as utils

_log = logging.getLogger(__name__)


@dataclass
class FoundJpnLexicalItem(object):
    """A single Japanese lexical item found within a block of text.

    In the following descriptions, 'the text' refers to the text block where
    the lexical item was found.

    Attributes:
        surface_form: The form the lexical item used within the text.
        reading: The (best guess) reading of the surface form. This attr will
            be in full-width katakana whenever possible. Setting the attr to a
            non-katakana value will automatically convert it to katakana to the
            extent possible.
        base_form: The base (dictionary) form of the lecixal item. Character
            widths will automatically be normalized when setting the attr.
        parts_of_speech: The parts of speech of the lexical item. Possibly
            multiple, so it is a list.
        conjugated_type: The name of the conjugation type of the token.
        conjugated_form: The name of the conjugated form of the token.
        text_pos_abs: The zero-indexed alnum character offset of the start of
            the lexical item from the start of the text.
        text_pos_percent: The percent of the total alnum characters in the text
            ahead of the lecixal item.
    """
    surface_form: str = None
    reading: str = None
    base_form: str = None
    parts_of_speech: List[str] = None
    conjugated_type: str = None
    conjugated_form: str = None
    text_pos_abs: int = None
    text_pos_percent: float = None

    _base_form: str = field(init=False, repr=False)
    _reading: str = field(init=False, repr=False)

    @property
    def base_form(self) -> str:
        """See class docstring for base_form documentation."""
        return self._base_form

    @base_form.setter
    def base_form(self, set_value: str) -> None:
        if set_value is None:
            self._base_form = None
            return

        self._base_form = utils.normalize_char_width(set_value)

    @property
    def reading(self) -> str:
        """See class docstring for reading documentation."""
        return self._reading

    @reading.setter
    def reading(self, set_value: str) -> None:
        if set_value is None:
            self._reading = None
            return

        normalized_str = utils.normalize_char_width(set_value)
        katakana_str = jaconv.hira2kata(normalized_str)
        self._reading = katakana_str


@dataclass
class JpnArticle(object):
    """The text and metadata for a Japanese text article.

    Attributes:
        title: The title of the article.
        full_text: The full text of the article. Includes the title.
        alnum_count: The total count of the alphanumeric characters within
            the full text of the article.
        source_url: The fully qualified URL where the article was found.
        source_name: The human-readable name of the source of the article.
        publication_datetime: The UTC datetime the article was published.
        scraped_datetime: The UTC datetime the article was scraped.
        found_lexical_items: All of the Japanese lexical items found within the
            article.
        """
    title: str = None
    full_text: str = None
    alnum_count: int = None
    source_url: str = None
    source_name: str = None
    publication_datetime: datetime = None
    scraped_datetime: datetime = None

    found_lexical_items: List[FoundJpnLexicalItem] = None

    def __str__(self) -> str:
        """Returns the title and publication time in string format."""
        return '{}--{}'.format(
            self.title,
            self.publication_datetime.isoformat()
        )
