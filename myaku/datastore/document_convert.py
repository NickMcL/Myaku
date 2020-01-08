"""Functions for converting Myaku data to and from MongoDB BSON documents."""

import functools
import logging
from typing import Dict, List

from bson.objectid import ObjectId

import myaku
from myaku import utils
from myaku.datastore import Document, SearchResult
from myaku.datatypes import (
    ArticleTextPosition,
    FoundJpnLexicalItem,
    InterpSource,
    JpnArticle,
    JpnArticleBlog,
    JpnLexicalItemInterp,
    MecabLexicalItemInterp,
)

_log = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _get_myaku_version_doc() -> Document:
    """Get a MongoDB BSON document containing the Myaku package version info.

    It can take a non-trivial amount of work to get the full version info for
    the Myaku package components, so the version info will be cached after
    being retreived when this function is first called, and subsequent calls to
    the function will return the cached version info.
    """
    return myaku.get_version_info()


def convert_blogs_to_docs(blogs: List[JpnArticleBlog]) -> List[Document]:
    """Convert blogs to MongoDB BSON documents."""
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
            'myaku_version_info': _get_myaku_version_doc(),
        })

    return docs


def convert_articles_to_docs(
    articles: List[JpnArticle], blog_oid_map: Dict[int, ObjectId]
) -> List[Document]:
    """Convert articles to MongoDB BSON documents.

    Args:
        articles: List of articles to convert to documents.
        blog_oid_map: A mapping from JpnArticleBlog id()s to the MongoDB
            ObjectId being used for that blog in the Myaku database.
            Must contain entries for all of the blogs referenced by the given
            articles.

    Returns:
        List of MongoDB BSON documents for the given articles.
    """
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
            'myaku_version_info': _get_myaku_version_doc(),
        })

    return docs


def convert_mecab_interp_to_doc(
    mecab_interp: MecabLexicalItemInterp
) -> Document:
    """Convert a MeCab interp to a MongoDB BSON document."""
    doc = {
        'parts_of_speech': mecab_interp.parts_of_speech,
        'conjugated_type': mecab_interp.conjugated_type,
        'conjugated_form': mecab_interp.conjugated_form,
    }

    return doc


def convert_lexical_item_interps_to_docs(
    interps: List[JpnLexicalItemInterp]
) -> List[Document]:
    """Convert lexical item interps to MongoDB BSON documents."""
    docs = []
    for interp in interps:
        interp_sources = [s.value for s in interp.interp_sources]
        if interp.mecab_interp is None:
            mecab_interp_doc = None
        else:
            mecab_interp_doc = convert_mecab_interp_to_doc(interp.mecab_interp)

        docs.append({
            'interp_sources': interp_sources,
            'mecab_interp': mecab_interp_doc,
            'jmdict_interp_entry_id': interp.jmdict_interp_entry_id,
        })

    return docs


def convert_found_positions_to_docs(
    found_positions: List[ArticleTextPosition]
) -> List[Document]:
    """Convert found positions to MongoDB BSON documents."""
    docs = []
    for found_position in found_positions:
        docs.append({
            'index': found_position.start,
            'len': found_position.len
        })

    return docs


def convert_interp_pos_map_to_doc(fli: FoundJpnLexicalItem) -> Document:
    """Convert a found lexical item interp position map to a MongoDB doc."""
    interp_pos_map_doc = {}
    for i, interp in enumerate(fli.possible_interps):
        if interp not in fli.interp_position_map:
            continue

        interp_pos_docs = convert_found_positions_to_docs(
            fli.interp_position_map[interp]
        )
        interp_pos_map_doc[str(i)] = interp_pos_docs

    if len(interp_pos_map_doc) == 0:
        interp_pos_map_doc = None

    return interp_pos_map_doc


def convert_found_lexical_items_to_docs(
    found_lexical_items: List[FoundJpnLexicalItem],
    article_oid_map: Dict[int, ObjectId]
) -> List[Document]:
    """Convert found lexical items to MongoDB BSON documents.

    Args:
        found_lexical_items: List of found lexical items to convert to
            documents.
        article_oid_map: A mapping from JpnArticle id()s to the MongoDB
            ObjectId being used for that article in the Myaku database.
            Must contain entries for all of the articles referenced by the
            given found lexical items.

    Returns:
        List of MongoDB BSON documents for the given articles.
    """
    docs = []
    for fli in found_lexical_items:
        interp_docs = convert_lexical_item_interps_to_docs(
            fli.possible_interps
        )
        found_positions_docs = convert_found_positions_to_docs(
            fli.found_positions
        )
        interp_pos_map_doc = convert_interp_pos_map_to_doc(fli)

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
            'myaku_version_info': _get_myaku_version_doc(),
        })

    return docs


def convert_docs_to_blogs(
    docs: List[Document]
) -> Dict[ObjectId, JpnArticleBlog]:
    """Convert MongoDB BSON documents to blog objects.

    Returns:
        A mapping from each blog document's MongoDB ObjectId to the created
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
            rating=utils.float_or_none(doc['rating']),
            rating_count=utils.int_or_none(doc['rating_count']),
            tags=doc['tags'],
            catchphrase=doc.get('catchphrase'),
            introduction=doc.get('introduction'),
            article_count=utils.int_or_none(doc['article_count']),
            total_char_count=utils.int_or_none(doc['total_char_count']),
            comment_count=utils.int_or_none(doc['comment_count']),
            follower_count=utils.int_or_none(doc['follower_count']),
            in_serialization=doc['in_serialization'],
            last_crawled_datetime=doc.get('last_crawled_datetime'),
        )

    return oid_blog_map


def convert_docs_to_articles(
    docs: List[Document], oid_blog_map: Dict[ObjectId, JpnArticleBlog]
) -> Dict[ObjectId, JpnArticle]:
    """Convert MongoDB BSON documents to article objects.

    Args:
        docs: MongoDB BSON documents to convert to article objects.
        oid_blog_map: A mapping from blogs' MongoDB ObjectIds to blog objects
            with the data for those blogs.
            Must contain entries for all of the blogs referenced in the given
            article documents.

    Returns:
        A mapping from each article document's MongoDB ObjectId to the created
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
            alnum_count=utils.int_or_none(doc['alnum_count']),
            has_video=doc['has_video'],
            tags=doc['tags'],
            blog=oid_blog_map.get(doc['blog_oid']),
            blog_article_order_num=utils.int_or_none(
                doc['blog_article_order_num']
            ),
            blog_section_name=doc['blog_section_name'],
            blog_section_order_num=utils.int_or_none(
                doc['blog_section_order_num']
            ),
            blog_section_article_order_num=utils.int_or_none(doc[
                'blog_section_article_order_num'
            ]),
            publication_datetime=doc['publication_datetime'],
            last_updated_datetime=doc['last_updated_datetime'],
            last_crawled_datetime=doc['last_crawled_datetime'],
            database_id=str(doc['_id']),
            quality_score=utils.int_or_none(doc['quality_score']),
        )

    return oid_article_map


def convert_doc_to_mecab_interp(doc: Document) -> MecabLexicalItemInterp:
    """Convert a MongoDB BSON document to a MeCab interp."""
    mecab_interp = MecabLexicalItemInterp(
        parts_of_speech=utils.tuple_or_none(doc['parts_of_speech']),
        conjugated_type=doc['conjugated_type'],
        conjugated_form=doc['conjugated_form'],
    )

    return mecab_interp


def convert_docs_to_lexical_item_interps(
    docs: List[Document]
) -> List[JpnLexicalItemInterp]:
    """Convert MongoDB BSON documents to lexical item interps."""
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
            mecab_interp = convert_doc_to_mecab_interp(doc['mecab_interp'])

        interps.append(JpnLexicalItemInterp(
            interp_sources=interp_sources,
            mecab_interp=mecab_interp,
            jmdict_interp_entry_id=doc['jmdict_interp_entry_id'],
        ))

    return interps


def convert_docs_to_found_positions(
    docs: List[Document]
) -> List[ArticleTextPosition]:
    """Convert MongoDB BSON documents to found positions."""
    found_positions = []
    for doc in docs:
        found_positions.append(ArticleTextPosition(
            start=utils.int_or_none(doc['index']),
            len=utils.int_or_none(doc['len']),
        ))

    return found_positions


def convert_docs_to_found_lexical_items(
    docs: List[Document], oid_article_map: Dict[ObjectId, JpnArticle]
) -> List[FoundJpnLexicalItem]:
    """Convert MongoDB BSON documents to found lexical items.

    Args:
        docs: MongoDB BSON documents to convert to found lexical item objects.
        oid_article_map: A mapping from articles' MongoDB ObjectIds to article
            objects with the data for those articles.
            Must contain entries for all of the articles referenced in the
            given found lexical item documents.

    Returns:
        A list of found lexical item objects converted from the given
        documents.
    """
    found_lexical_items = []
    for doc in docs:
        interps = convert_docs_to_lexical_item_interps(doc['possible_interps'])
        found_positions = convert_docs_to_found_positions(
            doc['found_positions']
        )

        if doc['interp_position_map'] is None:
            doc['interp_position_map'] = {}

        interp_position_map = {}
        for i in doc['interp_position_map']:
            interp_positions = convert_docs_to_found_positions(
                doc['interp_position_map'][i]
            )
            interp_position_map[interps[int(i)]] = interp_positions

        found_lexical_items.append(FoundJpnLexicalItem(
            base_form=doc['base_form'],
            article=oid_article_map[doc['article_oid']],
            found_positions=found_positions,
            possible_interps=interps,
            interp_position_map=interp_position_map,
            quality_score_mod=utils.int_or_none(
                doc['quality_score_exact_mod']
            ),
            database_id=str(doc['_id']),
        ))

    return found_lexical_items


def convert_docs_to_search_results(
    docs: List[Document], oid_article_map: Dict[ObjectId, JpnArticle]
) -> List[SearchResult]:
    """Convert MongoDB BSON documents to article search results.

    Args:
        docs: MongoDB BSON documents to convert to search result objects.
        oid_article_map: A mapping from articles' MongoDB ObjectIds to article
            objects with the data for those articles.
            Must contain entries for all of the articles referenced in the
            given search result documents.

    Returns:
        A list of search result objects converted from the given documents.
    """
    search_results = []
    for doc in docs:
        found_positions = convert_docs_to_found_positions(
            doc['found_positions']
        )

        search_results.append(SearchResult(
            article=oid_article_map[doc['article_oid']],
            matched_base_forms=doc['matched_base_forms'],
            found_positions=found_positions,
            quality_score=utils.int_or_none(doc['quality_score']),
        ))

    return search_results
