"""Handles CRUD operations for the Reibun database.

The public members of this module are defined generically so that the
implementation of the article index can be changed freely while keeping the
access interface consistent.
"""

import logging
import re
from operator import itemgetter
from typing import Any, Dict, List, TypeVar, Union

from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.results import InsertManyResult

import reibun
import reibun.utils as utils
from reibun.datatypes import (FoundJpnLexicalItem, InterpSource, JpnArticle,
                              JpnArticleMetadata, JpnLexicalItemInterp)

_log = logging.getLogger(__name__)

T = TypeVar('T')
_Document = Dict[str, Any]


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

    def __init__(self) -> None:
        """Initializes the connection to the database."""
        self._mongo_client = MongoClient()
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
        self._found_lexical_item_collection.create_index(
            'possible_interps.base_form'
        )

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
        docs_key_vals = set()
        for doc in stored_docs:
            docs_key_vals.add(tuple(sorted(doc.items(), key=itemgetter(0))))

        unstored_objs = []
        for obj in objs:
            attr_key_vals = tuple(
                (attr, getattr(obj, attr)) for attr in sorted(eq_attrs)
            )
            if attr_key_vals not in docs_key_vals:
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
            'possible_interps.base_form', base_forms,
            self._found_lexical_item_collection
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
            })

        return docs

    @utils.skip_method_debug_logging
    def _convert_lexical_item_interps_to_docs(
        self, interps: List[JpnLexicalItemInterp]
    ) -> List[_Document]:
        """Converts interps to dicts for inserting into MongoDB."""
        docs = []
        for interp in interps:
            docs.append({
                'base_form': interp.base_form,
                'reading': interp.reading,
                'parts_of_speech': interp.parts_of_speech,
                'conjugated_type': interp.conjugated_type,
                'conjugated_form': interp.conjugated_form,
                'text_form_info': interp.text_form_info,
                'text_form_freq': interp.text_form_freq,
                'fields': interp.fields,
                'dialects': interp.dialects,
                'misc': interp.misc,
                'interp_sources': [s.name for s in interp.interp_sources],
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
            docs.append({
                'surface_form': found_lexical_item.surface_form,
                'article_oid': article_oid_map[id(found_lexical_item.article)],
                'text_pos_abs': found_lexical_item.text_pos_abs,
                'text_pos_percent': found_lexical_item.text_pos_percent,
                'possible_interps': interp_docs,
                'reibun_version_info': self._version_doc,
            })

        return docs

    @utils.skip_method_debug_logging
    def _convert_docs_to_article_metadata(
        self, docs: List[_Document]
    ) -> List[JpnArticle]:
        """Converts docs to article metadata."""
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
        """Converts docs to article objects.

        Returns:
            A mapping from each article document's ObjectId to the created
            article object for that article document.
        """
        oid_article_map = {}
        for doc in docs:
            oid_article_map[doc['_id']] = JpnArticle(
                full_text=doc['full_text'],
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
    def _convert_docs_to_lexical_item_interps(
        self, docs: List[_Document]
    ) -> List[JpnLexicalItemInterp]:
        """Converts docs to lexical item interps."""
        interps = []
        for doc in docs:
            if doc['interp_sources'] is None:
                interp_sources = None
            else:
                interp_sources = tuple(
                    InterpSource[s] for s in doc['interp_sources']
                )

            interps.append(JpnLexicalItemInterp(
                base_form=doc['base_form'],
                reading=doc['reading'],
                parts_of_speech=utils.tuple_or_none(doc['parts_of_speech']),
                conjugated_type=utils.tuple_or_none(doc['conjugated_type']),
                conjugated_form=utils.tuple_or_none(doc['conjugated_form']),
                text_form_info=utils.tuple_or_none(doc['text_form_info']),
                text_form_freq=utils.tuple_or_none(doc['text_form_freq']),
                fields=utils.tuple_or_none(doc['fields']),
                dialects=utils.tuple_or_none(doc['dialects']),
                misc=utils.tuple_or_none(doc['misc']),
                interp_sources=interp_sources,
            ))

        return interps

    def _convert_docs_to_found_lexical_items(
        self, docs: List[_Document],
        oid_article_map: Dict[ObjectId, JpnArticle]
    ) -> List[FoundJpnLexicalItem]:
        """Converts docs to found lexical items.

        The given ObjectId to article map must contain the created article
        objects for all of found lexical item documents.
        """
        found_lexical_items = []
        for doc in docs:
            interps = self._convert_docs_to_lexical_item_interps(
                doc['possible_interps']
            )
            found_lexical_items.append(FoundJpnLexicalItem(
                surface_form=doc['surface_form'],
                article=oid_article_map[doc['article_oid']],
                text_pos_abs=doc['text_pos_abs'],
                possible_interps=interps,
            ))

        return found_lexical_items
