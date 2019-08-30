"""Classes for holding data used across the Myaku project."""

import enum
import functools
import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from operator import attrgetter
from typing import Dict, List, NamedTuple, Tuple

from myaku import utils
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
class Crawlable(object):
    """An item that can be crawled by a Myaku crawler.

    Attributes:
        source_name: Human-readable name of the source website of the item.
        source_url: Url of the item.
        publication_datetime: UTC datetime when the item was first published.
        last_updated_datetime: UTC datetime of the last update to the item.
        last_crawled_datetime: UTC datetime when the item was last crawled.
    """
    source_name: str = None
    source_url: str = None
    publication_datetime: datetime = None
    last_updated_datetime: datetime = None
    last_crawled_datetime: datetime = None


@dataclass
class JpnArticleBlog(Crawlable):
    """Info for a blog of Japanese text articles.

    Attributes:
        title: Title of the blog.
        author: Name of the author of the blog.
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
    """
    title: str = None
    author: str = None
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

    def __str__(self) -> str:
        """Returns the title and author in string format."""
        return '{}|{}'.format(self.title, self.author)


class ArticleTextPosition(NamedTuple):
    """The index and length of a segment of text in an article.

    The segment can be retrieved from its containing article text with the
    slice [index:index + len].

    Attributes:
        index: The index of the first character of the text segment in the
            article text.
        len: The length of the text segment.
    """
    index: int
    len: int

    def slice(self) -> slice:
        """Returns slice for getting the text segment from its article text."""
        return slice(self.index, self.index + self.len)


@dataclass
@utils.make_properties_work_in_dataclass
class JpnArticle(Crawlable):
    """The full text and metadata for a Japanese text article.

    Attributes:
        title: Title of the article.
        author: Author of the article.
        full_text: The full text of the article. Includes the title.
        alnum_count: The alphanumeric character count of full_text.
        has_video: True if the article contains a video.
        tags: Tags specified for the article. Vary based on article source.
        blog: Blog the article was posted to. If None, the article was not
            posted as part of a blog.
        blog_article_order_num: Overall number of this article in the ordering
            of the articles on the blog this article was posted on.
        blog_section_name: Name of the section of the blog this article was
            posted in.
        blog_section_order_num: Overall number of this section in the ordering
            of the sections on the blog this article was posted on.
        blog_section_article_order_num: Number of this article in the ordering
            of the articles in the section of the blog this article was posted
            in.
        database_id: The ID for this article in the Myaku database.
        quality_score: Quality score for this article determined by Myaku.
        text_hash: The hex digest of the SHA-256 hash of full_text. Evaluated
            automatically lazily after changes to full_text. Read-only.
        """
    title: str = None
    author: str = None
    full_text: str = None
    alnum_count: int = None
    has_video: bool = None
    tags: List[str] = None
    blog: JpnArticleBlog = None
    blog_article_order_num: int = None
    blog_section_name: str = None
    blog_section_order_num: int = None
    blog_section_article_order_num: int = None
    database_id: str = None
    quality_score: int = None

    # Read-only
    text_hash: str = None

    _full_text: str = field(init=False, repr=False)
    _text_hash: str = field(default=None, init=False, repr=False)
    _text_hash_change: bool = field(default=False, init=False, repr=False)

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
            if self.full_text:
                self._text_hash = (
                    hashlib.sha256(self.full_text.encode('utf-8')).hexdigest()
                )
            else:
                self._text_hash = None
            self._text_hash_change = False

        return self._text_hash

    def __str__(self) -> str:
        """Returns the identifying data for the article in string format."""
        return '|'.join([
            self.title,
            self.source_url,
            str(self.blog),
            self.publication_datetime.isoformat(),
            str(self.quality_score)
        ])

    def get_containing_sentence(
        self, item_pos: ArticleTextPosition
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

    def group_text_positions_by_sentence(
        self, text_positions: List[ArticleTextPosition]
    ) -> List[Tuple[ArticleTextPosition, Tuple[ArticleTextPosition, ...]]]:
        """Groups a list of text positions by their containing sentences.

        Args:
            text_positions: List of of text positions in this article.

        Returns:
            A list of (sentence position, contained text positions) tuples. The
            tuples are sorted by sentence start index.
        """
        sentence_groups = defaultdict(list)
        end = -1
        for pos in sorted(text_positions, key=attrgetter('index')):
            if pos.index > end:
                start = utils.find_jpn_sentence_start(
                    self.full_text, pos.index
                )
                end = utils.find_jpn_sentence_end(
                    self.full_text, pos.index + pos.len
                )
            sentence_groups[
                ArticleTextPosition(start, end - start + 1)
            ].append(pos)

        group_tuples = []
        for sentence_pos, text_pos_list in sentence_groups.items():
            group_tuples.append((sentence_pos, tuple(text_pos_list)))

        return group_tuples


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
        quality_score_mod: The modifier for this found lexical item that can be
            added to the base quality score for its article to get the quality
            score for the article in terms of demonstrating usage of this
            lexical item.
        database_id: The ID of this lexical item in the Myaku database.
    """
    base_form: str = None
    article: JpnArticle = None
    found_positions: List[ArticleTextPosition] = None
    possible_interps: List[JpnLexicalItemInterp] = None
    interp_position_map: (
        Dict[JpnLexicalItemInterp, List[ArticleTextPosition]]
    ) = field(default_factory=dict)
    quality_score_mod: int = None
    database_id: str = None

    _base_form: str = field(init=False, repr=False)
    _surface_form_cache: Dict[ArticleTextPosition, str] = (
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
        self, surface_form: str, text_pos: ArticleTextPosition
    ) -> None:
        """Adds surface form to a cache for quick retrieval later."""
        self._surface_form_cache[text_pos] = surface_form


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
