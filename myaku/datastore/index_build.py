"""Objects for building the Myaku article index."""

import logging
from typing import Dict, List

from bson.objectid import ObjectId

from myaku import utils
from myaku.datastore import DataAccessMode, Query
from myaku.datastore.cache import FirstPageCache
from myaku.datastore.database import ArticleIndexDb
from myaku.datastore.document_convert import (
    convert_articles_to_docs,
    convert_blogs_to_docs,
    convert_found_lexical_items_to_docs,
)
from myaku.datastore.index_search import ArticleIndexSearcher
from myaku.datatypes import (
    ArticleRankKey,
    FoundJpnLexicalItem,
    JpnArticle,
    JpnArticleBlog,
)

_log = logging.getLogger(__name__)


@utils.add_method_debug_logging
class ArticleIndexBuilder(object):
    """Builder for the Myaku article index."""
    MAX_ALLOWED_ARTICLE_LEN = 2**16  # 65,536

    def __init__(self):
        """Initialize the index database connection."""
        self._db = ArticleIndexDb(DataAccessMode.READ_WRITE)

        # Track the best article rank key seen for each found lexical item
        # written to the index for use when updating the article index first
        # page cache on builder close.
        self._fli_best_rank_key_map: Dict[str, ArticleRankKey] = {}

    def close(self) -> None:
        """Close the index database connection."""
        try:
            self._update_first_page_cache()
        finally:
            self._db.close()

    def __enter__(self) -> 'ArticleIndexBuilder':
        """Return self on context enter."""
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Invoke close() method of self on context exit."""
        self.close()

    # Debug level logging can be extremely noisy (can be over 1gb) when enabled
    # during this function, so switch to info level if logging.
    @utils.set_package_log_level(logging.INFO)
    def _update_first_page_cache(self) -> None:
        """Update the first page cache with the newly indexed articles.

        The articles newly indexed by this object are tracked over the object's
        lifetime using the _fli_best_rank_key_map.
        The best article rank key data stored in this map is then used by this
        function to determine which keys in the first page cache need to be
        updated.
        """
        _log.info('Beginning first page cache update...')
        first_page_cache = FirstPageCache()
        update_count = 0
        best_key_map = self._fli_best_rank_key_map
        with ArticleIndexSearcher() as searcher:
            for i, (base_form, best_key) in enumerate(best_key_map.items()):
                if i % 1000 == 0:
                    _log.info(f'Updated {i:,} / {len(best_key_map):,} keys')

                needs_recache = first_page_cache.is_recache_required(
                    Query(base_form, 1), best_key
                )
                if needs_recache:
                    search_result_page = searcher.search_articles_using_db(
                        Query(base_form, 1)
                    )
                    first_page_cache.set(search_result_page)
                    update_count += 1
        _log.info(
            f'Completed first page cache update with {update_count:,} '
            f'keys updated and {len(best_key_map) - update_count:,} keys not '
            f'needing updating'
        )

    def _is_article_text_stored(self, article: JpnArticle) -> bool:
        """Return True if an article with the same text is already stored."""
        docs = self._db.read_with_log(
            'text_hash', article.text_hash, self._db.article_collection,
            {'text_hash': 1, '_id': 0}
        )
        return len(docs) > 0

    def can_store_article(self, article: JpnArticle) -> bool:
        """Return True if the article is safe to store in the db.

        Checks that:
            1. The article is not too long.
            2. There is not an article with the exact same text already stored
                in the db.
        """
        if self._is_article_text_stored(article):
            _log.info('Article %s already stored!', article)
            return False

        if len(article.full_text) > self.MAX_ALLOWED_ARTICLE_LEN:
            _log.info(
                'Article %s is too long to store (%s chars)',
                article, len(article.full_text)
            )
            return False

        return True

    def _get_fli_safe_articles(
            self, flis: List[FoundJpnLexicalItem]
    ) -> List[JpnArticle]:
        """Get the unique articles referenced by the found lexical items.

        Does NOT include any articles in the returned list that cannot be
        safely stored in the index db (due to being too long, etc.).
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
        """Get the unique blogs referenced by the articles."""
        articles_with_blog = [a for a in articles if a.blog]

        # Many found lexical items can point to the same blog object in
        # memory, so dedupe using id() to get each blog object only once.
        blog_id_map = {id(a.blog): a.blog for a in articles_with_blog}
        return list(blog_id_map.values())

    def _write_blogs(
        self, blogs: List[JpnArticleBlog]
    ) -> Dict[int, ObjectId]:
        """Write the blogs to the database.

        Args:
            blogs: Blogs to write to the database.

        Returns:
            A mapping from the id() for each given blog to the ObjectId that
            blog was written with.
        """
        blog_docs = convert_blogs_to_docs(blogs)
        object_ids = self._db.replace_write_with_log(
            blog_docs, self._db.blog_collection, 'source_url'
        )
        blog_oid_map = {
            id(b): oid for b, oid in zip(blogs, object_ids)
        }

        return blog_oid_map

    def _read_article_oids(
        self, articles: List[JpnArticle]
    ) -> Dict[int, ObjectId]:
        """Read the ObjectIds for the articles from the database.

        Args:
            articles: Articles to read from the database.

        Returns:
            A mapping from the id() for each given article to the ObjectId that
            article is stored with.
        """
        source_urls = [a.source_url for a in articles]
        docs = self._db.read_with_log(
            'source_url', source_urls, self._db.article_collection,
            {'source_url': 1}
        )
        source_url_oid_map = {d['source_url']: d['_id'] for d in docs}
        article_oid_map = {
            id(a): source_url_oid_map[a.source_url] for a in articles
        }

        return article_oid_map

    def _write_articles(
        self, articles: List[JpnArticle]
    ) -> Dict[int, ObjectId]:
        """Write the articles to the database.

        Args:
            articles: Articles to write to the database.

        Returns:
            A mapping from the id() for each given article to the ObjectId that
            article was written with.
        """
        blogs = self._get_article_blogs(articles)
        blog_oid_map = self._write_blogs(blogs)

        article_docs = convert_articles_to_docs(articles, blog_oid_map)
        result = self._db.write_with_log(
            article_docs, self._db.article_collection
        )
        article_oid_map = {
            id(a): oid for a, oid in zip(articles, result.inserted_ids)
        }
        return article_oid_map

    def _update_fli_best_rank_key(
        self, found_lexical_items: List[FoundJpnLexicalItem]
    ) -> None:
        """Update the best rank key for the found lexical items.

        The highest quality score for each found lexical item is tracked in
        order to determine which found lexical item entries in the first page
        cache for the article index need to be updated when an
        ArticleIndexBuilder object is closed.
        """
        for fli in found_lexical_items:
            rank_key = ArticleRankKey(
                fli.article.quality_score + fli.quality_score_mod,
                fli.article.last_updated_datetime,
                fli.article.database_id,
            )
            best_rank_key = self._fli_best_rank_key_map.get(fli.base_form)
            if best_rank_key is None or rank_key > best_rank_key:
                self._fli_best_rank_key_map[fli.base_form] = rank_key

    def write_found_lexical_items(
            self, found_lexical_items: List[FoundJpnLexicalItem],
            write_articles: bool = True
    ) -> bool:
        """Write found lexical items and their articles to the index database.

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
            See the can_store_article method docstring for the reasons why an
            article could be considered unsafe.
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

        found_lexical_item_docs = convert_found_lexical_items_to_docs(
            safe_article_flis, safe_article_oid_map
        )
        self._db.write_with_log(
            found_lexical_item_docs, self._db.found_lexical_item_collection
        )
        self._update_fli_best_rank_key(safe_article_flis)

        return len(safe_article_flis) == len(found_lexical_items)
