"""Driver for accessing the Myaku search index database."""

import functools
import logging
from contextlib import closing
from typing import Any, Callable, Dict, List, Type, Union

import pymongo
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection, ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError
from pymongo.results import InsertManyResult

from myaku import utils
from myaku.datastore import (
    DataAccessMode,
    Document,
    QueryType,
    require_write_permission,
)
from myaku.datatypes import Crawlable, JpnArticle, JpnArticleBlog

_log = logging.getLogger(__name__)

_DB_HOST_ENV_VAR = 'MYAKU_CRAWLDB_HOST'
_DB_PORT = 27017

_DB_USERNAME_FILE_ENV_VAR = 'MYAKU_CRAWLDB_USERNAME_FILE'
_DB_PASSWORD_FILE_ENV_VAR = 'MYAKU_CRAWLDB_PASSWORD_FILE'


def copy_db_data(
    src_host: str, src_username: str, src_password: str,
    dest_host: str, dest_username: str, dest_password: str
) -> None:
    """Copy all Myaku data from one ArticleIndexDb to another.

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
            src, dest, ArticleIndexDb._BLOG_COLL_NAME
        )
        article_new_id_map = _copy_db_collection_data(
            src, dest, ArticleIndexDb._ARTICLE_COLL_NAME,
            {'blog_oid': blog_new_id_map}
        )
        _copy_db_collection_data(
            src, dest, ArticleIndexDb._FOUND_LEXICAL_ITEM_COLL_NAME,
            {'article_oid': article_new_id_map}
        )


def _copy_db_collection_data(
    src_client: MongoClient, dest_client: MongoClient, collection_name: str,
    new_foreign_key_maps: Dict[str, Dict[ObjectId, ObjectId]] = None
) -> Dict[ObjectId, ObjectId]:
    """Copy all docs in a collection in one ArticleIndexDb instance to another.

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
    src_coll = src_client[ArticleIndexDb._DB_NAME][collection_name]
    dest_coll = dest_client[ArticleIndexDb._DB_NAME][collection_name]
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


def _require_db_connection(func: Callable) -> Callable:
    """Enforce that the database connection is initialized before running func.

    For use inside the ArticleIndexDb class only. Used to put off initializing
    the database connection until right before it is actually needed for an
    operation.
    """
    @functools.wraps(func)
    def wrapper_require_db_connection(*args, **kwargs):
        args[0]._connect_to_db()
        value = func(*args, **kwargs)
        return value
    return wrapper_require_db_connection


@utils.add_method_debug_logging
class ArticleIndexDb(object):
    """Interface object for accessing the Myaku article index database.

    This database stores mappings from Japanese lexical items to native
    Japanese web articles that use those lexical items. This allows for easy
    look up of native Japanese articles that make use of a particular lexical
    item of interest.

    Implements the database using MongoDB.
    """
    _DB_NAME = 'myaku'
    _ARTICLE_COLL_NAME = 'articles'
    _BLOG_COLL_NAME = 'blogs'
    _CRAWL_SKIP_COLL_NAME = 'crawl_skip'
    _FOUND_LEXICAL_ITEM_COLL_NAME = 'found_lexical_items'
    _RESCORE_TRACKING_COLL_NAME = 'rescore_tracking'

    QUERY_TYPE_QUERY_FIELD_MAP = {
        QueryType.EXACT: 'base_form',
        QueryType.DEFINITE_ALT_FORMS: 'base_form_definite_group',
        QueryType.POSSIBLE_ALT_FORMS: 'base_form_possible_group',
    }

    QUERY_TYPE_SCORE_FIELD_MAP = {
        QueryType.EXACT: 'quality_score_exact',
        QueryType.DEFINITE_ALT_FORMS: 'quality_score_definite',
        QueryType.POSSIBLE_ALT_FORMS: 'quality_score_possible',
    }

    @property
    def article_collection(self) -> Collection:
        """Article collection from the aritcle index database."""
        self._connect_to_db()
        return self._article_collection

    @property
    def blog_collection(self) -> Collection:
        """Blog collection from the aritcle index database."""
        self._connect_to_db()
        return self._blog_collection

    @property
    def crawl_skip_collection(self) -> Collection:
        """Crawl skip collection from the aritcle index database."""
        self._connect_to_db()
        return self._crawl_skip_collection

    @property
    def found_lexical_item_collection(self) -> Collection:
        """Found lexical item collection from the aritcle index database."""
        self._connect_to_db()
        return self._found_lexical_item_collection

    @property
    def rescore_tracking_collection(self) -> Collection:
        """Rescore tracking collection from the aritcle index database."""
        self._connect_to_db()
        return self._rescore_tracking_collection

    @property
    def crawlable_coll_map(self) -> Dict[Type[Crawlable], Collection]:
        """Map from Crawlable types to their corresponding collection."""
        self._connect_to_db()
        return self._crawlable_coll_map

    def __init__(
        self, access_mode: DataAccessMode = DataAccessMode.READ
    ) -> None:
        """Set the access mode to be used for this database session.

        The database connection is initialized lazily by the object right
        before an operation is attempted that needs it, so no work to
        initialize the database connection is done in this function.

        Args:
            access_mode: Data access mode to use for this db session. If an
                operation is attempted that requires permissions not granted by
                the set access mode, a DataAccessPermissionError will be
                raised.
        """
        self.access_mode = access_mode

        self._mongo_client: MongoClient = None
        self._db: Database = None
        self._article_collection: Collection = None
        self._blog_collectio: Collection = None
        self._crawl_skip_collectio: Collection = None
        self._found_lexical_item_collectio: Collection = None
        self._rescore_tracking_collectio: Collection = None
        self._crawlable_coll_map: Dict[Type[Crawlable], Collection] = None

    def _connect_to_db(self) -> None:
        """Init the connection to the article index database if necessary.

        Initializes all collection properties for accessing the database
        collections.

        Does nothing if the connection to the database has already been
        initialized.
        """
        if self._mongo_client is not None:
            return

        self._mongo_client = self._init_mongo_client()

        self._db = self._mongo_client[self._DB_NAME]
        self._article_collection = self._db[self._ARTICLE_COLL_NAME]
        self._blog_collection = self._db[self._BLOG_COLL_NAME]
        self._crawl_skip_collection = self._db[self._CRAWL_SKIP_COLL_NAME]
        self._found_lexical_item_collection = (
            self._db[self._FOUND_LEXICAL_ITEM_COLL_NAME]
        )
        self._rescore_tracking_collection = (
            self._db[self._RESCORE_TRACKING_COLL_NAME]
        )

        self._crawlable_coll_map = {
            JpnArticle: self.article_collection,
            JpnArticleBlog: self.blog_collection,
        }

        if self.access_mode.has_write_permission():
            self._create_indexes()

    def _init_mongo_client(self) -> MongoClient:
        """Initialize and return the mongo client for connecting to database.

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
    @_require_db_connection
    def _create_indexes(self) -> None:
        """Create the necessary indexes for the db if they don't exist."""
        self.article_collection.create_index('text_hash')
        self.article_collection.create_index('last_updated_datetime')
        self.article_collection.create_index('blog_oid')
        self.crawl_skip_collection.create_index('source_url')
        self.found_lexical_item_collection.create_index('article_oid')

        for crawlable_collection in self.crawlable_coll_map.values():
            crawlable_collection.create_index([
                ('source_url', pymongo.ASCENDING),
                ('last_crawled_datetime', pymongo.ASCENDING),
            ])

        for query_type in QueryType:
            query_field = self.QUERY_TYPE_QUERY_FIELD_MAP[query_type]
            score_field = self.QUERY_TYPE_SCORE_FIELD_MAP[query_type]
            self.found_lexical_item_collection.create_index(
                [
                    (query_field, pymongo.DESCENDING),
                    (score_field, pymongo.DESCENDING),
                    ('article_last_updated_datetime', pymongo.DESCENDING),
                    ('article_oid', pymongo.DESCENDING),
                ],
                name=query_field + '_search'
            )

    def close(self) -> None:
        """Close the connection to the database."""
        if self._mongo_client is not None:
            self._mongo_client.close()

    def __enter__(self) -> 'ArticleIndexDb':
        """Initialize the connection to the database."""
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Close the connection to the database."""
        self.close()

    @_require_db_connection
    def read_with_log(
        self, lookup_field_name: str, lookup_values: Union[Any, List[Any]],
        collection: Collection, projection: Document = None
    ) -> List[Document]:
        """Read docs from collection with logging.

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

        if len(lookup_values) == 0:
            return []

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
    @_require_db_connection
    def write_with_log(
        self, docs: List[Document], collection: Collection
    ) -> InsertManyResult:
        """Write docs to collection with logging."""
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
    @_require_db_connection
    def replace_write_with_log(
        self, docs: List[Document], collection: Collection, id_field: str
    ) -> List[ObjectId]:
        """Write or replace with docs with logging.

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
