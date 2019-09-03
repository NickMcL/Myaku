"""Driver for the Myaku crawl and search index database.

Currently implemented using MongoDB, but the public members of this module are
defined generically so that the implementation of the database can be changed
freely while keeping the access interface consistent.
"""

import logging
import re
from collections import defaultdict
from contextlib import closing
from operator import methodcaller
from typing import Any, Dict, Iterator, List, Optional, TypeVar, Union

import pymongo
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection, ReturnDocument
from pymongo.cursor import Cursor
from pymongo.errors import DuplicateKeyError
from pymongo.results import InsertManyResult

import myaku
from myaku import utils
from myaku.datastore import (DataAccessMode, JpnArticleQueryType,
                             JpnArticleSearchResult, require_update_permission,
                             require_write_permission)
from myaku.datastore.cache import FirstPageCache
from myaku.datatypes import (ArticleTextPosition, Crawlable,
                             FoundJpnLexicalItem, InterpSource, JpnArticle,
                             JpnArticleBlog, JpnLexicalItemInterp,
                             MecabLexicalItemInterp)

_log = logging.getLogger(__name__)

T = TypeVar('T')
_Document = Dict[str, Any]

_DB_HOST_ENV_VAR = 'MYAKU_CRAWLDB_HOST'
_DB_PORT = 27017

_DB_USERNAME_FILE_ENV_VAR = 'MYAKU_CRAWLDB_USERNAME_FILE'
_DB_PASSWORD_FILE_ENV_VAR = 'MYAKU_CRAWLDB_PASSWORD_FILE'


def copy_db_data(
    src_host: str, src_username: str, src_password: str,
    dest_host: str, dest_username: str, dest_password: str
) -> None:
    """Copies all Myaku data from one CrawlDb to another.

    The source database data must not change during the duration of the copy.

    The given username and password should be for the root user for each
    database.
    """
    src_client = MongoClient(
        host=src_host, port=_DB_PORT, username=src_username,
        password=src_password
    )
    dest_client = MongoClient(
        host=dest_host, port=_DB_PORT, username=dest_username,
        password=dest_password
    )

    with closing(src_client) as src, closing(dest_client) as dest:
        blog_new_id_map = _copy_db_collection_data(
            src, dest, CrawlDb._BLOG_COLL_NAME
        )
        article_new_id_map = _copy_db_collection_data(
            src, dest, CrawlDb._ARTICLE_COLL_NAME,
            {'blog_oid': blog_new_id_map}
        )
        _copy_db_collection_data(
            src, dest, CrawlDb._FOUND_LEXICAL_ITEM_COLL_NAME,
            {'article_oid': article_new_id_map}
        )


def _copy_db_collection_data(
    src_client: MongoClient, dest_client: MongoClient, collection_name: str,
    new_foreign_key_maps: Dict[str, Dict[ObjectId, ObjectId]] = None
) -> Dict[ObjectId, ObjectId]:
    """Copies all docs in a collection in one CrawlDb instance to another.

    Args:
        src_client: MongoClient connected to the source db.
        dest_client: MongoClient connected to the destination db.
        collection_name: Name of the collection whose docs should be copied
            from the source db to the destination db.
        new_foreign_key_maps: Dictionary mapping foreign key field names to a
            dictionary that maps a value of that field in the source collection
            to the replacement value that should be used instead of that value
            in the destination collection.

            These replacement values are used to avoid _id collisions in the
            destination collection.

    Returns:
        A dictionary mapping any _id changes that had to be made when a doc was
        copied from the source db to the destination db in order to avoid
        collisions in the destination collection.
    """
    _log.info(
        'Copying "%s" collection documents from "%s" to "%s"',
        collection_name, src_client.address[0], dest_client.address[0]
    )
    if new_foreign_key_maps is None:
        new_foreign_key_maps = {}

    new_id_map = {}
    src_coll = src_client[CrawlDb._DB_NAME][collection_name]
    dest_coll = dest_client[CrawlDb._DB_NAME][collection_name]
    total_docs = src_coll.count_documents({})
    skipped = 0
    for i, doc in enumerate(src_coll.find({})):
        if i % 1000 == 0:
            _log.info(
                'Processed %s / %s documents (%s copied, %s skipped)',
                i, total_docs, i - skipped, skipped
            )

        for (field, new_foreign_key_map) in new_foreign_key_maps.items():
            if doc[field] in new_foreign_key_map:
                doc[field] = new_foreign_key_map[doc[field]]

        # Don't copy documents that are already in the destination.
        if dest_coll.find_one(doc) is not None:
            skipped += 1
            continue

        try:
            dest_coll.insert_one(doc)
        except DuplicateKeyError:
            old_id = doc.pop('_id')
            result = dest_coll.insert_one(doc)
            new_id_map[old_id] = result.inserted_id
            _log.info('_id collision: %s -> %s', old_id, result.inserted_id)

    return new_id_map


@utils.add_method_debug_logging
class CrawlDb(object):
    """Interface object for accessing the Myaku database.

    This database stores mappings from Japanese lexical items to native
    Japanese web articles that use those lexical items. This allows for easy
    look up of native Japanese articles that make use of a particular lexical
    item of interest.

    Implements the Myaku database using MongoDB.
    """
    MAX_ALLOWED_ARTICLE_LEN = 2**16  # 65,536
    SEARCH_RESULTS_PAGE_SIZE = 20

    _DB_NAME = 'myaku'
    _ARTICLE_COLL_NAME = 'articles'
    _BLOG_COLL_NAME = 'blogs'
    _FOUND_LEXICAL_ITEM_COLL_NAME = 'found_lexical_items'

    # The match stage at the start of the aggergate is necessary in order to
    # get a covered query that only scans the index for base_form.
    _BASE_FORM_COUNT_LIMIT = 1000
    _EXCESS_BASE_FORM_AGGREGATE = [
        {'$match': {'base_form': {'$gt': ''}}},
        {'$group': {'_id': '$base_form', 'total': {'$sum': 1}}},
        {'$match': {'total': {'$gt': _BASE_FORM_COUNT_LIMIT}}},
    ]

    _QUERY_TYPE_QUERY_FIELD_MAP = {
        JpnArticleQueryType.EXACT: 'base_form',
        JpnArticleQueryType.DEFINITE_ALT_FORMS: 'base_form_definite_group',
        JpnArticleQueryType.POSSIBLE_ALT_FORMS: 'base_form_possible_group',
    }

    _QUERY_TYPE_SCORE_FIELD_MAP = {
        JpnArticleQueryType.EXACT: 'quality_score_exact',
        JpnArticleQueryType.DEFINITE_ALT_FORMS: 'quality_score_definite',
        JpnArticleQueryType.POSSIBLE_ALT_FORMS: 'quality_score_possible',
    }

    def __init__(
        self, access_mode: DataAccessMode = DataAccessMode.READ,
        update_first_page_cache_on_exit: bool = False
    ) -> None:
        """Initializes the connection to the database.

        Args:
            access_mode: Data access mode to use for this db session. If an
                operation is attempted that requires permissions not granted by
                the set access mode, a DataAccessPermissionError will be
                raised.
            update_first_page_cache_on_exit: If True, on session close, will
                automatically update the search results first page cache with
                any changes made to the db during the database session. If
                False, will not update the first page cache at all.
        """
        self._mongo_client = self._init_mongo_client()

        self._db = self._mongo_client[self._DB_NAME]
        self._article_collection = self._db[self._ARTICLE_COLL_NAME]
        self._blog_collection = self._db[self._BLOG_COLL_NAME]
        self._found_lexical_item_collection = (
            self._db[self._FOUND_LEXICAL_ITEM_COLL_NAME]
        )

        self._first_page_cache = FirstPageCache()
        self._update_first_page_cache_on_exit = update_first_page_cache_on_exit

        self._crawlable_coll_map = {
            JpnArticle: self._article_collection,
            JpnArticleBlog: self._blog_collection,
        }

        self.access_mode = access_mode
        self._written_fli_base_forms = set()
        if access_mode.has_write_permission():
            self._create_indexes()
            self._version_doc = myaku.get_version_info()

    def _init_mongo_client(self) -> MongoClient:
        """Initializes and returns the client for connecting to the database.

        Returns:
            A client object connected and authenticated with the database.

        Raises:
            EnvironmentNotSetError: if a needed value from the environment to
                init the client is not set in the environment.
        """
        username = utils.get_value_from_env_file(_DB_USERNAME_FILE_ENV_VAR)
        password = utils.get_value_from_env_file(_DB_PASSWORD_FILE_ENV_VAR)
        hostname = utils.get_value_from_env_variable(_DB_HOST_ENV_VAR)

        mongo_client = MongoClient(
            host=hostname, port=_DB_PORT,
            username=username, password=password, authSource=self._DB_NAME
        )
        _log.debug(
            'Connected to MongoDB at %s:%s as user %s',
            mongo_client.address[0], mongo_client.address[1], username
        )

        return mongo_client

    @require_write_permission
    def _create_indexes(self) -> None:
        """Creates the necessary indexes for the db if they don't exist."""
        self._article_collection.create_index('text_hash')
        self._article_collection.create_index('blog_oid')
        self._found_lexical_item_collection.create_index('article_oid')

        for crawlable_collection in self._crawlable_coll_map.values():
            crawlable_collection.create_index([
                ('source_url', pymongo.ASCENDING),
                ('last_crawled_datetime', pymongo.ASCENDING),
            ])

        for query_type in JpnArticleQueryType:
            query_field = self._QUERY_TYPE_QUERY_FIELD_MAP[query_type]
            score_field = self._QUERY_TYPE_SCORE_FIELD_MAP[query_type]
            self._found_lexical_item_collection.create_index(
                [
                    (query_field, pymongo.DESCENDING),
                    (score_field, pymongo.DESCENDING),
                    ('article_last_updated_datetime', pymongo.DESCENDING),
                    ('article_oid', pymongo.DESCENDING),
                ],
                name=query_field + '_search'
            )

    def is_article_text_stored(self, article: JpnArticle) -> bool:
        """Returns True if an article with the same text is already stored."""
        docs = self._read_with_log(
            'text_hash', article.text_hash, self._article_collection,
            {'text_hash': 1, '_id': 0}
        )
        return len(docs) > 0

    def can_store_article(self, article: JpnArticle) -> bool:
        """Returns True if the article is safe to store in the db.

        Checks that:
            1. The article is not too long
            2. There is not an article with the exact same text already stored
                in the db.
        """
        if self.is_article_text_stored(article):
            _log.info('Article %s already stored!', article)
            return False

        if len(article.full_text) > self.MAX_ALLOWED_ARTICLE_LEN:
            _log.info(
                'Article %s is too long to store (%s chars)',
                article, len(article.full_text)
            )
            return False

        return True

    @utils.skip_method_debug_logging
    def filter_crawlable_to_updated(
        self, crawlable_items: List[Crawlable]
    ) -> List[Crawlable]:
        """Returns new list with the items updated since last crawled.

        The new list includes items that have never been crawled as well.
        """
        if len(crawlable_items) == 0:
            return []

        cursor = self._crawlable_coll_map[type(crawlable_items[0])].find(
            {'source_url': {'$in': [i.source_url for i in crawlable_items]}},
            {'_id': -1, 'source_url': 1, 'last_crawled_datetime': 1}
        )
        last_crawled_map = {
            d['source_url']: d['last_crawled_datetime'] for d in cursor
        }

        updated_items = []
        unstored_count = 0
        partial_stored_count = 0
        updated_count = 0
        for item in crawlable_items:
            item_url = item.source_url
            if item_url not in last_crawled_map:
                unstored_count += 1
                updated_items.append(item)
            elif last_crawled_map[item_url] is None:
                partial_stored_count += 1
                updated_items.append(item)
            elif (item.last_updated_datetime is not None
                  and item.last_updated_datetime > last_crawled_map[item_url]):
                updated_count += 1
                updated_items.append(item)

        _log.debug(
            'Filtered to %s unstored, %s partially stored, and %s updated '
            'crawlable items of type %s',
            unstored_count, partial_stored_count, updated_count,
            type(crawlable_items[0])
        )
        return updated_items

    @utils.skip_method_debug_logging
    @require_update_permission
    def update_last_crawled(self, item: Crawlable) -> None:
        """Updates the last crawled datetime of the item in the db."""
        _log.debug(
            'Updating the last crawled datetime for item "%s" of type %s',
            item, type(item)
        )
        result = self._crawlable_coll_map[type(item)].update_one(
            {'source_url': item.source_url},
            {'$set': {'last_crawled_datetime': item.last_crawled_datetime}}
        )
        _log.debug('Update result: %s', result.raw_result)

    def _get_fli_safe_articles(
            self, flis: List[FoundJpnLexicalItem]
    ) -> List[JpnArticle]:
        """Gets the unique articles referenced by the found lexical items.

        Does NOT include any articles in the returned list that cannot be
        safely stored in the db.
        """
        # Many found lexical items can point to the same article object in
        # memory, so dedupe using id() to get each article object only once.
        article_id_map = {
            id(item.article): item.article for item in flis
        }

        articles = list(article_id_map.values())
        return [a for a in articles if self.can_store_article(a)]

    def _get_article_blogs(
            self, articles: List[JpnArticle]
    ) -> List[JpnArticleBlog]:
        """Gets the unique blogs referenced by the articles."""
        articles_with_blog = [a for a in articles if a.blog]

        # Many found lexical items can point to the same blog object in
        # memory, so dedupe using id() to get each blog object only once.
        blog_id_map = {id(a.blog): a.blog for a in articles_with_blog}
        return list(blog_id_map.values())

    @require_write_permission
    def write_found_lexical_items(
            self, found_lexical_items: List[FoundJpnLexicalItem],
            write_articles: bool = True
    ) -> bool:
        """Writes the found lexical items to the database.

        Args:
            found_lexical_items: List of found lexical items to write to the
                database.
            write_articles: If True, will write all of the articles referenced
                by the given found lexical items to the database as well. If
                False, will assume the articles referenced by the the given
                found lexical items are already in the database.

        Returns:
            True if all of the given found lexical items were written to the
            db, or False if some or all of the given found lexical items were
            not written to the db because their articles were not safe to
            store.
            See the myaku info log for the reasons why any articles were
            considered unsafe.
        """
        safe_articles = self._get_fli_safe_articles(found_lexical_items)
        if write_articles:
            safe_article_oid_map = self._write_articles(safe_articles)
        else:
            safe_article_oid_map = self._read_article_oids(safe_articles)

        # Don't write found lexical items to the db unless their article is
        # safe to store.
        safe_article_flis = []
        for fli in found_lexical_items:
            if id(fli.article) in safe_article_oid_map:
                safe_article_flis.append(fli)

        found_lexical_item_docs = self._convert_found_lexical_items_to_docs(
            safe_article_flis, safe_article_oid_map
        )
        self._write_with_log(
            found_lexical_item_docs, self._found_lexical_item_collection
        )
        self._written_fli_base_forms |= {
            fli.base_form for fli in safe_article_flis
        }

        return len(safe_article_flis) == len(found_lexical_items)

    def _get_fli_score_recalculate_pipeline(
            self, article_quality_score: int
    ) -> List[_Document]:
        """Gets a pipeline to recalculate found lexical item quality scores.

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

    @utils.skip_method_debug_logging
    @require_update_permission
    def update_article_score(self, article: JpnArticle) -> bool:
        """Updates the quality score for the article in the db.

        Updates the quality score for the article and found lexical items for
        the article in the db to match the data stored in quality_score field
        of the given article object.

        The given article must have its database_id field set.

        Args:
            article: The article whose quality score to update in the db.

        Returns:
            True if the quality score was changed for the article in the db.
            False if the quality score for the article in the db was already
            the same as the given one, so no update was necessary.
        """
        result = self._article_collection.update_one(
            {'_id': ObjectId(article.database_id)},
            {'$set': {'quality_score': article.quality_score}}
        )
        if result.modified_count == 0:
            return False
        _log.debug(
            'Updated the quality score for the article with _id "%s" to '
            '%s', article.database_id, article.quality_score
        )

        _log.debug(
            'Will recalculate the quality scores for the found lexical items '
            'for the article with _id "%s" using updated article quality '
            'score %s', article.database_id, article.quality_score
        )
        result = self._found_lexical_item_collection.update_many(
            {'article_oid': ObjectId(article.database_id)},
            self._get_fli_score_recalculate_pipeline(article.quality_score)
        )
        _log.debug('Update result: %s', result.raw_result)

        cursor = self._found_lexical_item_collection.find(
            {'article_oid': ObjectId(article.database_id)}, {'base_form': 1}
        )
        self._written_fli_base_forms |= {d['base_form'] for d in cursor}

        return True

    # Debug level logging is extremely noisy (can be over 1gb) when enabled
    # during this function, so switch to info level if logging.
    @utils.set_package_log_level(logging.INFO)
    def build_search_result_cache(self) -> None:
        """Builds the full first page cache using current db data."""
        # Count all unique base forms currently in the db
        cursor = self._found_lexical_item_collection.aggregate([
            {'$match': {'base_form': {'$gt': ''}}},
            {'$group': {'_id': '$base_form'}},
            {'$count': 'total'}
        ])
        base_form_total = next(cursor)['total']
        _log.info(
            f'Will build the first page cache for all {base_form_total:,} '
            f'base forms currently in db'
        )

        cursor = self._found_lexical_item_collection.aggregate([
            {'$match': {'base_form': {'$gt': ''}}},
            {'$group': {'_id': '$base_form'}}
        ])
        for i, doc in enumerate(cursor):
            base_form = doc['_id']
            search_results = self._search_articles_using_db(
                base_form, JpnArticleQueryType.EXACT, 1
            )
            self._first_page_cache.set(base_form, search_results)

            if (i + 1) % 1000 == 0 or (i + 1) == base_form_total:
                _log.info(
                    f'Cached first page count: {i + 1:,} / {base_form_total:,}'
                )

        self._first_page_cache.set_built_marker()
        _log.info('First page cache built successfully')

    # Debug level logging is extremely noisy (can be over 1gb) when enabled
    # during this function, so switch to info level if logging.
    @utils.set_package_log_level(logging.INFO)
    def update_first_page_cache(self) -> None:
        """Updates the first page cache with changes from this db session.

        Updates the search result first page cache entries related to all of
        the found lexical items written to the db since either the last time
        this function was called or the start of this client session.
        """
        if not self._first_page_cache.is_built():
            _log.info(
                'First page cache has not been built yet, so will build '
                'the full the cache'
            )
            self.build_first_page_cache()
            self._written_fli_base_forms = set()
            return

        update_total = len(self._written_fli_base_forms)
        _log.info(
            f'Will update the first page cache for {update_total:,} '
            f'queries'
        )
        for i, base_form in enumerate(self._written_fli_base_forms):
            search_results = self._search_articles_using_db(
                base_form, JpnArticleQueryType.EXACT, 1
            )
            self._first_page_cache.set(base_form, search_results)

            if (i + 1) % 1000 == 0 or (i + 1) == update_total:
                _log.info(f'Updated count: {i + 1:,} / {update_total:,}')

        self._written_fli_base_forms = set()
        _log.info('First page cache update complete')

    def _get_article_docs_from_search_results(
        self, search_results_cursor: Cursor, quality_score_field: str,
        results_start_index: int, max_results_to_return: int
    ) -> List[_Document]:
        """Merges the top search result docs together to get one per article.

        Args:
            search_results_cursor: Cursor that will yield search result
                docs in ranked order.
            quality_score_field: Name of field in the docs yielded from the
                search_results_cursor that has the quality score for the search
                result.
            results_start_index: Index of the search results to start getting
                article docs from. Indexing starts at 0.
            max_results_to_return: Max number of search result article docs to
                get. If the cursor reaches the last search result before
                reaching this max, will return all of the search result article
                docs that could be got.

        Returns:
            A list of ranked search results docs with only one per article.
        """
        article_search_result_docs = []
        last_article_oid = None
        skipped_articles = 0
        for doc in search_results_cursor:
            if doc['article_oid'] != last_article_oid:
                last_article_oid = doc['article_oid']
                if skipped_articles != results_start_index:
                    skipped_articles += 1
                    continue

                if len(article_search_result_docs) == max_results_to_return:
                    break

                article_search_result_docs.append({
                    'article_oid': doc['article_oid'],
                    'matched_base_forms': [doc['base_form']],
                    'found_positions': doc['found_positions'],
                    'quality_score': doc[quality_score_field],
                })
            elif skipped_articles == results_start_index:
                article_search_result_docs[-1]['matched_base_forms'].append(
                    doc['base_form']
                )
                article_search_result_docs[-1]['found_positions'].extend(
                    doc['found_positions']
                )

        return article_search_result_docs

    @utils.skip_method_debug_logging
    def _search_articles_using_cache(
        self, query: str
    ) -> Optional[List[JpnArticleSearchResult]]:
        """Searches for articles that match the query using only the cache.

        Does not use the db in any case, even if the cache contains no search
        results for the query.

        The search results are in ranked order by quality score. See the scorer
        module for more info on how quality scores are determined.

        Args:
            query_value: Lexical item base form value to use to search for
                articles.

        Returns:
            A list containing a page of article search results that match the
            lexical item query if there was results in the cache, or None if
            nothing was stored in the search results cache for the query.
        """
        _log.debug('Checking first page cache for query "%s"', query)
        cached_results = self._first_page_cache.get(query)
        if cached_results:
            _log.debug(
                'Query "%s" results retrieved from first page cache', query
            )
            return cached_results

        _log.debug('Query "%s" not found in first page cache', query)
        return None

    @utils.skip_method_debug_logging
    def _search_articles_using_db(
        self, query: str, query_type: JpnArticleQueryType, page: int = 1
    ) -> List[JpnArticleSearchResult]:
        """Searches for articles that match the query using only the db.

        Does not use the search result cache in any case.

        The search results are in ranked order by quality score. See the scorer
        module for more info on how quality scores are determined.

        Args:
            query_value: Lexical item base form value to use to search for
                articles.
            query_type: Type of matching to use when searching for articles
                whose text contains terms matching query_value.
            page: Page of the search results to return. Page indexing starts
                from 1.

        Returns:
            A list containing a page of article search results that match the
            lexical item query.
        """
        query_field = self._QUERY_TYPE_QUERY_FIELD_MAP[query_type]
        quality_score_field = self._QUERY_TYPE_SCORE_FIELD_MAP[query_type]

        cursor = self._found_lexical_item_collection.find({query_field: query})
        cursor.sort([
            (quality_score_field, pymongo.DESCENDING),
            ('article_last_updated_datetime', pymongo.DESCENDING),
            ('article_oid', pymongo.DESCENDING),
        ])
        search_result_docs = self._get_article_docs_from_search_results(
            cursor, quality_score_field,
            (page - 1) * self.SEARCH_RESULTS_PAGE_SIZE,
            page * self.SEARCH_RESULTS_PAGE_SIZE
        )

        article_oids = [doc['article_oid'] for doc in search_result_docs]
        oid_article_map = self._read_articles(article_oids)

        search_results = self._convert_docs_to_search_results(
            search_result_docs, oid_article_map
        )
        return search_results

    def search_articles(
        self, query: str, query_type: JpnArticleQueryType, page: int = 1
    ) -> List[JpnArticleSearchResult]:
        """Searches the db for articles that match the lexical item query.

        The search results are in ranked order by quality score. See the scorer
        module for more info on how quality scores are determined.

        Args:
            query_value: Lexical item base form value to use to search for
                articles.
            query_type: Type of matching to use when searching for articles
                whose text contains terms matching query_value.
            page: Page of the search results to return. Page indexing starts
                from 1.

        Returns:
            A list containing a page of article search results that match the
            lexical item query.
        """
        if page == 1:
            cached_results = self._search_articles_using_cache(query)
            if cached_results:
                return cached_results

        return self._search_articles_using_db(query, query_type, page)

    def read_found_lexical_items(
        self, base_forms: Union[str, List[str]], starts_with: bool = False
    ) -> List[FoundJpnLexicalItem]:
        """Reads found lexical items that match base form from the database.

        Args:
            base_forms: Either one or a list of base forms of Japanese lexical
                items to search for matching found lexical items in the db.
            starts_with: If True, will return all found lexical items with a
                possible interpretation base form that starts with one of the
                given base forms. If False, will return all found lexical items
                with a possible interpretation base form that exactly matches
                one of the given base forms.

        Returns:
            A list of found lexical items with at least on possible
            interpretation that matches at least one of the base forms given.
        """
        if not isinstance(base_forms, list):
            base_forms = [base_forms]

        if starts_with:
            base_forms = [re.compile('^' + s) for s in base_forms]

        found_lexical_item_docs = self._read_with_log(
            'base_form', base_forms, self._found_lexical_item_collection
        )
        article_oids = list(
            set(doc['article_oid'] for doc in found_lexical_item_docs)
        )
        oid_article_map = self._read_articles(article_oids)

        found_lexical_items = self._convert_docs_to_found_lexical_items(
            found_lexical_item_docs, oid_article_map
        )
        return found_lexical_items

    def get_article_count(self) -> int:
        """Returns the total number of articles in the db."""
        return self._article_collection.count_documents({})

    def read_all_articles(self) -> Iterator[JpnArticle]:
        """Returns generator that yields all articles from the database."""
        _log.debug(
            'Will query %s for all documents',
            self._article_collection.full_name
        )
        cursor = self._article_collection.find({}).sort('blog_oid')
        _log.debug(
            'Retrieved cursor from %s', self._article_collection.full_name
        )

        oid_blog_map = None
        last_blog_oid = None
        for doc in cursor:
            if doc['blog_oid'] is None:
                oid_blog_map = {}
            elif doc['blog_oid'] != last_blog_oid:
                blog_doc = self._blog_collection.find_one(
                    {'_id': doc['blog_oid']}
                )
                oid_blog_map = self._convert_docs_to_blogs([blog_doc])

            article_oid_map = self._convert_docs_to_articles(
                [doc], oid_blog_map
            )
            yield article_oid_map[doc['_id']]

    @require_write_permission
    def _write_blogs(
        self, blogs: JpnArticleBlog
    ) -> Dict[int, ObjectId]:
        """Writes the blogs to the database.

        Args:
            blogs: Blogs to write to the database.

        Returns:
            A mapping from the id() for each given blog to the ObjectId that
            blog was written with.
        """
        blog_docs = self._convert_blogs_to_docs(blogs)
        object_ids = self._replace_write_with_log(
            blog_docs, self._blog_collection, 'source_url'
        )
        blog_oid_map = {
            id(b): oid for b, oid in zip(blogs, object_ids)
        }

        return blog_oid_map

    @require_write_permission
    def _write_articles(
        self, articles: JpnArticle
    ) -> Dict[int, ObjectId]:
        """Writes the articles to the database.

        Args:
            articles: Articles to write to the database.

        Returns:
            A mapping from the id() for each given article to the ObjectId that
            article was written with.
        """
        blogs = self._get_article_blogs(articles)
        blog_oid_map = self._write_blogs(blogs)

        article_docs = self._convert_articles_to_docs(articles, blog_oid_map)
        result = self._write_with_log(article_docs, self._article_collection)
        article_oid_map = {
            id(a): oid for a, oid in zip(articles, result.inserted_ids)
        }
        return article_oid_map

    def _read_article_oids(
        self, articles: List[JpnArticle]
    ) -> Dict[int, ObjectId]:
        """Reads the ObjectIds for the articles from the database.

        Args:
            articles: Articles to read from the database.

        Returns:
            A mapping from the id() for each given article to the ObjectId that
            article is stored with.
        """
        source_urls = [a.source_url for a in articles]
        docs = self._read_with_log(
            'source_url', source_urls, self._article_collection,
            {'source_url': 1}
        )
        source_url_oid_map = {d['source_url']: d['_id'] for d in docs}
        article_oid_map = {
            id(a): source_url_oid_map[a.source_url] for a in articles
        }

        return article_oid_map

    def _read_articles(
        self, object_ids: List[ObjectId]
    ) -> Dict[ObjectId, JpnArticle]:
        """Reads the articles for the given ObjectIds from the database.

        Args:
            object_ids: ObjectIds for articles to read from the database.

        Returns:
            A mapping from the given ObjectIds to the article stored in the
            database for that ObjectId.
        """
        article_docs = self._read_with_log(
            '_id', object_ids, self._article_collection
        )

        blog_oids = list(
            set(doc['blog_oid'] for doc in article_docs if doc['blog_oid'])
        )
        if len(blog_oids) > 0:
            blog_docs = self._read_with_log(
                '_id', blog_oids, self._blog_collection
            )
            oid_blog_map = self._convert_docs_to_blogs(blog_docs)
        else:
            oid_blog_map = {}

        oid_article_map = self._convert_docs_to_articles(
            article_docs, oid_blog_map
        )
        return oid_article_map

    @require_write_permission
    def delete_article_found_lexical_items(self, article: JpnArticle) -> None:
        """Deletes found lexical items from article from the database."""
        _log.debug(
            'Will delete found lexical items for "%s" article from "%s"',
            article, self._found_lexical_item_collection.full_name
        )
        result = self._found_lexical_item_collection.delete_many(
            {'article_oid': ObjectId(article.database_id)}
        )
        _log.debug(
            'Deleted %s found lexical items from "%s"',
            result.deleted_count, self._found_lexical_item_collection.full_name
        )

    @require_write_permission
    def delete_base_form_excess(self) -> None:
        """Deletes found lexical items with base forms in excess in the db.

        A base form is considered in excess if over a certain limit
        (_BASE_FORM_COUNT_LIMIT) of found lexical items with the base form are
        in the database.

        This function:
            1. Finds all base forms in excess in the database.
            2. Ranks all of the found lexical items for each from highest to
                lowest quality of usage of that base form.
            3. Deletes all found lexical items for each with quality rank not
                within _BASE_FORM_COUNT_LIMIT.
        """
        excess_base_forms = self._get_base_forms_in_excess()
        excess_flis = self.read_found_lexical_items(
            excess_base_forms
        )
        base_form_fli_map = self._make_base_form_mapping(excess_flis)

        for base_form in excess_base_forms:
            base_form_flis = base_form_fli_map[base_form]
            self._delete_low_quality(base_form_flis)

        self._delete_articles_with_no_found_lexical_items()

    def _get_base_forms_in_excess(self) -> List[str]:
        """Queries db to get base forms currently in excess.

        See delete_base_form_excess docstring for info on how base forms in
        excess is defined.

        Returns:
            A list of all of the base forms that are currently in excess in the
            database.
        """
        _log.debug(
            'Running aggregate to get excess base forms from %s',
            self._found_lexical_item_collection.full_name
        )
        cursor = self._found_lexical_item_collection.aggregate(
            self._EXCESS_BASE_FORM_AGGREGATE
        )
        docs = list(cursor)
        _log.debug(
            'Aggregate returns %s excess base forms from %s',
            len(docs), self._found_lexical_item_collection.full_name
        )

        return [d['_id'] for d in docs]

    def _make_base_form_mapping(
        self, found_lexical_items: List[FoundJpnLexicalItem]
    ) -> Dict[str, FoundJpnLexicalItem]:
        """Returns mapping from base forms to the given found lexical items.

        Returns:
            A dictionary where the keys are base form strings and the values
            are a list with the found lexical items from the given list with
            that base form.
        """
        base_form_map = defaultdict(list)
        for item in found_lexical_items:
            base_form_map[item.base_form].append(item)

        return base_form_map

    @require_write_permission
    def _delete_low_quality(
        self, excess_flis: List[FoundJpnLexicalItem]
    ) -> None:
        """Deletes found lexical items from the db if they are too low quality.

        See FoundJpnLexicalItem quality key for info on how low quality is
        determined.

        Modifies the order of the given found lexical item list.

        Args:
            excess_flis: A list of found lexical items whose base form is
                currently in excess in the db.
            base_form_ranks: A mapping from each of the given found lexical
                items to the quality rank for that item.
        """
        base_form = excess_flis[0].base_form
        _log.debug('Sorting "%s" found lexical items by quality', base_form)
        excess_flis.sort(key=methodcaller('quality_key'), reverse=True)
        _log.debug('Sort of "%s" found lexical items finished', base_form)

        low_quality_item_oids = []
        for fli in excess_flis[self._BASE_FORM_COUNT_LIMIT:]:
            low_quality_item_oids.append(ObjectId(fli.database_id))
        _log.debug(
            'Deleting %s found lexical items from "%s" for "%s" with too low '
            'quality',
            len(low_quality_item_oids),
            self._found_lexical_item_collection.full_name, base_form
        )
        result = self._found_lexical_item_collection.delete_many(
            {'_id': {'$in': low_quality_item_oids}}
        )
        _log.debug(
            'Successfully deleted %s found lexical items from "%s" for "%s"',
            result.deleted_count,
            self._found_lexical_item_collection.full_name, base_form
        )

    @require_write_permission
    def _delete_articles_with_no_found_lexical_items(self) -> None:
        """Deletes articles with no stored found lexical items from the db.

        Curently, only simulated deletion without actually deleting anything.
        """
        _log.debug(
            'Reading all article IDs referenced by stored found lexical items'
        )
        cursor = self._found_lexical_item_collection.aggregate([
            {'$group': {'_id': '$article_oid'}}
        ])
        article_ids = [doc['_id'] for doc in cursor]
        _log.debug(
            'Retrieved %s article IDs from %s',
            len(article_ids), self._found_lexical_item_collection.full_name
        )

        _log.debug(
            'Deleting articles from %s not referenced by any stored found '
            'lexical items', self._article_collection.full_name
        )
        result = self._article_collection.find(
            {'_id': {'$nin': article_ids}}, {'_id': 1}
        )
        _log.debug(
            'Simulated deletion of %s articles from %s',
            len(list(result)), self._article_collection.full_name
        )

    def close(self) -> None:
        """Closes the connection to the database."""
        try:
            if self._update_first_page_cache_on_exit:
                self.update_first_page_cache()
        finally:
            self._mongo_client.close()

    def __enter__(self) -> 'CrawlDb':
        """Initializes the connection to the database."""
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Closes the connection to the database."""
        self.close()

    def _read_with_log(
        self, lookup_field_name: str, lookup_values: Union[Any, List[Any]],
        collection: Collection, projection: _Document = None
    ) -> List[_Document]:
        """Reads docs from collection with before and after logging.

        Args:
            lookup_field_name: The field to query on. Should be an indexed
                field to ensure high performance.
            lookup_values: The values for the lookup field to query for. Can be
                a single value or a list of values.
            collection: The collection to query.
            projection: The projection to use for the query. No projection will
                be used if None.

        Returns:
            Retreives all documents from the cursor for the query and returns
            them in a list.
        """
        if not isinstance(lookup_values, list):
            lookup_values = [lookup_values]

        _log.debug(
            'Will query %s with %s %s',
            collection.full_name, len(lookup_values), lookup_field_name
        )
        cursor = collection.find(
            {lookup_field_name: {'$in': lookup_values}}, projection
        )
        docs = list(cursor)
        _log.debug(
            'Retrieved %s documents from %s', len(docs), collection.full_name
        )

        return docs

    @require_write_permission
    def _write_with_log(
        self, docs: List[_Document], collection: Collection
    ) -> InsertManyResult:
        """Writes docs to collection with logging."""
        _log.debug(
            'Will write %s documents to "%s" collection',
            len(docs), collection.full_name
        )
        result = collection.insert_many(docs)
        _log.debug(
            'Wrote %s documents to "%s" collection',
            len(result.inserted_ids), collection.full_name
        )

        return result

    @require_write_permission
    def _replace_write_with_log(
        self, docs: List[_Document], collection: Collection, id_field: str
    ) -> List[ObjectId]:
        """Writes or replaces with docs with logging.

        If a doc exists in the collection, replaces it with the given doc, and
        if a doc does not exists in the collection, writes it to the
        collection.

        Args:
            docs: Documents to write or replace with.
            collection: Collection to perform writes and replaces on.
            id_field: Field from the doc that can be used to uniquely id a doc
                in the collection.

        Returns:
            The list of the ObjectIds stored for the given docs. The ObjectId
            list is in the order of the given docs list.
        """
        _log.debug(
            'Will write replace %s documents to "%s" collection',
            len(docs), collection.full_name
        )

        object_ids = []
        for doc in docs:
            replacement_doc = collection.find_one_and_replace(
                {id_field: doc[id_field]}, doc, upsert=True,
                return_document=ReturnDocument.AFTER
            )
            object_ids.append(replacement_doc['_id'])

        _log.debug(
            'Wrote replaced %s documents to "%s" collection',
            len(object_ids), collection.full_name
        )
        return object_ids

    @utils.skip_method_debug_logging
    def _convert_blogs_to_docs(
        self, blogs: List[JpnArticleBlog]
    ) -> List[_Document]:
        """Converts blogs to dicts for inserting into MongoDB."""
        docs = []
        for blog in blogs:
            docs.append({
                'title': blog.title,
                'author': blog.author,
                'source_name': blog.source_name,
                'source_url': blog.source_url,
                'publication_datetime': blog.publication_datetime,
                'last_updated_datetime': blog.last_updated_datetime,
                'rating': blog.rating,
                'rating_count': blog.rating_count,
                'tags': blog.tags,
                'catchphrase': blog.catchphrase,
                'introduction': blog.introduction,
                'article_count': blog.article_count,
                'total_char_count': blog.total_char_count,
                'comment_count': blog.comment_count,
                'follower_count': blog.follower_count,
                'in_serialization': blog.in_serialization,
                'last_crawled_datetime': blog.last_crawled_datetime,
                'myaku_version_info': self._version_doc,
            })

        return docs

    @utils.skip_method_debug_logging
    def _convert_articles_to_docs(
        self, articles: List[JpnArticle], blog_oid_map: Dict[int, ObjectId]
    ) -> List[_Document]:
        """Converts articles to dicts for inserting into MongoDB."""
        docs = []
        for article in articles:
            docs.append({
                'full_text': article.full_text,
                'title': article.title,
                'author': article.author,
                'source_url': article.source_url,
                'source_name': article.source_name,
                'blog_oid': blog_oid_map.get(id(article.blog)),
                'blog_article_order_num': article.blog_article_order_num,
                'blog_section_name': article.blog_section_name,
                'blog_section_order_num': article.blog_section_order_num,
                'blog_section_article_order_num':
                    article.blog_section_article_order_num,
                'publication_datetime': article.publication_datetime,
                'last_updated_datetime': article.last_updated_datetime,
                'last_crawled_datetime': article.last_crawled_datetime,
                'text_hash': article.text_hash,
                'alnum_count': article.alnum_count,
                'has_video': article.has_video,
                'tags': article.tags,
                'quality_score': article.quality_score,
                'myaku_version_info': self._version_doc,
            })

        return docs

    @utils.skip_method_debug_logging
    def _convert_mecab_interp_to_doc(
        self, mecab_interp: MecabLexicalItemInterp
    ) -> _Document:
        """Converts MeCab interp to a dict for inserting into MongoDB."""
        doc = {
            'parts_of_speech': mecab_interp.parts_of_speech,
            'conjugated_type': mecab_interp.conjugated_type,
            'conjugated_form': mecab_interp.conjugated_form,
        }

        return doc

    @utils.skip_method_debug_logging
    def _convert_lexical_item_interps_to_docs(
        self, interps: List[JpnLexicalItemInterp]
    ) -> List[_Document]:
        """Converts interps to dicts for inserting into MongoDB."""
        docs = []
        for interp in interps:
            interp_sources = [s.value for s in interp.interp_sources]
            if interp.mecab_interp is None:
                mecab_interp_doc = None
            else:
                mecab_interp_doc = self._convert_mecab_interp_to_doc(
                    interp.mecab_interp
                )

            docs.append({
                'interp_sources': interp_sources,
                'mecab_interp': mecab_interp_doc,
                'jmdict_interp_entry_id': interp.jmdict_interp_entry_id,
            })

        return docs

    @utils.skip_method_debug_logging
    def _convert_found_positions_to_docs(
        self, found_positions: List[ArticleTextPosition]
    ) -> List[_Document]:
        """Converts found positions to dicts for inserting into MongoDB."""
        docs = []
        for found_position in found_positions:
            docs.append({
                'index': found_position.index,
                'len': found_position.len
            })

        return docs

    @utils.skip_method_debug_logging
    def _convert_interp_pos_map_to_doc(
        self, fli: FoundJpnLexicalItem
    ) -> _Document:
        """Converts a found lexical item interp position map to a doc."""
        interp_pos_map_doc = {}
        for i, interp in enumerate(fli.possible_interps):
            if interp not in fli.interp_position_map:
                continue

            interp_pos_docs = self._convert_found_positions_to_docs(
                fli.interp_position_map[interp]
            )
            interp_pos_map_doc[str(i)] = interp_pos_docs

        if len(interp_pos_map_doc) == 0:
            interp_pos_map_doc = None

        return interp_pos_map_doc

    @utils.skip_method_debug_logging
    def _convert_found_lexical_items_to_docs(
        self, found_lexical_items: List[FoundJpnLexicalItem],
        article_oid_map: Dict[int, ObjectId]
    ) -> List[_Document]:
        """Converts found lexical items to dicts for inserting into MongoDB.

        The given article to ObjectId map must contain all of the articles for
        the given found lexical items.
        """
        docs = []
        for fli in found_lexical_items:
            interp_docs = self._convert_lexical_item_interps_to_docs(
                fli.possible_interps
            )
            found_positions_docs = self._convert_found_positions_to_docs(
                fli.found_positions
            )
            interp_pos_map_doc = self._convert_interp_pos_map_to_doc(fli)

            quality_score = fli.article.quality_score + fli.quality_score_mod
            docs.append({
                'base_form': fli.base_form,
                'base_form_definite_group': fli.base_form,
                'base_form_possible_group': fli.base_form,
                'article_oid': article_oid_map[id(fli.article)],
                'found_positions': found_positions_docs,
                'found_positions_exact_count': len(found_positions_docs),
                'found_positions_definite_count': len(found_positions_docs),
                'found_positions_possible_count': len(found_positions_docs),
                'possible_interps': interp_docs,
                'interp_position_map': interp_pos_map_doc,
                'quality_score_exact_mod': fli.quality_score_mod,
                'quality_score_definite_mod': fli.quality_score_mod,
                'quality_score_possible_mod': fli.quality_score_mod,
                'article_quality_score': fli.article.quality_score,
                'article_last_updated_datetime':
                    fli.article.last_updated_datetime,
                'quality_score_exact': quality_score,
                'quality_score_definite': quality_score,
                'quality_score_possible': quality_score,
                'myaku_version_info': self._version_doc,
            })

        return docs

    @utils.skip_method_debug_logging
    def _convert_docs_to_blogs(
        self, docs: List[_Document]
    ) -> Dict[ObjectId, JpnArticleBlog]:
        """Converts MongoDB docs to blog objects.

        Returns:
            A mapping from each blog document's ObjectId to the created
            blog object for that blog document.
        """
        oid_blog_map = {}
        for doc in docs:
            oid_blog_map[doc['_id']] = JpnArticleBlog(
                title=doc['title'],
                author=doc['author'],
                source_name=doc['source_name'],
                source_url=doc['source_url'],
                publication_datetime=doc['publication_datetime'],
                last_updated_datetime=doc['last_updated_datetime'],
                rating=doc['rating'],
                rating_count=doc['rating_count'],
                tags=doc['tags'],
                catchphrase=doc.get('catchphrase'),
                introduction=doc.get('introduction'),
                article_count=doc['article_count'],
                total_char_count=doc['total_char_count'],
                comment_count=doc['comment_count'],
                follower_count=doc['follower_count'],
                in_serialization=doc['in_serialization'],
                last_crawled_datetime=doc.get('last_crawled_datetime'),
            )

        return oid_blog_map

    @utils.skip_method_debug_logging
    def _convert_docs_to_articles(
        self, docs: List[_Document],
        oid_blog_map: Dict[ObjectId, JpnArticleBlog]
    ) -> Dict[ObjectId, JpnArticle]:
        """Converts MongoDB docs to article objects.

        Returns:
            A mapping from each article document's ObjectId to the created
            article object for that article document.
        """
        oid_article_map = {}
        for doc in docs:
            oid_article_map[doc['_id']] = JpnArticle(
                title=doc['title'],
                author=doc.get('author'),
                source_url=doc['source_url'],
                source_name=doc['source_name'],
                full_text=doc['full_text'],
                alnum_count=doc['alnum_count'],
                has_video=doc['has_video'],
                tags=doc['tags'],
                blog=oid_blog_map.get(doc['blog_oid']),
                blog_article_order_num=doc['blog_article_order_num'],
                blog_section_name=doc['blog_section_name'],
                blog_section_order_num=doc['blog_section_order_num'],
                blog_section_article_order_num=doc[
                    'blog_section_article_order_num'
                ],
                publication_datetime=doc['publication_datetime'],
                last_updated_datetime=doc['last_updated_datetime'],
                last_crawled_datetime=doc['last_crawled_datetime'],
                database_id=str(doc['_id']),
                quality_score=doc['quality_score'],
            )

        return oid_article_map

    @utils.skip_method_debug_logging
    def _convert_doc_to_mecab_interp(
        self, doc: _Document
    ) -> MecabLexicalItemInterp:
        """Converts MongoDB doc to MeCab interp."""
        mecab_interp = MecabLexicalItemInterp(
            parts_of_speech=utils.tuple_or_none(doc['parts_of_speech']),
            conjugated_type=doc['conjugated_type'],
            conjugated_form=doc['conjugated_form'],
        )

        return mecab_interp

    @utils.skip_method_debug_logging
    def _convert_docs_to_lexical_item_interps(
        self, docs: List[_Document]
    ) -> List[JpnLexicalItemInterp]:
        """Converts MongoDB docs to lexical item interps."""
        interps = []
        for doc in docs:
            if doc['interp_sources'] is None:
                interp_sources = None
            else:
                interp_sources = tuple(
                    InterpSource(i) for i in doc['interp_sources']
                )

            if doc['mecab_interp'] is None:
                mecab_interp = None
            else:
                mecab_interp = self._convert_doc_to_mecab_interp(
                    doc['mecab_interp']
                )

            interps.append(JpnLexicalItemInterp(
                interp_sources=interp_sources,
                mecab_interp=mecab_interp,
                jmdict_interp_entry_id=doc['jmdict_interp_entry_id'],
            ))

        return interps

    @utils.skip_method_debug_logging
    def _convert_docs_to_found_positions(
        self, docs: List[_Document]
    ) -> List[ArticleTextPosition]:
        """Converts MongoDB docs to found positions."""
        found_positions = []
        for doc in docs:
            found_positions.append(ArticleTextPosition(
                index=doc['index'],
                len=doc['len'],
            ))

        return found_positions

    @utils.skip_method_debug_logging
    def _convert_docs_to_found_lexical_items(
        self, docs: List[_Document],
        oid_article_map: Dict[ObjectId, JpnArticle]
    ) -> List[FoundJpnLexicalItem]:
        """Converts MongoDB docs to found lexical items.

        The given ObjectId to article map must contain the created article
        objects for all of found lexical item documents.
        """
        found_lexical_items = []
        for doc in docs:
            interps = self._convert_docs_to_lexical_item_interps(
                doc['possible_interps']
            )
            found_positions = self._convert_docs_to_found_positions(
                doc['found_positions']
            )

            if doc['interp_position_map'] is None:
                doc['interp_position_map'] = {}

            interp_position_map = {}
            for i in doc['interp_position_map']:
                interp_positions = self._convert_docs_to_found_positions(
                    doc['interp_position_map'][i]
                )
                interp_position_map[interps[int(i)]] = interp_positions

            found_lexical_items.append(FoundJpnLexicalItem(
                base_form=doc['base_form'],
                article=oid_article_map[doc['article_oid']],
                found_positions=found_positions,
                possible_interps=interps,
                interp_position_map=interp_position_map,
                database_id=str(doc['_id']),
            ))

        return found_lexical_items

    @utils.skip_method_debug_logging
    def _convert_docs_to_search_results(
        self, docs: List[_Document],
        oid_article_map: Dict[ObjectId, JpnArticle]
    ) -> List[FoundJpnLexicalItem]:
        """Converts MongoDB docs to article search results.

        The given ObjectId to article map must contain the created article
        objects for all of the given search result docs.
        """
        search_results = []
        for doc in docs:
            found_positions = self._convert_docs_to_found_positions(
                doc['found_positions']
            )

            search_results.append(JpnArticleSearchResult(
                article=oid_article_map[doc['article_oid']],
                matched_base_forms=doc['matched_base_forms'],
                found_positions=found_positions,
                quality_score=doc['quality_score'],
            ))

        return search_results
