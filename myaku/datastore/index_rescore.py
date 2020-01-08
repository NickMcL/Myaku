"""Functions for rescoring articles in the Myaku article index.

Rescoring articles is necessary because the recency of an article affects its
quality score. This means that the quality score must be periodically decreased
over time as an article becomes less and less recent.
"""

import logging
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timedelta
from pprint import pformat
from typing import DefaultDict, Dict, Iterator, List

from bson.objectid import ObjectId

from myaku import utils
from myaku.datastore import DataAccessMode, Document, Query
from myaku.datastore.cache import CacheUpdateResult, FirstPageCache
from myaku.datastore.database import ArticleIndexDb
from myaku.datastore.document_convert import (
    convert_docs_to_articles,
    convert_docs_to_blogs,
    convert_docs_to_found_lexical_items,
)
from myaku.datastore.index_search import ArticleIndexSearcher
from myaku.datatypes import (
    ArticleRankKey,
    FoundJpnLexicalItem,
    JpnArticle,
    JpnArticleBlog,
)
from myaku.scorer import MyakuArticleScorer
from myaku.scorer.factor_scorers import PublicationRecencyScorer

_log = logging.getLogger(__name__)


@utils.add_debug_logging
def rescore_article_index() -> None:
    """Rescore all articles needing rescoring in the article index.

    See the module docstring for more info on why article rescoring is
    necesary.

    Updates the article index database and its first page cache to reflect the
    new quality scores of the rescored articles.
    """
    current_rescore_datetime = datetime.utcnow()
    with ArticleIndexDb(DataAccessMode.READ_UPDATE) as db:
        base_form_article_key_map = _rescore_article_index_database(db)
        _update_first_page_cache(base_form_article_key_map)
        _update_last_rescore_datetime(db, current_rescore_datetime)


def _rescore_article_index_database(
    db: ArticleIndexDb
) -> DefaultDict[str, List[ArticleRankKey]]:
    """Rescore and update articles needing rescoring in the index database.

    Unlike rescore_article_index, only updates the article quality score data
    in the article index database and does not update the first page cache.

    Args:
        db: Article index database connection to use to make the article score
            updates.

    Returns:
        A mapping from each of the found lexcial item base forms in the article
        index that were found in at least one rescored article to a list of the
        rank keys of all of the rescored articles that contain that found
        lexical item.
    """
    _log.info('Beginning article rescoring...')
    base_form_article_key_map: DefaultDict[str, List[ArticleRankKey]] = (
        defaultdict(list)
    )
    total_count = 0
    update_count = 0
    scorer = MyakuArticleScorer()
    for i, article in enumerate(_get_articles_needing_rescoring(db)):
        total_count += 1
        if i % 100 == 0:
            _log.info(f'Rescored {i:,} articles')

        scorer.score_article(article)
        update_made = _update_article_score_in_database(db, article)
        if update_made:
            update_count += 1

        for fli in _get_flis_for_article(db, article):
            base_form_article_key_map[fli.base_form].append(
                article.get_rank_key(fli.quality_score_mod)
            )

    _log.info(
        f'{total_count:,} articles were rescored with {update_count:,} having '
        f'their quality score updated'
    )
    return base_form_article_key_map


@utils.add_debug_logging
def _query_articles(
    db: ArticleIndexDb, query: Document
) -> Iterator[JpnArticle]:
    """Return a generator for all articles matching the query in the index."""
    _log.debug(
        'Will query %s with query:\n%s',
        db.article_collection.full_name, pformat(query)
    )
    cursor = db.article_collection.find(query, no_cursor_timeout=True)
    cursor.sort('blog_oid')
    _log.debug(
        'Retrieved cursor from %s', db.article_collection.full_name
    )

    with closing(cursor) as context_cursor:
        oid_blog_map: Dict[ObjectId, JpnArticleBlog] = None
        last_blog_oid = None
        for article_doc in context_cursor:
            if article_doc['blog_oid'] is None:
                oid_blog_map = {}
            elif article_doc['blog_oid'] != last_blog_oid:
                blog_doc = db.blog_collection.find_one(
                    {'_id': article_doc['blog_oid']}
                )
                oid_blog_map = convert_docs_to_blogs([blog_doc])

            article_oid_map = convert_docs_to_articles(
                [article_doc], oid_blog_map
            )
            yield article_oid_map[article_doc['_id']]


@utils.add_debug_logging
def _get_articles_needing_rescoring(
    db: ArticleIndexDb
) -> Iterator[JpnArticle]:
    """Get all articles in the article index that need rescoring.

    Determines which articles need rescoring by looking at which articles have
    a last updated datetime that moved from one recency tier to another since
    the last time rescoring was done.
    """
    query: Document = {}
    rescore_tracking_doc = db.rescore_tracking_collection.find_one({})
    if rescore_tracking_doc is not None:
        current_rescore_datetime = datetime.utcnow()
        last_rescore_datetime = rescore_tracking_doc['last_rescore_datetime']
        rescore_time_delta = current_rescore_datetime - last_rescore_datetime

        query['$or'] = []
        recency_range_day_boundaries = (
            PublicationRecencyScorer.RECENCY_RANGE_MULTIPLIERS
            .get_range_boundary_values()
        )
        for day_count in recency_range_day_boundaries:
            query['$or'].append(
                {'$and': [
                    {'last_updated_datetime': {
                        '$gte': (
                            current_rescore_datetime
                            - timedelta(days=day_count)
                            - rescore_time_delta
                        )
                    }},
                    {'last_updated_datetime': {
                        '$lte': (
                            current_rescore_datetime
                            - timedelta(days=day_count)
                        )
                    }},
                ]}
            )

    yield from _query_articles(db, query)


def _get_flis_for_article(
    db: ArticleIndexDb, article: JpnArticle
) -> Iterator[FoundJpnLexicalItem]:
    """Get all found lexical items in the index for an article."""
    article_oid = ObjectId(article.database_id)
    cursor = db.found_lexical_item_collection.find(
        {'article_oid': article_oid}
    )
    article_oid_map = {article_oid: article}
    for fli_doc in cursor:
        fli_list = convert_docs_to_found_lexical_items(
            [fli_doc], article_oid_map
        )
        yield fli_list[0]


def _get_fli_score_recalculate_pipeline(
        article_quality_score: int
) -> List[Document]:
    """Get a pipeline to recalculate found lexical item quality scores.

    Args:
        article_quality_score: New article quality score to use to
            recalculate the found lexical items scores in the pipeline.

    Returns:
        Pipeline that can be used in an update operation to recalculate
        found lexical item quality scores using the given article quality
        score.
    """
    return [
        {'$set': {
            'article_quality_score': article_quality_score,
            'quality_score_exact': {
                '$add': [
                    article_quality_score,
                    '$quality_score_exact_mod'
                ]
            },
            'quality_score_definite': {
                '$add': [
                    article_quality_score,
                    '$quality_score_definite_mod'
                ]
            },
            'quality_score_possible': {
                '$add': [
                    article_quality_score,
                    '$quality_score_possible_mod'
                ]
            },
        }},
    ]


@utils.add_debug_logging
def _update_article_score_in_database(
    db: ArticleIndexDb, article: JpnArticle
) -> bool:
    """Update the quality score for the article in the index database.

    Updates the quality score for the article and found lexical items for
    the article in the index db to match the data stored in quality_score field
    of the given article object.

    The given article must have its database_id field set.

    Args:
        db: Article index database connection to use to make the updates.
        article: The article whose quality score to update in the db.

    Returns:
        True if the article data in the index db needed to be modified to make
        the quality score update, or False if no modification was necessary
        because the article data in the index db already matched the given
        article data.
    """
    result = db.article_collection.update_one(
        {'_id': ObjectId(article.database_id)},
        {'$set': {'quality_score': article.quality_score}}
    )
    _log.debug(
        'Updated the quality score for the article with _id "%s" to '
        '%s', article.database_id, article.quality_score
    )
    if result.modified_count == 0:
        return False

    _log.debug(
        'Will recalculate the quality scores for the found lexical items '
        'for the article with _id "%s" using updated article quality '
        'score %s', article.database_id, article.quality_score
    )
    result = db.found_lexical_item_collection.update_many(
        {'article_oid': ObjectId(article.database_id)},
        _get_fli_score_recalculate_pipeline(article.quality_score)
    )
    _log.debug('Update result: %s', result.raw_result)

    return True


# Debug level logging can be extremely noisy (can be over 1gb) when enabled
# during this function, so switch to info level if logging.
@utils.set_package_log_level(logging.INFO)
def _update_first_page_cache(
    base_form_article_key_map: Dict[str, List[ArticleRankKey]]
) -> None:
    """Update the first page cache to reflect the rescored articles.

    Args:
        base_form_article_key_map: A mapping from found lexical item base forms
            to the updated article rank keys for the articles that were
            rescored that contained that found lexical item.
        db: Article index database connection to use to make the updates.
    """
    first_page_cache = FirstPageCache()
    success_count = 0
    unnecessary_count = 0
    recache_count = 0

    _log.info('Beginning first page cache update...')
    key_map = base_form_article_key_map
    with ArticleIndexSearcher() as searcher:
        for i, (base_form, article_rank_keys) in enumerate(key_map.items()):
            if i % 1000 == 0:
                _log.info(f'Updated {i:,} / {len(key_map):,} keys')

            update_result = first_page_cache.update(
                Query(base_form, 1), article_rank_keys
            )
            if update_result == CacheUpdateResult.SUCCESSFUL:
                success_count += 1
            elif update_result == CacheUpdateResult.UNNECESSARY:
                unnecessary_count += 1
            elif update_result == CacheUpdateResult.RECACHE_REQUIRED:
                search_result_page = searcher.search_articles_using_db(
                    Query(base_form, 1)
                )
                first_page_cache.set(search_result_page)
                recache_count += 1

    _log.info(
        f'Completed first page cache update with {success_count:,} '
        f'SUCCESSFUL, {unnecessary_count:,} UNNECESSARY, and '
        f'{recache_count:,} RECACHE_REQUIRED'
    )


@utils.add_debug_logging
def _update_last_rescore_datetime(
    db: ArticleIndexDb, rescore_datetime: datetime
) -> None:
    """Update the last rescore datetime stored in the database."""
    _log.info(
        'Updating last rescore datetime in db to %s...', rescore_datetime
    )
    result = db.rescore_tracking_collection.update_one(
        {}, {'$set': {'last_rescore_datetime': rescore_datetime}}, upsert=True
    )
    _log.info('Update result: %s', result.raw_result)
