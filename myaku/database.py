"""Handles CRUD operations for the Myaku database.

The public members of this module are defined generically so that the
implementation of the article index can be changed freely while keeping the
access interface consistent.
"""

import enum
import functools
import logging
import re
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass
from operator import methodcaller
from typing import Any, Callable, Dict, Iterator, List, TypeVar, Union

import pymongo
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection, ReturnDocument
from pymongo.cursor import Cursor
from pymongo.errors import DuplicateKeyError
from pymongo.results import InsertManyResult

import myaku
import myaku.utils as utils
from myaku.datatypes import (FoundJpnLexicalItem, InterpSource, JpnArticle,
                             JpnArticleBlog, JpnArticleMetadata,
                             JpnLexicalItemInterp, LexicalItemTextPosition,
                             MecabLexicalItemInterp)
from myaku.errors import NoDbWritePermissionError

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
    """Copies all Myaku data from one MyakuCrawlDb to another.

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
            src, dest, MyakuCrawlDb._BLOG_COLL_NAME
        )
        article_new_id_map = _copy_db_collection_data(
            src, dest, MyakuCrawlDb._ARTICLE_COLL_NAME,
            {'blog_oid': blog_new_id_map}
        )
        _copy_db_collection_data(
            src, dest, MyakuCrawlDb._FOUND_LEXICAL_ITEM_COLL_NAME,
            {'article_oid': article_new_id_map}
        )
        _copy_db_collection_data(
            src, dest, MyakuCrawlDb._CRAWLED_COLL_NAME
        )


def _copy_db_collection_data(
    src_client: MongoClient, dest_client: MongoClient, collection_name: str,
    new_foreign_key_maps: Dict[str, Dict[ObjectId, ObjectId]] = None
) -> Dict[ObjectId, ObjectId]:
    """Copies all docs in a collection in one MyakuCrawlDb instance to another.

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
    skipped = 0
    src_coll = src_client[MyakuCrawlDb._DB_NAME][collection_name]
    dest_coll = dest_client[MyakuCrawlDb._DB_NAME][collection_name]
    for i, doc in enumerate(src_coll.find({})):
        if i % 1000 == 0:
            _log.info('Skipped %s, copied %s documents', skipped, i - skipped)

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


def _require_write_permission(func: Callable) -> Callable:
    """Checks that the db object instance is not read-only before running func.

    Can only be used to wrap db class methods for a db class with a read_only
    member variable.

    Raises:
        NoDbWritePermissionError: If the db object is read-only.
    """
    @functools.wraps(func)
    def wrapper_require_write_permission(*args, **kwargs):
        if args[0].read_only:
            utils.log_and_raise(
                _log, NoDbWritePermissionError,
                'Write operation "{}" was attempted with a read-only database '
                'connection'.format(utils.get_full_name(func))
            )

        value = func(*args, **kwargs)
        return value
    return wrapper_require_write_permission


@enum.unique
class JpnArticleQueryType(enum.Enum):
    """Match type for a found lexical item query on an article corpus.

    Attributes:
        EXACT: Only match articles containing a term whose base form matches
            the query exactly.

            For example, searching for "落ち込む" will not match
            "落ちこむ" because they do not match exactly even though they are
            definte alternate forms of the same lexical item.
        DEFINITE_ALT_FORMS: In addition to articles matched by EXACT,
            also match articles containing any term whose base form
            is a definite alternate form of a lexical item that has a form that
            exactly matches the query.

            For example, searching for "落ち込む" will also match
            "落ちこむ" because they are definite alternate forms of the same
            lexical item, but searching for "変える" will not match
            "かえる" even though "かえる" is an alternate form of it because it
            is not a definite alternate form.
            This is because "かえる" is also an alternate form for words like
            "帰る" which are completely different lexical items that do not
            have the searched "変える" as an alternate form.

        POSSIBLE_ALT_FORMS: In addition to the articles matched by
            DEFNITE_ALT_FORMS, also match articles containing any term whose
            base form is an alternate form of a lexical item that has a form
            that exactly matches the query, even if that base form is also an
            alternate form of other lexical items that do not have a form that
            exactly matches the query.

            For example, searching for "変える" will also match "かえる"
            because "かえる" is an alternate form of it even though "かえる" is
            also an alternate form for "帰る" which is a completely different
            lexical item that does not have the searched "変える" as an
            alternate form.

    """
    EXACT = 1
    DEFINITE_ALT_FORMS = 3
    POSSIBLE_ALT_FORMS = 2


@dataclass
class JpnArticleSearchResult(object):
    """Article result of a database search for found lexical items.

    Attributes:
        article: Article matching the found lexical item search query.
        matched_base_forms: Lexical item base forms that matched the search
            query that were found in the article.
        found_positions: Positions of the found lexical items in the article
            that matched the search query.
        quality_score: Quality score of this search result. See the scorers
            module for more info on how quality scoring is done.
    """
    article: JpnArticle
    matched_base_forms: List[str]
    found_positions: List[LexicalItemTextPosition]
    quality_score: int


@utils.add_method_debug_logging
class MyakuCrawlDb(object):
    """Interface object for accessing the Myaku database.

    This database stores mappings from Japanese lexical items to native
    Japanese web articles that use those lexical items. This allows for easy
    look up of native Japanese articles that make use of a particular lexical
    item of interest.

    Implements the Myaku database using MongoDB.
    """
    _DB_NAME = 'myaku'
    _ARTICLE_COLL_NAME = 'articles'
    _BLOG_COLL_NAME = 'blogs'
    _FOUND_LEXICAL_ITEM_COLL_NAME = 'found_lexical_items'

    # Stores only metadata for previous crawled articles. Used to keep track of
    # which articles have been crawled before so that crawlers don't try to
    # crawl them again even after the article is deleted from the articles
    # collection.
    _CRAWLED_COLL_NAME = 'crawled'

    # The match stage at the start of the aggergate is necessary in order to
    # get a covered query that only scans the index for base_form.
    _BASE_FORM_COUNT_LIMIT = 1000
    _EXCESS_BASE_FORM_AGGREGATE = [
        {'$match': {'base_form': {'$gt': ''}}},
        {'$group': {'_id': '$base_form', 'total': {'$sum': 1}}},
        {'$match': {'total': {'$gt': _BASE_FORM_COUNT_LIMIT}}},
    ]

    # If attempting to recalculate the composite quality scores for found
    # lexical items for more than this percentage of the total articles in the
    # database, it is faster to simply do a recalculate query on the whole
    # found lexical item collection instead.
    _RECALCULATE_ALL_FLI_SCORES_THRESHOLD_PERCENT = 0.5

    _FLI_QUALITY_SCORE_RECALCULATE_AGGREGATE = [
        {'$set': {
            'quality_score_exact': {
                '$add': [
                    '$article_quality_score',
                    '$quality_score_exact_mod'
                ]
            },
            'quality_score_definite': {
                '$add': [
                    '$article_quality_score',
                    '$quality_score_definite_mod'
                ]
            },
            'quality_score_possible': {
                '$add': [
                    '$article_quality_score',
                    '$quality_score_possible_mod'
                ]
            },
        }},
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

    def __init__(self, read_only: bool = False) -> None:
        """Initializes the connection to the database."""
        self._mongo_client = self._init_mongo_client()

        self._db = self._mongo_client[self._DB_NAME]
        self._article_collection = self._db[self._ARTICLE_COLL_NAME]
        self._blog_collection = self._db[self._BLOG_COLL_NAME]
        self._crawled_collection = self._db[self._CRAWLED_COLL_NAME]
        self._found_lexical_item_collection = (
            self._db[self._FOUND_LEXICAL_ITEM_COLL_NAME]
        )

        self.read_only = read_only
        if not read_only:
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

    def _create_indexes(self) -> None:
        """Creates the necessary indexes for the db if they don't exist."""
        self._article_collection.create_index('text_hash')
        self._article_collection.create_index('blog_oid')
        self._found_lexical_item_collection.create_index('article_oid')

        for q_type in JpnArticleQueryType:
            self._found_lexical_item_collection.create_index([
                (self._QUERY_TYPE_QUERY_FIELD_MAP[q_type], pymongo.DESCENDING),
                (self._QUERY_TYPE_SCORE_FIELD_MAP[q_type], pymongo.DESCENDING),
                ('article_last_updated_datetime', pymongo.DESCENDING),
                ('article_oid', pymongo.DESCENDING),
            ])

        crawled_id_index = []
        for field in JpnArticleMetadata.ID_FIELDS:
            crawled_id_index.append((field, pymongo.ASCENDING))
        self._crawled_collection.create_index(crawled_id_index)

        blog_id_index = []
        for field in JpnArticleBlog.ID_FIELDS:
            blog_id_index.append((field, pymongo.ASCENDING))
        self._blog_collection.create_index(blog_id_index)

    def is_article_stored(self, article: JpnArticle) -> bool:
        """Returns True if article is stored in the db, False otherwise."""
        docs = self._read_with_log(
            'text_hash', article.text_hash, self._article_collection,
            {'text_hash': 1, '_id': 0}
        )
        return len(docs) > 0

    def filter_to_unstored_articles(
        self, articles: List[JpnArticle]
    ) -> List[JpnArticle]:
        """Returns new list with the articles not currently stored in the db.

        Does not modify the given articles list.

        Args:
            articles: A list of articles to check for in the database.

        Returns:
            The articles from the given list that are not currently stored in
            the database. Preserves ordering used in the given list.
        """
        article_hashes = [a.text_hash for a in articles]

        # Since there is an index on text_hash and this query queries and
        # returns only the text_hash field, it will be a covered query
        # (i.e. it's fast!)
        stored_docs = self._read_with_log(
            'text_hash', article_hashes, self._article_collection,
            {'text_hash': 1, '_id': 0}
        )

        unstored_articles = self._filter_to_unstored(
            articles, stored_docs, ['text_hash']
        )
        return unstored_articles

    @utils.skip_method_debug_logging
    def _create_id_query(self, obj: Any) -> _Document:
        """Creates docs to query for obj and project its id fields.

        Args:
            obj: Object being queried for. It must define an ID_FIELDS list
                with the field names that can be used to uniquely identify an
                object of its type.

        Returns:
            (query doc, projection doc)
        """
        query_doc = {}
        proj_doc = {'_id': 0}
        for field in obj.ID_FIELDS:
            query_doc[field] = getattr(obj, field)
            proj_doc[field] = 1
        return (query_doc, proj_doc)

    def filter_to_uncrawled_article_metadatas(
        self, metadatas: List[JpnArticleMetadata]
    ) -> List[JpnArticleMetadata]:
        """Returns new list with the metadatas for the uncrawled articles."""
        unstored_metadatas = []
        for metadata in metadatas:
            query, proj = self._create_id_query(metadata)
            if self._crawled_collection.find_one(query, proj) is None:
                unstored_metadatas.append(metadata)

        _log.debug(
            'Filtered to %s unstored article metadatas',
            len(unstored_metadatas)
        )
        return unstored_metadatas

    def filter_to_updated_blogs(
        self, blogs: List[JpnArticleBlog]
    ) -> List[JpnArticleBlog]:
        """Returns new list with the blogs updated since last crawled.

        The new list includes blogs that have never been crawled as well.
        """
        updated_blogs = []
        unstored_count = 0
        partial_stored_count = 0
        updated_count = 0
        for blog in blogs:
            query, proj = self._create_id_query(blog)
            proj['last_crawled_datetime'] = 1
            doc = self._blog_collection.find_one(query, proj)

            if doc is None:
                unstored_count += 1
                updated_blogs.append(blog)
            elif doc['last_crawled_datetime'] is None:
                partial_stored_count += 1
                updated_blogs.append(blog)
            elif blog.last_updated_datetime > doc['last_crawled_datetime']:
                updated_count += 1
                updated_blogs.append(blog)

        _log.debug(
            'Filtered to %s unstored, %s partially stored, and %s updated '
            'blogs', unstored_count, partial_stored_count, updated_count
        )
        return updated_blogs

    def update_blog_last_crawled(self, blog: JpnArticleBlog) -> None:
        """Updates the last crawled datetime of the blog in the db."""
        query, proj = self._create_id_query(blog)

        _log.debug(
            'Updating the last crawled datetime in collection "%s" for blog '
            '"%s"', self._blog_collection.full_name, blog
        )
        result = self._blog_collection.update_one(
            query,
            {
                '$set': {
                    'last_crawled_datetime': blog.last_crawled_datetime
                }
            }
        )
        _log.debug('Update result: %s', result.raw_result)

    def _get_fli_articles(
            self, flis: List[FoundJpnLexicalItem]
    ) -> List[JpnArticle]:
        """Gets the unique articles referenced by the found lexical items."""
        # Many found lexical items can point to the same article object in
        # memory, so dedupe using id() to get each article object only once.
        article_id_map = {
            id(item.article): item.article for item in flis
        }
        return list(article_id_map.values())

    def _get_article_blogs(
            self, articles: List[JpnArticle]
    ) -> List[JpnArticleBlog]:
        """Gets the unique blogs referenced by the articles."""
        articles_with_blog = [
            a for a in articles if a.metadata and a.metadata.blog
        ]

        # Many found lexical items can point to the same blog object in
        # memory, so dedupe using id() to get each blog object only once.
        blog_id_map = {
            id(a.metadata.blog): a.metadata.blog for a in articles_with_blog
        }
        return list(blog_id_map.values())

    @_require_write_permission
    def write_found_lexical_items(
            self, found_lexical_items: List[FoundJpnLexicalItem],
            write_articles: bool = True
    ) -> None:
        """Writes the found lexical items to the database.

        Args:
            found_lexical_items: List of found lexical items to write to the
                database.
            write_articles: If True, will write all of the articles referenced
                by the given found lexical items to the database as well. If
                False, will assume the articles referenced by the the given
                found lexical items are already in the database.
        """
        articles = self._get_fli_articles(found_lexical_items)
        if write_articles:
            article_oid_map = self._write_articles(articles)
        else:
            article_oid_map = self._read_article_oids(articles)

        found_lexical_item_docs = self._convert_found_lexical_items_to_docs(
            found_lexical_items, article_oid_map
        )
        self._write_with_log(
            found_lexical_item_docs, self._found_lexical_item_collection
        )

    @utils.skip_method_debug_logging
    @_require_write_permission
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
        _log.debug(
            'Will update the quality score for the article with _id "%s" to '
            '%s', article.database_id, article.quality_score
        )
        result = self._article_collection.update_one(
            {'_id': ObjectId(article.database_id)},
            {'$set': {'quality_score': article.quality_score}}
        )
        _log.debug('Update result: %s', result.raw_result)
        if result.modified_count == 0:
            return False

        _log.debug(
            'Will update the quality score for the found lexical items for '
            'the article with _id "%s" to %s',
            article.database_id, article.quality_score
        )
        result = self._found_lexical_item_collection.update_many(
            {'article_oid': ObjectId(article.database_id)},
            {'$set': {'article_quality_score': article.quality_score}}
        )
        _log.debug('Update result: %s', result.raw_result)

        return True

    def recalculate_found_lexical_item_scores(
        self, changed_article_ids: List[str]
    ) -> None:
        """Recalculates quality scores for found lexical items in the db.

        Args:
            changed_article_ids: Ids of the articles whose found lexical items
                need their composite quality scores recalculated.
        """
        changed_article_percent = (
            len(changed_article_ids) / self.get_article_count()
        )
        if (changed_article_percent >
                self._RECALCULATE_ALL_FLI_SCORES_THRESHOLD_PERCENT):
            _log.debug(
                'Attempting to recalculate the found lexical item composite '
                'quality scores for {} percent of articles, so the scores for '
                'all found lexical items will be recalculated instead.'.format(
                    changed_article_percent
                )
            )
            query_doc = {}
        else:
            _log.debug(
                'Will recalculate the found lexical item composite quality '
                'scores for {} articles'.format(len(changed_article_ids))
            )
            article_oids = [ObjectId(id_str) for id_str in changed_article_ids]
            query_doc = {'article_oid': {'$in': article_oids}}

        result = self._found_lexical_item_collection.update_many(
            query_doc, self._FLI_QUALITY_SCORE_RECALCULATE_AGGREGATE
        )
        _log.debug('Update result: %s', result.raw_result)

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

    def search_articles(
        self, query: str, query_type: JpnArticleQueryType,
        results_start_index: int, max_results_to_return: int
    ) -> List[JpnArticleSearchResult]:
        """Searchs the db for articles that match the given lexical item query.

        The search results are in ranked order by quality score. See the scorer
        module for more info on how quality scores are determined.

        Args:
            query_value: Lexical item base form value to use to search for
                articles.
            query_type: Type of matching to use when searching for articles
                whose text contains terms matching query_value.
            results_start_index: Index of the search results that the returned
                results should start from. Indexing start from 0.
            max_results_to_return: Max number of search results that the
                returned generator should yield. If the generator reaches the
                last overall search result before reaching this max, it will
                also stop yielding.

        Returns:
            A list of article search results that match the found lexical item
            query starting from index results_start_index of the results with a
            max of max_results_to_return results in the list.
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
            cursor, quality_score_field, results_start_index,
            max_results_to_return
        )

        article_oids = [doc['article_oid'] for doc in search_result_docs]
        oid_article_map = self._read_articles(article_oids)

        search_results = self._convert_docs_to_search_results(
            search_result_docs, oid_article_map
        )
        return search_results

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
            blog_docs, self._blog_collection, JpnArticleBlog.ID_FIELDS
        )
        blog_oid_map = {
            id(b): oid for b, oid in zip(blogs, object_ids)
        }

        return blog_oid_map

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
        text_hashes = [a.text_hash for a in articles]
        docs = self._read_with_log(
            'text_hash', text_hashes, self._article_collection,
            {'text_hash': 1}
        )
        hash_oid_map = {d['text_hash']: d['_id'] for d in docs}
        article_oid_map = {
            id(a): hash_oid_map[a.text_hash] for a in articles
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

        blog_oids = list(set(doc['blog_oid'] for doc in article_docs))
        blog_docs = self._read_with_log(
            '_id', blog_oids, self._blog_collection
        )
        oid_blog_map = self._convert_docs_to_blogs(blog_docs)

        oid_article_map = self._convert_docs_to_articles(
            article_docs, oid_blog_map
        )
        return oid_article_map

    @_require_write_permission
    def write_crawled(self, metadatas: List[JpnArticleMetadata]) -> None:
        """Writes the article metadata to the crawled database."""
        metadata_docs = self._convert_article_metadata_to_docs(metadatas)
        self._write_with_log(metadata_docs, self._crawled_collection)

    @_require_write_permission
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

    @_require_write_permission
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
        self._mongo_client.close()

    def __enter__(self) -> 'MyakuCrawlDb':
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

    def _replace_write_with_log(
        self, docs: List[_Document], collection: Collection,
        id_fields: List[str]
    ) -> List[ObjectId]:
        """Writes or replaces with docs with logging.

        If a doc exists in the collection, replaces it with the given doc, and
        if a doc does not exists in the collection, writes it to the
        collection.

        Args:
            docs: Documents to write or replace with.
            collection: Collection to perform writes and replaces on.
            id_fields: List of fields from the docs that can be used together
                to uniquely id a doc in the collection.

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
            filter_doc = {}
            for field in id_fields:
                filter_doc[field] = doc[field]

            replacement_doc = collection.find_one_and_replace(
                filter_doc, doc, upsert=True,
                return_document=ReturnDocument.AFTER
            )
            object_ids.append(replacement_doc['_id'])

        _log.debug(
            'Wrote replaced %s documents to "%s" collection',
            len(object_ids), collection.full_name
        )
        return object_ids

    def _convert_article_metadata_to_docs(
        self, metadatas: List[JpnArticleMetadata]
    ) -> List[_Document]:
        """Converts article metadata to dicts for inserting into MongoDB."""
        docs = []
        for metadata in metadatas:
            docs.append({
                'title': metadata.title,
                'author': metadata.author,
                'source_url': metadata.source_url,
                'source_name': metadata.source_name,
                'blog_id': metadata.blog_id,
                'blog_article_order_num': metadata.blog_article_order_num,
                'blog_section_name': metadata.blog_section_name,
                'blog_section_order_num': metadata.blog_section_order_num,
                'blog_section_article_order_num':
                    metadata.blog_section_article_order_num,
                'publication_datetime': metadata.publication_datetime,
                'last_updated_datetime': metadata.last_updated_datetime,
                'last_crawled_datetime': metadata.last_crawled_datetime,
                'myaku_version_info': self._version_doc,
            })

        return docs

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
                'start_datetime': blog.start_datetime,
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

    def _convert_articles_to_docs(
        self, articles: List[JpnArticle], blog_oid_map: Dict[int, ObjectId]
    ) -> List[_Document]:
        """Converts articles to dicts for inserting into MongoDB."""
        docs = []
        for article in articles:
            docs.append({
                'full_text': article.full_text,
                'title': article.metadata.title,
                'author': article.metadata.author,
                'source_url': article.metadata.source_url,
                'source_name': article.metadata.source_name,
                'blog_oid': blog_oid_map.get(id(article.metadata.blog)),
                'blog_article_order_num':
                    article.metadata.blog_article_order_num,
                'blog_section_name': article.metadata.blog_section_name,
                'blog_section_order_num':
                    article.metadata.blog_section_order_num,
                'blog_section_article_order_num':
                    article.metadata.blog_section_article_order_num,
                'publication_datetime': article.metadata.publication_datetime,
                'last_updated_datetime':
                    article.metadata.last_updated_datetime,
                'last_crawled_datetime':
                    article.metadata.last_crawled_datetime,
                'text_hash': article.text_hash,
                'alnum_count': article.alnum_count,
                'has_video': article.has_video,
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
        self, found_positions: List[LexicalItemTextPosition]
    ) -> List[_Document]:
        """Converts found positions to dicts for inserting into MongoDB."""
        docs = []
        for found_position in found_positions:
            docs.append({
                'index': found_position.index,
                'len': found_position.len
            })

        return docs

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
                    fli.article.metadata.last_updated_datetime,
                'quality_score_exact': quality_score,
                'quality_score_definite': quality_score,
                'quality_score_possible': quality_score,
                'myaku_version_info': self._version_doc,
            })

        return docs

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
                start_datetime=doc['start_datetime'],
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
                full_text=doc['full_text'],
                alnum_count=doc['alnum_count'],
                has_video=doc['has_video'],
                database_id=str(doc['_id']),
                quality_score=doc['quality_score'],
                metadata=JpnArticleMetadata(
                    title=doc['title'],
                    author=doc.get('author'),
                    source_url=doc['source_url'],
                    source_name=doc['source_name'],
                    blog=oid_blog_map.get(doc.get('blog_oid')),
                    blog_article_order_num=doc.get('blog_article_order_num'),
                    blog_section_name=doc.get('blog_section_name'),
                    blog_section_order_num=doc.get('blog_section_order_num'),
                    blog_section_article_order_num=doc.get(
                        'blog_section_article_order_num'
                    ),
                    publication_datetime=doc['publication_datetime'],
                    last_updated_datetime=doc.get('last_updated_datetime'),
                    last_crawled_datetime=doc['last_crawled_datetime'],
                ),
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
    ) -> List[LexicalItemTextPosition]:
        """Converts MongoDB docs to found positions."""
        found_positions = []
        for doc in docs:
            found_positions.append(LexicalItemTextPosition(
                index=doc['index'],
                len=doc['len'],
            ))

        return found_positions

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
