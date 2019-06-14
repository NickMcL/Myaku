"""Handles CRUD operations for the Reibun index database.

The public members of this module are defined generically so that the
implementation of the article index can be changed freely while keeping the
access interface consistent.
"""

import logging
from typing import Any, Dict, List, Union

from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.results import InsertManyResult

import reibun.utils as utils
from reibun.datatypes import (FoundJpnLexicalItem, InterpSource, JpnArticle,
                              JpnLexicalItemInterp)

_log = logging.getLogger(__name__)

_Document = Dict[str, Any]


@utils.add_method_debug_logging
class ReibunIndexDb(object):
    """Interface object for accessing the Reibun index database.

    This database stores mappings from Japanese lexical items to native
    Japanese web articles that use those lexical item. This allows for easy
    look up of native Japanese articles that make use of a particular lexical
    item of interest.

    Implements the Reibun index using MongoDB.
    """
    _DB_NAME = 'reibun'
    _ARTICLE_COLL_NAME = 'articles'
    _FOUND_LEXICAL_ITEM_COLL_NAME = 'found_lexical_items'

    def __init__(self) -> None:
        """Initializes the connection to the database."""
        self._mongo_client = MongoClient()
        _log.debug(
            'Connected to MongoDB at %s:%s',
            self._mongo_client.address[0], self._mongo_client.address[1]
        )

        self._db = self._mongo_client[self._DB_NAME]
        self._article_collection = self._db[self._ARTICLE_COLL_NAME]
        self._found_lexical_item_collection = (
            self._db[self._FOUND_LEXICAL_ITEM_COLL_NAME]
        )

        self._create_indexes()

    def _create_indexes(self) -> None:
        """Creates the necessary indexes for the db if they don't exist."""
        self._article_collection.create_index('text_hash')
        self._found_lexical_item_collection.create_index(
            'possible_interps.base_form'
        )

    def filter_to_unstored_articles(
        self, articles: List[JpnArticle]
    ) -> List[JpnArticle]:
        """Returns new list with articles not currently stored in the database.

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
        docs = self._read_with_log(
            'text_hash', article_hashes, self._article_collection,
            {'text_hash': 1, '_id': 0}
        )

        stored_hashes = set(doc['text_hash'] for doc in docs)
        return [a for a in articles if a.text_hash not in stored_hashes]

    def write_found_lexical_items(
            self, found_lexical_items: List[FoundJpnLexicalItem]
    ) -> None:
        """Writes the found lexical items to the database."""
        # Many found lexical items can point to the same article object in
        # memory, so dedupe using id() to get each article object only once
        article_id_map = {
            id(item.article): item.article for item in found_lexical_items
        }
        articles = list(article_id_map.values())

        article_docs = self._convert_articles_to_docs(articles)
        result = self._write_with_log(article_docs, self._article_collection)

        article_oid_map = {
            id(a): oid for a, oid in zip(articles, result.inserted_ids)
        }
        found_lexical_item_docs = self._convert_found_lexical_items_to_docs(
            found_lexical_items, article_oid_map
        )
        self._write_with_log(
            found_lexical_item_docs, self._found_lexical_item_collection
        )

    def read_found_lexical_items(
        self, base_forms: Union[str, List[str]]
    ) -> List[FoundJpnLexicalItem]:
        """Reads found lexical items that match base form from the database.

        Args:
            base_forms: Either one or a list of base forms of Japanese lexical
                items to search for matching found lexical items in the db.

        Returns:
            A list of found lexical items with at least on possible
            interpretation that matches at least one of the base forms given.
        """
        if isinstance(base_forms, str):
            base_forms = [base_forms]

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

    def close(self) -> None:
        """Closes the connection to the database."""
        self._mongo_client.close()

    def __enter__(self) -> 'ReibunIndexDb':
        """Initializes the connection to the database."""
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Closes the connection to the database."""
        self.close()

    def _read_with_log(
        self, lookup_field_name: str, lookup_values: List[Any],
        collection: Collection, projection: _Document = None
    ) -> List[_Document]:
        """Reads docs from collection with before and after logging.

        Args:
            lookup_field_name: The field to query on. Should be an indexed
                field to ensure high performance.
            lookup_values: The values for the lookup field to query for.
            collection: The collection to query.
            projection: The projection to use for the query. No projection will
                be used if None.

        Returns:
            Retreives all documents from the cursor for the query and returns
            them in a list.
        """
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

    def _convert_articles_to_docs(
        self, articles: List[JpnArticle]
    ) -> List[_Document]:
        """Converts articles to dicts for inserting into MongoDB."""
        docs = []
        for article in articles:
            docs.append({
                'title': article.title,
                'full_text': article.full_text,
                'text_hash': article.text_hash,
                'alnum_count': article.alnum_count,
                'source_url': article.source_url,
                'source_name': article.source_name,
                'publication_datetime': article.publication_datetime,
                'scraped_datetime': article.scraped_datetime,
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
            })

        return docs

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
                title=doc['title'],
                full_text=doc['full_text'],
                source_url=doc['source_url'],
                source_name=doc['source_name'],
                publication_datetime=doc['publication_datetime'],
                scraped_datetime=doc['scraped_datetime'],
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
