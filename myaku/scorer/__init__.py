"""Quality scorer for articles."""

import logging
import math

from myaku.datatypes import FoundJpnLexicalItem, JpnArticle
from myaku.scorer.factor_scorers import (
    ArticleLengthScorer,
    BlogArticleOrderScorer,
    BlogRatingScorer,
    HasVideoScorer,
    PublicationRecencyScorer,
    TermFrequencyScorer,
)

_log = logging.getLogger(__name__)


class MyakuArticleScorer(object):
    """Scorer for determining the quality of articles for use in Myaku.

    Articles are scored based on how good of an example they are at
    demonstrating native Japanese usage of the lexical items used within them.
    """

    # 2-tuples in format (ArticleFactorScorer, factor weight)
    _ARTICLE_SCORE_FACTORS = [
        (ArticleLengthScorer(), 3),
        (BlogArticleOrderScorer(), 1),
        (BlogRatingScorer(), 2),
        (HasVideoScorer(), 1),
        (PublicationRecencyScorer(), 2),
    ]

    # 2-tuples in format (FoundLexicalItemModifierFactorScorer, factor weight)
    _FLI_MODIFIER_SCORE_FACTORS = [
        (TermFrequencyScorer(), 3),
    ]

    def score_article(self, article: JpnArticle) -> None:
        """Score the quality of an article.

        Sets the score as the quality_score attr of the article.

        If the quality score is higher/lower, it means the article is a
        better/worse example for demonstrating native Japanese usage of the
        lexical items used within it.

        The quality score can be compared to other article scores to determine
        which is a higher quality for learning.

        Args:
            article: The article to score.
        """
        article_score = 0
        for (scorer, factor_weight) in self._ARTICLE_SCORE_FACTORS:
            article_score += math.floor(
                scorer.score_article(article) * factor_weight
            )
        article.quality_score = article_score

    def score_fli_modifier(self, fli: FoundJpnLexicalItem) -> None:
        """Determine the article score modifier for a found lexical item.

        Sets the score as the quality_score_mod attr of the found lexical item.

        The score_article function gives the base quality score of an article,
        but the quality of an article in terms of demenostrating usage of a
        lexical items varies depending on the lexical item.

        This function determines a modifier for a found lexical item that can
        be added to the base quality score for the article for that found
        lexical item to get the quality score for the article in terms of
        demonstrating usage of that specific lexical item.

        Args:
            fli: The found lexical item whose article score modifier to
                determine.
        """
        fli_modifier_score = 0
        for (scorer, factor_weight) in self._FLI_MODIFIER_SCORE_FACTORS:
            fli_modifier_score += math.floor(
                scorer.score_fli_modifier(fli) * factor_weight
            )
        fli.quality_score_mod = fli_modifier_score
