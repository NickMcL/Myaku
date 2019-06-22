"""Handles CRUD operations for the Reibun database.

The public members of this module are defined generically so that the
implementation of the article index can be changed freely while keeping the
access interface consistent.
"""

import logging
import re
import os
from collections import defaultdict
from datetime import datetime
from operator import methodcaller
from typing import Any, Dict, List, TypeVar, Union

import pytz
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.results import InsertManyResult

import reibun
import reibun.utils as utils
from reibun.datatypes import (FoundJpnLexicalItem, InterpSource, JpnArticle,
                              JpnArticleMetadata, JpnLexicalItemInterp,
                              LexicalItemTextPosition, MecabLexicalItemInterp)

_log = logging.getLogger(__name__)

T = TypeVar('T')
_Document = Dict[str, Any]

_DB_HOST_ENV_VAR = 'REIBUN_DB_HOST'
_DB_HOST = os.environ.get(_DB_HOST_ENV_VAR)
if _DB_HOST is None:
    _DB_HOST = 'localhost'

_DB_PORT = 27017


@utils.add_method_debug_logging
class ReibunDb(object):
    """Interface object for accessing the Reibun database.

    This database stores mappings from Japanese lexical items to native
    Japanese web articles that use those lexical item. This allows for easy
    look up of native Japanese articles that make use of a particular lexical
    item of interest.

    Implements the Reibun database using MongoDB.
    """
    _DB_NAME = 'reibun'
    _ARTICLE_COLL_NAME = 'articles'
    _FOUND_LEXICAL_ITEM_COLL_NAME = 'found_lexical_items'

    # Stores only metadata for previous crawled articles. Used to keep track of
    # which articles have been crawled before so that crawlers don't try to
    # crawl them again even after the article is deleted from the articles
    # collection.
    _CRAWLED_COLL_NAME = 'crawled'

    BASE_FORM_COUNT_LIMIT = 1000
    _EXCESS_BASE_FORM_AGGREGATE = [
        {'$match': {'base_form': {'$gt': ''}}},
        {'$group': {'_id': '$base_form', 'total': {'$sum': 1}}},
        {'$match': {'total': {'$gt': BASE_FORM_COUNT_LIMIT}}},
    ]

    def __init__(self) -> None:
        """Initializes the connection to the database."""
        self._mongo_client = MongoClient(_DB_HOST, _DB_PORT)
        _log.debug(
            'Connected to MongoDB at %s:%s',
            self._mongo_client.address[0], self._mongo_client.address[1]
        )

        self._db = self._mongo_client[self._DB_NAME]
        self._article_collection = self._db[self._ARTICLE_COLL_NAME]
        self._crawled_collection = self._db[self._CRAWLED_COLL_NAME]
        self._found_lexical_item_collection = (
            self._db[self._FOUND_LEXICAL_ITEM_COLL_NAME]
        )

        self._create_indexes()

        self._version_doc = reibun.get_version_info()

    def _create_indexes(self) -> None:
        """Creates the necessary indexes for the db if they don't exist."""
        self._article_collection.create_index('text_hash')
        self._crawled_collection.create_index('title')
        self._crawled_collection.create_index('source_name')
        self._crawled_collection.create_index('publication_datetime')
        self._found_lexical_item_collection.create_index('base_form')
        self._found_lexical_item_collection.create_index('article_oid')

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

    def filter_to_unstored_article_metadatas(
        self, metadatas: List[JpnArticleMetadata], eq_attrs: List[str]
    ) -> List[JpnArticleMetadata]:
        """Returns new list with the metadatas not currently stored in the db.

        Uses a comparison on the attributes specified in eq_attrs to determine
        if two article metadatas are equal.

        Does not modify the given article metadatas list.

        Args:
            metadatas: A list of article metadatas to check for in the
                database.
            eq_attrs: A list of attributes names whose values to compare to
                determine if two article metadatas are equivalent.

        Returns:
            The article metadatas from the given list that are not currently
            stored in the database based on a comparison using eq_attrs.
            Preserves ordering used in the given list.
        """
        match_docs = [dict() for _ in metadatas]
        for i, metadata in enumerate(metadatas):
            for field in eq_attrs:
                match_docs[i][field] = getattr(metadata, field)

        if len(match_docs) == 1:
            query = match_docs[0]
        else:
            query = {'$or': match_docs}

        projection = {field: 1 for field in eq_attrs}
        projection['_id'] = 0

        _log.debug(
            'Will query %s with %s metadatas using %s fields',
            self._crawled_collection.full_name, len(match_docs), eq_attrs
        )
        cursor = self._crawled_collection.find(query, projection)
        stored_docs = list(cursor)
        _log.debug(
            'Retrieved %s documents from %s',
            len(stored_docs), self._crawled_collection.full_name
        )

        unstored_metadatas = self._filter_to_unstored(
            metadatas, stored_docs, eq_attrs
        )
        return unstored_metadatas

    def _filter_to_unstored(
        self, objs: List[T], stored_docs: List[_Document], eq_attrs: List[str]
    ) -> List[T]:
        """Filters the objects to only those without an equal stored document.

        Uses a comparison on the attributes specified in eq_attrs to determine
        if an object is equivalent to a document.

        Runs in O(o*e + d*e) where o is the number of objects, d is the number
        of stored docs, and e is the number of eq attributes.

        Does not modify the given object or document lists.

        Args:
            objs: Object list to filter to remove stored objects.
            stored_docs: Stored documents to compare to the given objects to
                determine if an object is stored or not.
            eq_attrs: The attributes of the objects to compare to fields in the
                documents to determine if an object is equal to a document. All
                attributes in this list must be equal for an object and
                document to be considered equal.

        Returns:
            A new list containing only the objects from the given object list
            that do not have an equivalent document in the given document list
            based on a comparison of the attributes in eq_attrs.
            Preserves ordering used in the given objects list.
        """
        sorted_eq_attrs = sorted(eq_attrs)

        docs_key_vals = set()
        for doc in stored_docs:
            key_vals = []
            for attr in sorted_eq_attrs:
                if isinstance(doc[attr], datetime):
                    key_vals.append((attr, doc[attr].replace(tzinfo=pytz.utc)))
                else:
                    key_vals.append((attr, doc[attr]))
            docs_key_vals.add(tuple(key_vals))

        unstored_objs = []
        for obj in objs:
            key_vals = []
            for attr in sorted_eq_attrs:
                value = getattr(obj, attr)
                if isinstance(value, datetime):
                    key_vals.append((attr, value.replace(tzinfo=pytz.utc)))
                else:
                    key_vals.append((attr, value))

            if tuple(key_vals) not in docs_key_vals:
                unstored_objs.append(obj)

        return unstored_objs

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
        # Many found lexical items can point to the same article object in
        # memory, so dedupe using id() to get each article object only once
        article_id_map = {
            id(item.article): item.article for item in found_lexical_items
        }
        articles = list(article_id_map.values())

        if write_articles:
            article_docs = self._convert_articles_to_docs(articles)
            result = self._write_with_log(
                article_docs, self._article_collection
            )
            article_oid_map = {
                id(a): oid for a, oid in zip(articles, result.inserted_ids)
            }

        else:
            text_hashes = [a.text_hash for a in articles]
            docs = self._read_with_log(
                'text_hash', text_hashes, self._article_collection,
                {'text_hash': 1}
            )
            hash_oid_map = {d['text_hash']: d['_id'] for d in docs}
            article_oid_map = {
                id(a): hash_oid_map[a.text_hash] for a in articles
            }

        found_lexical_item_docs = self._convert_found_lexical_items_to_docs(
            found_lexical_items, article_oid_map
        )
        self._write_with_log(
            found_lexical_item_docs, self._found_lexical_item_collection
        )

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
        article_docs = self._read_with_log(
            '_id', article_oids, self._article_collection
        )
        oid_article_map = self._convert_docs_to_articles(article_docs)

        found_lexical_items = self._convert_docs_to_found_lexical_items(
            found_lexical_item_docs, oid_article_map
        )
        return found_lexical_items

    def read_articles(self) -> List[JpnArticle]:
        """Reads all articles from the database."""
        _log.debug(
            'Will query %s for all documents',
            self._article_collection.full_name
        )
        cursor = self._article_collection.find({})
        docs = list(cursor)
        _log.debug(
            'Retrieved %s documents from %s',
            len(docs), self._article_collection
        )

        article_oid_map = self._convert_docs_to_articles(docs)
        return list(article_oid_map.values())

    def write_crawled(self, metadatas: List[JpnArticleMetadata]) -> None:
        """Writes the article metadata to the crawled database."""
        metadata_docs = self._convert_article_metadata_to_docs(metadatas)
        self._write_with_log(metadata_docs, self._crawled_collection)

    def read_crawled(self, source_name: str) -> List[JpnArticleMetadata]:
        """Reads article metadata for given source from the crawled database.

        Args:
            source_name: Either one or a list of source names to get the
                previously crawled article metadata for from the database.

        Returns:
            A list of article metadatas.
        """
        metadata_docs = self._read_with_log(
            'source_name', source_name, self._crawled_collection
        )
        metadatas = self._convert_docs_to_article_metadata(metadata_docs)
        return metadatas

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

    def delete_base_form_excess(self) -> None:
        """Deletes found lexical items with base forms in excess in the db.

        A base form is considered in excess if over a certain limit
        (BASE_FORM_COUNT_LIMIT) of found lexical items with the base form are
        in the database.

        This function:
            1. Finds all base forms in excess in the database.
            2. Ranks all of the found lexical items for each from highest to
                lowest quality of usage of that base form.
            3. Deletes all found lexical items for each with quality rank not
                within BASE_FORM_COUNT_LIMIT.
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
        for fli in excess_flis[self.BASE_FORM_COUNT_LIMIT:]:
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

    def __enter__(self) -> 'ReibunDb':
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
        """Writes docs to collection with before and after logging."""
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

    def _convert_article_metadata_to_docs(
        self, metadatas: List[JpnArticleMetadata]
    ) -> List[_Document]:
        """Converts article metadata to dicts for inserting into MongoDB."""
        docs = []
        for metadata in metadatas:
            docs.append({
                'title': metadata.title,
                'source_url': metadata.source_url,
                'source_name': metadata.source_name,
                'publication_datetime': metadata.publication_datetime,
                'scraped_datetime': metadata.scraped_datetime,
                'reibun_version_info': self._version_doc,
            })

        return docs

    def _convert_articles_to_docs(
        self, articles: List[JpnArticle]
    ) -> List[_Document]:
        """Converts articles to dicts for inserting into MongoDB."""
        docs = []
        for article in articles:
            docs.append({
                'full_text': article.full_text,
                'title': article.metadata.title,
                'source_url': article.metadata.source_url,
                'source_name': article.metadata.source_name,
                'publication_datetime': article.metadata.publication_datetime,
                'scraped_datetime': article.metadata.scraped_datetime,
                'text_hash': article.text_hash,
                'alnum_count': article.alnum_count,
                'reibun_version_info': self._version_doc,
                'has_video': article.has_video,
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

    def _convert_found_lexical_items_to_docs(
        self, found_lexical_items: List[FoundJpnLexicalItem],
        article_oid_map: Dict[JpnArticle, ObjectId]
    ) -> List[_Document]:
        """Converts found lexical items to dicts for inserting into MongoDB.

        The given article to ObjectId map must contain all of the articles for
        the given found lexical items.
        """
        docs = []
        for found_lexical_item in found_lexical_items:
            interp_docs = self._convert_lexical_item_interps_to_docs(
                found_lexical_item.possible_interps
            )
            found_positions_docs = self._convert_found_positions_to_docs(
                found_lexical_item.found_positions
            )

            interp_pos_map_doc = {}
            for i, interp in enumerate(found_lexical_item.possible_interps):
                if interp not in found_lexical_item.interp_position_map:
                    continue

                interp_pos_docs = self._convert_found_positions_to_docs(
                    found_lexical_item.interp_position_map[interp]
                )
                interp_pos_map_doc[str(i)] = interp_pos_docs

            if len(interp_pos_map_doc) == 0:
                interp_pos_map_doc = None

            docs.append({
                'base_form': found_lexical_item.base_form,
                'article_oid': article_oid_map[id(found_lexical_item.article)],
                'found_positions': found_positions_docs,
                'possible_interps': interp_docs,
                'interp_position_map': interp_pos_map_doc,
                'reibun_version_info': self._version_doc,
            })

        return docs

    @utils.skip_method_debug_logging
    def _convert_docs_to_article_metadata(
        self, docs: List[_Document]
    ) -> List[JpnArticle]:
        """Converts MongoDB docs to article metadata."""
        metadatas = []
        for doc in docs:
            metadatas.append(JpnArticleMetadata(
                title=doc['title'],
                source_url=doc['source_url'],
                source_name=doc['source_name'],
                publication_datetime=doc['publication_datetime'],
                scraped_datetime=doc['scraped_datetime'],
            ))

        return metadatas

    def _convert_docs_to_articles(
        self, docs: List[_Document]
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
                metadata=JpnArticleMetadata(
                    title=doc['title'],
                    source_url=doc['source_url'],
                    source_name=doc['source_name'],
                    publication_datetime=doc['publication_datetime'],
                    scraped_datetime=doc['scraped_datetime'],
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
