"""Scorers for individual factors of articles."""

import logging
import math
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, List, Tuple, TypeVar

from typing_extensions import Protocol

from myaku.crawlers import KakuyomuCrawler
from myaku.datatypes import FoundJpnLexicalItem, JpnArticle

T = TypeVar('T')
C = TypeVar('C', bound='SameTypeComparable')

_log = logging.getLogger(__name__)

_MAX_FACTOR_SCORE = 1000


class SameTypeComparable(Protocol):
    """Protocol for supporting same type order comparison operators."""
    @abstractmethod
    def __eq__(self, other: Any) -> bool:  # noqa: D105
        pass

    @abstractmethod
    def __lt__(self: T, other: T) -> bool:  # noqa: D105
        pass

    @abstractmethod
    def __le__(self: T, other: T) -> bool:  # noqa: D105
        pass

    @abstractmethod
    def __gt__(self: T, other: T) -> bool:  # noqa: D105
        pass

    @abstractmethod
    def __ge__(self: T, other: T) -> bool:  # noqa: D105
        pass


class ValueRangeMultipliers(Generic[C]):
    """Stores the multipliers for all ranges of a value."""

    def __init__(self, value_range_tuples: List[Tuple[C, float]]) -> None:
        """Set the value ranges the scores should used.

        Args:
            value_range_tuples: A list of 2-tuples that defines the value
                ranges and their respective scores.

                The first value of the tuple indicates the inclusive upper end
                of a value range, and the second value indicates the score for
                that range.

                The lower value for each range is set as the first value of the
                tuple preceding the range tuple in the list. In the case of the
                first range tuple in the list, it has no lower bound on its
                range.

                The last tuple in the list should have a first value of None to
                indicate that the last range has no upper bound.

                For example, if the given range_tuple_list was:

                    [(5, 0.5), (10, 0.8), (None, 1)]

                Values in the range (-infinity, 5] would get a score of 0.5,
                value in the range (5, 10] would get a score of 0.8, and values
                in the range (10, infinity) would get a score of 1.
        """
        if None not in {t[0] for t in value_range_tuples}:
            raise ValueError('No range with no upper bound defined')

        self._value_range_tuples = value_range_tuples

    def get_value_multiplier(self, value: C) -> float:
        """Get multiplier for a value based on which value range it is in."""
        for (range_upper_bound, multiplier) in self._value_range_tuples:
            if range_upper_bound is None:
                return multiplier
            if value <= range_upper_bound:
                return multiplier

        # Should never happen because of check in __init__
        raise ValueError('No range with no upper bound defined')

    def __getitem__(self, value: C) -> float:
        """Alternative way to call get_value_multiplier(value)."""
        return self.get_value_multiplier(value)

    def get_range_boundary_values(self) -> List[C]:
        """Get the range boundary values set for the object.

        The returned list of values will be sorted in ascending order.
        """
        return [t[0] for t in self._value_range_tuples if t[0] is not None]


class ArticleFactorScorer(ABC):
    """ABC for an article scorer for a single factor."""

    @abstractmethod
    def score_article(self, article: JpnArticle) -> int:
        """Score an article for the factor for this class.

        Args:
            article: The article to be scored.

        Returns:
            A normalized score between [-_MAX_FACTOR_SCORE, _MAX_FACTOR_SCORE]
            representing how high quality the article is in terms of the factor
            considered by this class.
        """
        return 0


class HasVideoScorer(ArticleFactorScorer):
    """Scorer based on whether an article has a video or not."""

    def score_article(self, article: JpnArticle) -> int:
        """Score an article based on whether it has a video or not.

        Args:
            article: The article to be scored.

        Returns:
            MAX_FACTOR_SCORE if the article has a video, 0 if it does not.
        """
        if article.has_video:
            return _MAX_FACTOR_SCORE
        return 0


class ArticleLengthScorer(ArticleFactorScorer):
    """Scorer based on alnum length of article."""

    _LENGTH_RANGE_MULTIPLIERS = ValueRangeMultipliers([
        (100, -1),
        (200, -0.5),
        (300, 0),
        (400, 0.2),
        (500, 0.6),
        (700, 0.8),
        (1000, 1),
        (1300, 0.8),
        (1500, 0.6),
        (1700, 0.4),
        (1900, 0.2),
        (2100, 0),
        (2500, -0.5),
        (None, -1)
    ])

    def score_article(self, article: JpnArticle) -> int:
        """Score an article based on its alnum length.

        An alnum length around 1000 characters is considered the best because
        it is long enough to have plenty of context around lexical item usage
        while being short enough to be quickly readable.

        As article length gets shorter or longer than that, the article's
        length score decreases.

        Args:
            article: The article to be scored.

        Returns:
            The score for the alnum length of the article.
        """
        multiplier = self._LENGTH_RANGE_MULTIPLIERS[article.alnum_count]
        return math.floor(_MAX_FACTOR_SCORE * multiplier)


class PublicationRecencyScorer(ArticleFactorScorer):
    """Scorer based on how recently the article was published."""

    RECENCY_RANGE_MULTIPLIERS = ValueRangeMultipliers([
        (7, 1),
        (30, 0.9),
        (90, 0.6),
        (180, 0.4),
        (365, 0.2),
        (365 * 3, 0),
        (None, -0.2)
    ])

    def score_article(self, article: JpnArticle) -> int:
        """Score an article based on the recency of its publication.

        The more recently an article was published, the higher it is scored. If
        an article is many years old, it will get a slight negative score.

        Args:
            article: The article to be scored.

        Returns:
            The score for the recency of the publication of the article.
        """
        multiplier = self.RECENCY_RANGE_MULTIPLIERS[
            (datetime.utcnow() - article.last_updated_datetime).days
        ]
        return math.floor(_MAX_FACTOR_SCORE * multiplier)


class BlogArticleOrderScorer(ArticleFactorScorer):
    """Scorer based on the order position of an article in its blog."""

    _BLOG_FIRST_ARTICLE_MULTIPLIER = 1
    _SECTION_FIRST_ARTICLE_MULTIPLIER = 0.5

    def score_article(self, article: JpnArticle) -> int:
        """Score an article based on its order position in its blog.

        If an article is the first article in a section of a blog, it generally
        will require less context to understand and enjoy reading compared to
        articles in the middle of a section of a blog, so it is scored higher.

        Articles that are the very first article in a blog are especially
        scored the highest since they generally require no context from the
        rest of the blog at all to understand an enjoy.

        Articles that are either not part of a blog or that are in the middle
        of section of the blog are scored neutrally, not negatively.

        Args:
            article: The article to be scored.

        Returns:
            The score for the order position of the article in its blog.
        """
        blog_order_num = article.blog_article_order_num
        if blog_order_num is not None and blog_order_num == 1:
            return math.floor(
                _MAX_FACTOR_SCORE * self._BLOG_FIRST_ARTICLE_MULTIPLIER
            )

        section_order_num = article.blog_section_order_num
        if section_order_num is not None and section_order_num == 1:
            return math.floor(
                _MAX_FACTOR_SCORE * self._SECTION_FIRST_ARTICLE_MULTIPLIER
            )

        return 0


class BlogRatingScorer(ArticleFactorScorer):
    """Scorer based on the rating of the blog for an article."""

    _FIXED_SOURCE_MULTIPLIER_MAP = {
        'NHK News Web': 0.25,
        'Asahi Shinbun': 0.25,
    }

    _KAKUYOMU_STAR_RANGE_MULTIPLIERS = ValueRangeMultipliers([
        (5, -0.5),
        (10, -0.25),
        (20, 0),
        (30, 0.25),
        (50, 0.5),
        (70, 0.7),
        (100, 0.8),
        (None, 1)
    ])

    def score_article(self, article: JpnArticle) -> int:
        """Score an article based on the rating of its blog.

        The way blogs are rated depends on the source of the article, so a
        different scheme is used for each source, but generally, articles with
        higher rated blogs score higher.

        Sources without a blog concept such as news site get a fixed score for
        all articles.

        Args:
            article: The article to be scored.

        Returns:
            The score for the rating of the blog for the article.
        """
        if article.source_name in self._FIXED_SOURCE_MULTIPLIER_MAP:
            return math.floor(
                _MAX_FACTOR_SCORE
                * self._FIXED_SOURCE_MULTIPLIER_MAP[article.source_name]
            )
        elif article.source_name == KakuyomuCrawler.SOURCE_NAME:
            return self._score_kakuyomu_article(article)
        else:
            raise ValueError(
                'Unrecoginzed article source: {}'.format(article.source_name)
            )

    def _score_kakuyomu_article(self, article: JpnArticle) -> int:
        """Score a Kakuyomu article based on the star rating of its series.

        Args:
            article: The Kakuyomu article to be scored.

        Returns:
            The score for the star rating of the series for the Kakuyomu
            article.
        """
        multiplier = self._KAKUYOMU_STAR_RANGE_MULTIPLIERS[
            int(article.blog.rating)
        ]
        return math.floor(_MAX_FACTOR_SCORE * multiplier)


class FoundLexicalItemModifierFactorScorer(ABC):
    """ABC for a found lexical item modifier scorer for a single factor.

    The found lexical item modifier can be added to the quality score for the
    article for that found lexical item to get the quality score for that
    article as a usage demonstration for that lexical item.
    """

    @abstractmethod
    def score_fli_modifier(self, fli: FoundJpnLexicalItem) -> int:
        """Score a found lexical item modifier for the factor for this class.

        Args:
            fli: The found lexical item whose modifier to score.

        Returns:
            A normalized modifier score between
            [-_MAX_FACTOR_SCORE, _MAX_FACTOR_SCORE] representing how high or
            low the quality of the found lexical item's article is for
            demonstrating the usage of that lexical item.
        """
        return 0


class TermFrequencyScorer(FoundLexicalItemModifierFactorScorer):
    """Scorer based on how many times the fli is used in its article."""

    _TERM_FREQUENCY_RANGE_MULTIPLIERS = ValueRangeMultipliers([
        (1, 0),
        (2, 0.25),
        (3, 0.5),
        (4, 0.75),
        (None, 1),
    ])

    def score_fli_modifier(self, fli: FoundJpnLexicalItem) -> int:
        """Score an fli modifier based on its term frequency in its article.

        If the found lexical item is used more times in an article, then it
        will have a higher modifier score.

        Args:
            fli: The found lexical item whose modifier to score.

        Returns:
            The term frequency modifier score for the found lexical item.
        """
        multiplier = self._TERM_FREQUENCY_RANGE_MULTIPLIERS[
            len(fli.found_positions)
        ]
        return math.floor(_MAX_FACTOR_SCORE * multiplier)
