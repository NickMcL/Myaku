"""Classes for holding data used across the Reibun project."""

import enum
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple

import jaconv

import reibun.utils as utils

_log = logging.getLogger(__name__)


@enum.unique
class InterpSource(enum.Enum):
    """The source of a Japanese lexical item interpretation.

    There are many different methods and resources that can be used interpret a
    Japanese lexical item found in a body of text. This enum can be used to tag
    interpretations with which method or resource was used for it.

    Attributes:
        MECAB: Output from MeCab was directly used.
        JMDICT_MECAB_DECOMP: The base form decomposition of text provided by
            MeCab was used as an index into JMdict.
        JMDICT_SURFACE_FORM: The surface form of text was used as an index
            into JMdict.
        JMDICT_BASE_FORM: The base forms from the base form decomposition of
            text provided by MeCab were concatenated into a single string and
            then used as an index in JMdict.
    """
    MECAB = 1
    JMDICT_MECAB_DECOMP = 2
    JMDICT_SURFACE_FORM = 3
    JMDICT_BASE_FORM = 4


@dataclass
class JpnArticleMetadata(object):
    """The metadata for a Japanese text article.

    Attributes:
        title: The title of the article.
        source_url: The fully qualified URL where the article was found.
        source_name: The human-readable name of the source of the article.
        publication_datetime: The UTC datetime the article was published.
        scraped_datetime: The UTC datetime the article was scraped.
    """
    title: str = None
    source_url: str = None
    source_name: str = None
    publication_datetime: datetime = None
    scraped_datetime: datetime = None

    def __str__(self) -> str:
        """Returns the title and publication time in string format."""
        return '{}--{}'.format(
            self.title,
            self.publication_datetime.isoformat()
        )


@dataclass
@utils.make_properties_work_in_dataclass
class JpnArticle(object):
    """The full text and metadata for a Japanese text article.

    Attributes:
        full_text: The full text of the article. Includes the title.
        metadata: The metadata for the article.
        text_hash: The hex digest of the SHA-256 hash of full_text. Evaluated
            automatically lazily after changes to full_text. Read-only.
        alnum_count: The alphanumeric character count of full_text. Evaluated
            automatically lazily after changes to full_text. Read-only.
        """
    full_text: str = None
    metadata: JpnArticleMetadata = None

    # Read-only
    alnum_count: int = None
    text_hash: str = None

    _full_text: str = field(init=False, repr=False)
    _text_hash: str = field(default=None, init=False, repr=False)
    _text_hash_change: bool = field(default=False, init=False, repr=False)
    _alnum_count: int = field(default=None, init=False, repr=False)
    _alnum_count_change: bool = field(default=False, init=False, repr=False)

    @property
    def full_text(self) -> str:
        """See class docstring for full_text documentation."""
        return self._full_text

    @full_text.setter
    def full_text(self, set_value: str) -> None:
        self._text_hash_change = True
        self._alnum_count_change = True
        self._full_text = set_value

    @property
    def text_hash(self) -> str:
        """See class docstring for text_hash documentation."""
        if self._text_hash_change:
            self._text_hash = (
                hashlib.sha256(self.full_text.encode('utf-8')).hexdigest()
            )
            self._text_hash_change = False

        return self._text_hash

    @property
    def alnum_count(self) -> int:
        """See class docstring for alnum_count documentation."""
        if self._alnum_count_change:
            self._alnum_count = utils.get_alnum_count(self.full_text)
            self._alnum_count_change = False

        return self._alnum_count

    def __str__(self) -> str:
        if self.metadata is None:
            return '<No article metadata>'
        return str(self.metadata)


@dataclass
@utils.make_properties_work_in_dataclass
class JpnLexicalItemInterp(object):
    """An interpretation of a Japanese lexical item.

    From Wikipedia, a lexical item is "a single word, a part of a word, or a
    chain of words that forms the basic elements of a language's vocabulary".
    This includes words, set phrases, idioms, and more. See the Wikipedia page
    "Lexical item" for more information.

    A lexical item found in text may have more than one way to interpret it.
    For example, it could have more than one possible reading or have more than
    one possible part of speech. This class holds all the information for one
    interpretation.

    Attributes:
        base_form: The base (dictionary) form of the lecixal item. Character
            widths will automatically be normalized when setting this attr.
        reading: The reading of the lexical item. This attr will be in
            full-width katakana whenever possible. Setting the attr to a
            non-katakana value will automatically convert it to katakana to the
            extent possible.
        parts_of_speech: The parts of speech of the lexical item. Possibly
            multiple at the same time, so it is a tuple.
        conjugated_type: The name of the conjugation type of the lexical item.
            Not applicable for some parts of speech such as nouns.
        conjugated_form: The name of the conjugated form of the lexical item.
            Not applicable for some parts of speech such as nouns.
        text_form_info: Info related to the specific text form used that may
            not apply to other text forms of the same lexical item (e.g. if the
            text form uses ateji kanji for the lexical item).
        text_form_freq: Info related to how frequently this text form of the
            lexical item is used in Japanese. See JMdict schema for how to
            decode this info.
        fields: The fields of application for this lexical item (e.g. food
            term, baseball term, etc.)
        dialect: The dialects that apply for this lexical item (e.g.
            kansaiben).
        misc: Other miscellaneous info recorded for this lexical item from
            JMdict.
        interp_sources: The sources where this interpretation of the lexical
            item came from.
    """
    base_form: str = None
    reading: str = None
    parts_of_speech: Tuple[str, ...] = None
    conjugated_type: str = None
    conjugated_form: str = None
    text_form_info: Tuple[str, ...] = None
    text_form_freq: Tuple[str, ...] = None
    fields: Tuple[str, ...] = None
    dialects: Tuple[str, ...] = None
    misc: Tuple[str, ...] = None
    interp_sources: Tuple[InterpSource, ...] = None

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
@utils.make_properties_work_in_dataclass
class FoundJpnLexicalItem(object):
    """A Japanese lexical item found within a text article.

    Attributes:
        surface_form: The form the lexical item used within the article.
        possible_interps: Detailed information for each of the possible
            interpretations of the lexical item.
        article: The article where the lexical item was found.
        text_pos_abs: The zero-indexed character offset of the start of the
            lexical item from the start of the article.
        text_pos_percent: The percent of the total characters in the article
            ahead of the lecixal item. Automatically set once article and
            text_pos_abs are set. Read-only.
    """
    surface_form: str = None
    possible_interps: List[JpnLexicalItemInterp] = None
    article: JpnArticle = None
    text_pos_abs: int = None

    # Read-only
    text_pos_percent: float = None

    _article: str = field(default=None, init=False, repr=False)
    _text_pos_abs: str = field(default=None, init=False, repr=False)
    _text_pos_percent: str = field(default=None, init=False, repr=False)

    @property
    def article(self) -> JpnArticle:
        """See class docstring for article documentation."""
        return self._article

    @article.setter
    def article(self, set_value: JpnArticle) -> None:
        if set_value is not None and self.text_pos_abs is not None:
            self._text_pos_percent = (
                self.text_pos_abs / len(set_value.full_text)
            )
        self._article = set_value

    @property
    def text_pos_abs(self) -> int:
        """See class docstring for text_pos_abs documentation."""
        return self._text_pos_abs

    @text_pos_abs.setter
    def text_pos_abs(self, set_value: JpnArticle) -> None:
        if set_value is not None and self.article is not None:
            self._text_pos_percent = set_value / len(self.article.full_text)
        self._text_pos_abs = set_value

    @property
    def text_pos_percent(self) -> float:
        """See class docstring for text_pos_percent documentation."""
        return self._text_pos_percent
