"""Objects for searching the Myaku article index."""

import logging
from typing import Dict, List, Optional

import pymongo
from bson.objectid import ObjectId
from pymongo.cursor import Cursor

from myaku import utils
from myaku.datastore import (
    SEARCH_RESULTS_PAGE_SIZE,
    DataAccessMode,
    Document,
    Query,
    SearchResultPage,
)
from myaku.datastore.cache import FirstPageCache, NextPageCache
from myaku.datastore.database import ArticleIndexDb
from myaku.datastore.document_convert import (
    convert_docs_to_articles,
    convert_docs_to_blogs,
    convert_docs_to_search_results,
)
from myaku.datatypes import JpnArticle

_log = logging.getLogger(__name__)


@utils.add_method_debug_logging
class ArticleIndexSearcher(object):
    """Interface object for searching the Myaku article index."""

    def __init__(self):
        """Initialize the index database and cache connections."""
        self._db = ArticleIndexDb(DataAccessMode.READ)
        self._first_page_cache = FirstPageCache()
        self._next_page_cache = NextPageCache()

    def close(self) -> None:
        """Close the index database connection."""
        self._db.close()

    def __enter__(self) -> 'ArticleIndexSearcher':
        """Return self on context enter."""
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Invoke close() method of self on context exit."""
        self.close()

    def _get_query_article_count(self, query: Query) -> int:
        """Get the total number of articles in the db matching the query.

        Does not consider the page number of the query when counting the number
        of matching articles in the database.
        """
        query_field = self._db.QUERY_TYPE_QUERY_FIELD_MAP[query.query_type]

        cursor = self._db.found_lexical_item_collection.aggregate([
            {'$match': {query_field: query.query_str}},
            {'$group': {'_id': '$article_oid'}},
            {'$count': 'total'},
        ])
        docs = list(cursor)
        return docs[0]['total'] if len(docs) > 0 else 0

    def _read_articles(
        self, object_ids: List[ObjectId]
    ) -> Dict[ObjectId, JpnArticle]:
        """Read the articles for the given ObjectIds from the database.

        Args:
            object_ids: ObjectIds for articles to read from the database.

        Returns:
            A mapping from the given ObjectIds to the article stored in the
            database for that ObjectId.
        """
        article_docs = self._db.read_with_log(
            '_id', object_ids, self._db.article_collection
        )

        blog_oids = list(
            set(doc['blog_oid'] for doc in article_docs if doc['blog_oid'])
        )
        if len(blog_oids) > 0:
            blog_docs = self._db.read_with_log(
                '_id', blog_oids, self._db.blog_collection
            )
            oid_blog_map = convert_docs_to_blogs(blog_docs)
        else:
            oid_blog_map = {}

        oid_article_map = convert_docs_to_articles(
            article_docs, oid_blog_map
        )
        return oid_article_map

    def _get_article_docs_from_search_results(
        self, search_results_cursor: Cursor, quality_score_field: str,
        results_start_index: int, max_results_to_return: int
    ) -> List[Document]:
        """Merge the top search result docs together to get one per article.

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
        article_search_result_docs: List[Document] = []
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
    def _get_from_first_page_cache(
        self, query: Query
    ) -> Optional[SearchResultPage]:
        """Get first page of search results for query from first page cache.

        Args:
            query: Query to get the first page of search results for from the
                cache.

        Returns:
            The first page of search results for the query if the page was in
            the first page cache, or None of the first page of search results
            for the query was not in the first page cache.
        """
        _log.debug('Checking first page cache for query "%s"', query)
        cached_first_page = self._first_page_cache.get(query)
        if cached_first_page:
            _log.info(
                'Page for query "%s" retrieved from first page cache', query
            )
            return cached_first_page

        _log.debug(
            'Query "%s" search results not found in first page cache', query
        )
        return None

    @utils.skip_method_debug_logging
    def _get_from_next_page_cache(
        self, query: Query
    ) -> Optional[SearchResultPage]:
        """Get page of search results from the next page cache.

        Args:
            query: Query to get a page of search results for from the cache.

        Returns:
            The page of search results for the query if the page for it was in
            the next page cache, or None if the page for the query was not in
            the next page cache.
        """
        _log.debug('Checking next page cache for query "%s"', query)
        cached_next_page = self._next_page_cache.get(query)
        if cached_next_page:
            _log.info(
                'Page for query "%s" retrieved from next page cache', query
            )
            return cached_next_page

        _log.debug(
            'Query "%s" search results not found in next page cache', query
        )
        return None

    @utils.skip_method_debug_logging
    def search_articles_using_db(self, query: Query) -> SearchResultPage:
        """Search for articles that match the query using only the index db.

        Does not use the search result caches in any case.

        The search results are in ranked order by quality score. See the scorer
        module for more info on how quality scores are determined.

        Args:
            query: Query to get a page of search results for from the db.

        Returns:
            The queried page of search results.
        """
        query_field = self._db.QUERY_TYPE_QUERY_FIELD_MAP[query.query_type]
        score_field = self._db.QUERY_TYPE_SCORE_FIELD_MAP[query.query_type]

        cursor = self._db.found_lexical_item_collection.find(
            {query_field: query.query_str}
        )
        cursor.sort([
            (score_field, pymongo.DESCENDING),
            ('article_last_updated_datetime', pymongo.DESCENDING),
            ('article_oid', pymongo.DESCENDING),
        ])
        search_result_docs = self._get_article_docs_from_search_results(
            cursor, score_field,
            (query.page_num - 1) * SEARCH_RESULTS_PAGE_SIZE,
            SEARCH_RESULTS_PAGE_SIZE
        )

        article_oids = [doc['article_oid'] for doc in search_result_docs]
        oid_article_map = self._read_articles(article_oids)

        search_results = convert_docs_to_search_results(
            search_result_docs, oid_article_map
        )
        return SearchResultPage(
            query=query,
            total_results=self._get_query_article_count(query),
            search_results=search_results
        )

    def search_articles(self, query: Query) -> SearchResultPage:
        """Search the index for articles that match the lexical item query.

        Uses cached search results if possible.

        The search results are in ranked order by quality score. See the scorer
        module for more info on how quality scores are determined.

        Args:
            query: Query to get a page of search results for from the db.

        Returns:
            The queried page of search results.
        """
        if query.page_num == 1:
            cached_first_page = self._get_from_first_page_cache(query)
            if cached_first_page:
                return cached_first_page
        else:
            cached_next_page = self._get_from_next_page_cache(query)
            if cached_next_page:
                return cached_next_page

        _log.info(
            'Query "%s" search results will be retrieved from the crawl '
            'database', query
        )
        return self.search_articles_using_db(query)
