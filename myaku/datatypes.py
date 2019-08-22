"""Classes for holding data used across the Myaku project."""

import enum
import functools
import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, NamedTuple, Tuple

import myaku.utils as utils
from myaku.errors import MissingDataError

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
class JpnArticleBlog(object):
    """Info for a blog of Japanese text articles.

    Attributes:
        title: Title of the blog.
        author: Name of the author of the blog.
        source_name: Human-readable name of the source website of the blog.
        source_url: Url of the blog homepage.
        start_datetime: UTC datetime when the blog was started.
        last_updated_time: UTC datetime when the blog was last updated.
        rating: Rating score of the blog (scale depends on source).
        rating_count: Number of users that have rated the blog.
        tags: Tags specified for the blog.
        catchphrase: Catchphrase of the blog.
        introduction: Introduction text for the blog.
        article_count: Number of articles published on the blog.
        total_char_count: Total number of characters across all articles of the
            blog.
        comment_count: Number of user comments on the blog.
        follower_count: Number of users following the blog.
        in_serialization: Whether the blog is still in serialization or not.
            True means more articles are expected to be published to the blog,
            and False means no more articles are expected to be published to
            the blog.
        last_crawled_datetime: UTC datetime that the blog was last crawled.
    """
    title: str = None
    author: str = None
    source_name: str = None
    source_url: str = None
    start_datetime: datetime = None
    last_updated_datetime: datetime = None
    rating: float = None
    rating_count: int = None
    tags: List[str] = None
    catchphrase: str = None
    introduction: str = None
    article_count: int = None
    total_char_count: int = None
    comment_count: int = None
    follower_count: int = None
    in_serialization: bool = None
    last_crawled_datetime: datetime = None

    ID_FIELDS: Tuple[str, ...] = field(
        default=(
            'source_name',
            'title',
            'author',
        ),
        init=False,
        repr=False
    )

    def __str__(self) -> str:
        """Returns the title and author in string format."""
        return '{}|{}'.format(self.title, self.author)

    def get_id(self) -> str:
        """Returns the unique id for this blog."""
        id_strs = []
        for id_field in self.ID_FIELDS:
            value = getattr(self, id_field)
            if value is None:
                id_strs.append('')
            elif isinstance(value, datetime):
                id_strs.append(value.timestamp())
            else:
                id_strs.append(str(value))

        return '-'.join(id_strs)


@dataclass
class JpnArticleMetadata(object):
    """The metadata for a Japanese text article.

    Attributes:
        title: Title of the article.
        author: Author of the article.
        source_url: Fully-qualified URL where the article was found.
        source_name: Human-readable name of the source of the article.
        blog: Blog the article was posted to. If None, the article was not
            posted as part of a blog.
        blog_id: A unique id for the blog the article was posted to.
        blog_article_order_num: Overall number of this article in the ordering
            of the articles on the blog this article was posted on.
        blog_section_name: Name of the section of the blog this article was
            posted in.
        blog_section_order_num: Overall number of this section in the ordering
            of the sections on the blog this article was posted on.
        blog_section_article_order_num: Number of this article in the ordering
            of the articles in the section of the blog this article was posted
            in.
        publication_datetime: UTC datetime the article was published.
        last_updated_datetime: UTC datetime of the last update to the article.
        last_crawled_datetime: UTC datetime the article was last crawled.
    """
    title: str = None
    author: str = None
    source_url: str = None
    source_name: str = None
    blog: JpnArticleBlog = None
    blog_id: str = None
    blog_article_order_num: int = None
    blog_section_name: str = None
    blog_section_order_num: int = None
    blog_section_article_order_num: int = None
    publication_datetime: datetime = None
    last_updated_datetime: datetime = None
    last_crawled_datetime: datetime = None

    ID_FIELDS: Tuple[str, ...] = field(
        default=(
            'source_name',
            'blog_id',
            'title',
            'author',
            'publication_datetime',
        ),
        init=False,
        repr=False
    )

    def __str__(self) -> str:
        """Returns the title and publication time in string format."""
        return '{}|{}|{}'.format(
            self.title,
            self.blog,
            self.publication_datetime.isoformat()
        )


@dataclass
@utils.make_properties_work_in_dataclass
class JpnArticle(object):
    """The full text and metadata for a Japanese text article.

    Attributes:
        full_text: The full text of the article. Includes the title.
        alnum_count: The alphanumeric character count of full_text.
        has_video: True if the article contains a video.
        metadata: The source metadata for the article.
        text_hash: The hex digest of the SHA-256 hash of full_text. Evaluated
            automatically lazily after changes to full_text. Read-only.
        database_id: The ID for this article in the Myaku database.
        quality_score: Quality score for this article determined by Myaku.
        """
    full_text: str = None
    alnum_count: int = None
    has_video: bool = None
    metadata: JpnArticleMetadata = None
    database_id: str = None
    quality_score: int = None

    # Read-only
    text_hash: str = None

    _full_text: str = field(init=False, repr=False)
    _text_hash: str = field(default=None, init=False, repr=False)
    _text_hash_change: bool = field(default=False, init=False, repr=False)

    _ARTICLE_LEN_GROUPS: Tuple[int, ...] = field(
        default=(
            1000,
            500,
        ),
        init=False,
        repr=False
    )

    @property
    def full_text(self) -> str:
        """See class docstring for full_text documentation."""
        return self._full_text

    @full_text.setter
    def full_text(self, set_value: str) -> None:
        self._text_hash_change = True
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

    def __str__(self) -> str:
        if self.metadata is None:
            metadata_str = '<No article metadata>'
        else:
            metadata_str = str(self.metadata)
        return '{}|{}'.format(metadata_str, self.quality_score)

    def get_article_len_group(self) -> int:
        """Gets the article alnum length group for the lexical item."""
        if self.alnum_count is None:
            utils.log_and_raise(
                _log, MissingDataError,
                'alnum_count is not set, so cannot get article length group '
                'for {!r}'.format(self)
            )

        for group_min in self._ARTICLE_LEN_GROUPS:
            if self.alnum_count >= group_min:
                return group_min
        return 0

    def get_containing_sentence(
        self, item_pos: 'LexicalItemTextPosition',
        include_end_punctuation: bool = False
    ) -> Tuple[str, int]:
        """Gets the sentence containing the lexical item at item_pos.

        Args:
            item_pos: The position whose containing sentence to get.

        Returns:
            (containing sentence, offset of containing sentence in article)
        """
        if self.full_text is None:
            utils.log_and_raise(
                _log, MissingDataError,
                'full_text is not set, so cannot get containing sentences in '
                '{!r}'.format(self)
            )

        start = utils.find_jpn_sentence_start(
            self.full_text, item_pos.index
        )
        end = utils.find_jpn_sentence_end(
            self.full_text, item_pos.index + item_pos.len
        )

        return (self.full_text[start:end + 1], start)


class JpnLexicalItemInterp(NamedTuple):
    """An interpretation of a Japanese lexical item.

    See the FoundJpnLexicalItem class docstring for info on what a lexical item
    is.

    A lexical item found in text may have more than one way to interpret it.
    For example, it could have more than one possible part of speech. This
    class holds all the information for one interpretation.

    Attributes:
        interp_sources: The sources where this interpretation of the lexical
            item came from.
        mecab_interp: An interpretation of the lexical item from MeCab.
        jmdict_interp_entry_id: The entry sequence number of a JMdict entry
            that is an interpretation of the lexical item.
    """
    interp_sources: Tuple[InterpSource, ...]
    mecab_interp: 'MecabLexicalItemInterp' = None
    jmdict_interp_entry_id: str = None


class MecabLexicalItemInterp(NamedTuple):
    """An interpretation of a lexical item from MeCab.

    Attributes:
        parts_of_speech: The parts of speech of the lexical item. Possibly
            multiple at the same time, so it is a tuple.
        conjugated_type: The name of the conjugation type of the lexical item.
            Not applicable for some parts of speech such as nouns.
        conjugated_form: The name of the conjugated form of the lexical item.
            Not applicable for some parts of speech such as nouns.
    """
    parts_of_speech: Tuple[str, ...]
    conjugated_type: str = None
    conjugated_form: str = None


class LexicalItemTextPosition(NamedTuple):
    """The index and length of a lexical item in a body of text.

    The lexical item can be retrieved from its containing body of text with the
    slice [index:index + len].

    Attributes:
        index: The index of the first character of the lexical item in
            its containing body of text.
        len: The length of the lexical item.
    """
    index: int
    len: int

    def slice(self) -> slice:
        """Returns slice for getting the lexical item from its containing text.

        If "text" is a variable with the containing text for the lexical item
        and "obj" is a LexicalItemTextPosition object, can be called like
        "text[obj.slice()]" to get the lexical item from the text.
        """
        return slice(self.index, self.index + self.len)


@dataclass
@utils.make_properties_work_in_dataclass
class FoundJpnLexicalItem(object):
    """A Japanese lexical item found within a text article.

    From Wikipedia, a lexical item is "a single word, a part of a word, or a
    chain of words that forms the basic elements of a language's vocabulary".
    This includes words, set phrases, idioms, and more. See the Wikipedia page
    "Lexical item" for more information.

    Attributes:
        base_form: The base (dictionary) form of the lexical item. Character
            widths will automatically be normalized when setting this attr.
        article: The article where the lexical item was found.
        found_positions: All of the positions the lexical item was found at in
            the article.
        possible_interps: Each of the possible interpretations of the lexical
            item in the article. If the lexical item could actually be
            interpreted as different lexical items with the same base form,
            each interpretation will be in this list.
        interp_position_map: If one of the possible interpretations for the
            lexical item only applies to a subset of the positions the lexical
            item was found in the article, an entry mapping the interpretation
            to the subset of the positions it applies to will be in this dict.

            If an interpretation applies to all positions the lexical items was
            found in the article, that interpretation will not have an entry in
            this dict.
        article_quality_score_modifier: The modifier for this found lexical
            item that can be added to the base quality score for its article
            to get the quality score for the article in terms of demonstrating
            usage of this lexical item.
        database_id: The ID of this lexical item in the Myaku database.
    """
    base_form: str = None
    article: JpnArticle = None
    found_positions: List[LexicalItemTextPosition] = None
    possible_interps: List[JpnLexicalItemInterp] = None
    interp_position_map: (
        Dict[JpnLexicalItemInterp, List[LexicalItemTextPosition]]
    ) = field(default_factory=dict)
    article_quality_score_modifier: int = None
    database_id: str = None

    _base_form: str = field(init=False, repr=False)
    _surface_form_cache: Dict[LexicalItemTextPosition, str] = (
        field(default_factory=dict, init=False, repr=False)
    )

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

    def get_first_surface_form(self) -> str:
        """Returns surface form at the first position in found_positions."""
        first_pos = self.found_positions[0]
        if first_pos in self._surface_form_cache:
            return self._surface_form_cache[first_pos]

        _log.debug(
            'Surface form cache miss for base form "%s" at position %s',
            self.base_form, first_pos
        )
        surface_form = self.article.full_text[first_pos.slice()]
        self._surface_form_cache[first_pos] = surface_form
        return surface_form

    def cache_surface_form(
        self, surface_form: str, text_pos: LexicalItemTextPosition
    ) -> None:
        """Adds surface form to a cache for quick retrieval later."""
        self._surface_form_cache[text_pos] = surface_form

    def _text_position_quality_key(
        self, text_pos: LexicalItemTextPosition
    ) -> Tuple[Any, ...]:
        """Key function for getting quality of a lexical item text position."""
        if self.article is None:
            utils.log_and_raise(
                _log, MissingDataError,
                'article is not set, so cannot generate quality key value for '
                '{!r}'.format(text_pos)
            )

        key_list = []
        key_list.append(utils.get_alnum_count(
            self.article.get_containing_sentence(text_pos)[0]
        ))
        key_list.append(-1 * text_pos.index)
        key_list.append(text_pos.len)

        return tuple(key_list)

    def sort_found_positions_by_quality(self) -> None:
        """Sorts the found positions of the lexical item by their quality."""
        self.found_positions.sort(
            key=self._text_position_quality_key, reverse=True
        )

        if not self.interp_position_map:
            return
        for pos_list in self.interp_position_map.values():
            pos_list.sort(key=self._text_position_quality_key, reverse=True)

    def quality_key(self) -> Tuple[Any, ...]:
        """Key function for getting usage quality of the found lexical item."""
        required_attrs = [
            ('article', self.article),
            ('article.full_text', self.article.full_text),
            ('article.has_video', self.article.has_video),
            ('article.alnum_count', self.article.alnum_count),
            ('article.text_hash', self.article.text_hash),
            ('article.metadata', self.article.metadata),
            ('article.metadata.publication_datetime',
                self.article.metadata.publication_datetime),
            ('found_positions', self.found_positions),
        ]
        for attr in required_attrs:
            if attr[1] is None:
                utils.log_and_raise(
                    _log, MissingDataError,
                    '{} is not set, so cannot generate quality key value for '
                    '{}'.format(attr[0], self)
                )

        key_list = []
        key_list.append(int(self.article.has_video))
        key_list.append(len(self.found_positions))
        key_list.append(self.article.get_article_len_group())
        key_list.append(self.article.metadata.publication_datetime)
        key_list.append(self.article.alnum_count)
        key_list.append(self.article.text_hash)

        return tuple(key_list)


def reduce_found_lexical_items(
        found_lexical_items: List[FoundJpnLexicalItem]
) -> List[FoundJpnLexicalItem]:
    """Reduces the found lexical items to the minimum size equivalent set.

    Combines all found lexical items in the set with the same base form and
    article into one item each.

    Does not modify the given list.

    Args:
        found_lexical_items: A list of found lexical items to reduce.

    Returns:
        A list containing the minimum number of found lexical item objects
        needed to represent the data in the given found lexical items.
    """
    article_id_map = {}
    base_form_interp_map = defaultdict(functools.partial(defaultdict, set))
    for fli in found_lexical_items:
        article_id_map[id(fli.article)] = fli.article
        base_form_article_pair = (fli.base_form, id(fli.article))
        for interp in fli.possible_interps:
            base_form_interp_map[base_form_article_pair][interp].update(
                set(fli.found_positions)
            )

    reduced_flis = []
    for ((base_form, article_id), interp_map) in base_form_interp_map.items():
        new_fli = FoundJpnLexicalItem(
            base_form=base_form,
            article=article_id_map[article_id],
            possible_interps=[]
        )

        found_positions_set = set()
        for interp, interp_pos_set in interp_map.items():
            new_fli.possible_interps.append(interp)
            found_positions_set.update(interp_pos_set)
        new_fli.found_positions = list(found_positions_set)

        for interp, interp_pos_set in interp_map.items():
            if interp_pos_set != found_positions_set:
                new_fli.interp_position_map[interp] = list(interp_pos_set)

        reduced_flis.append(new_fli)

    _log.debug(
        'Reduced %s found lexical items to %s',
        len(found_lexical_items), len(reduced_flis)
    )
    return reduced_flis
