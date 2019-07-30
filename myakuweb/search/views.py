from operator import methodcaller
from typing import List

from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render

from myaku.database import MyakuCrawlDb
from myaku.datatypes import (FoundJpnLexicalItem, JpnArticle,
                             LexicalItemTextPosition)


MATCH_TYPE_DESC_MAP = {
    'Exact match': 'exactly matching',
    'Starts with': 'starting with',
    'Ends with': 'ending with',
}


class QueryArticleResultSet(object):
    """The set of article results of a query of the Myaku db."""

    def __init__(self, query: str) -> None:
        """Queries the Myaku db to get the article result set for query."""
        if query:
            with MyakuCrawlDb(read_only=True) as db:
                self._result_flis = db.read_found_lexical_items(query, True)
        else:
            self._result_flis = []

        self._result_flis.sort(key=methodcaller('quality_key'), reverse=True)
        self._result_flis = self._result_flis[:20]

        self.article_count = len(self._result_flis)
        self.instance_count = sum(
            len(item.found_positions) for item in self._result_flis
        )

        self.ranked_article_results = [
            QueryArticleResult(fli) for fli in self._result_flis
        ]


class QueryArticleResult(object):
    """A single article result of a query of the Myaku db."""

    def __init__(self, fli: FoundJpnLexicalItem) -> None:
        """Populates article result data using given found lexical item."""
        self.title = fli.article.metadata.title
        self.publication_datetime = fli.article.metadata.publication_datetime
        self.source_name = fli.article.metadata.source_name
        self.source_url = fli.article.metadata.source_url
        self.alnum_count = fli.article.alnum_count
        self.total_instances = len(fli.found_positions)
        self.tags = self._get_tags(fli)

        self.instance_results = []
        for pos in fli.found_positions:
            self.instance_results.append(QueryInstanceResult(pos, fli.article))

    def _get_tags(self, fli: FoundJpnLexicalItem) -> List[str]:
        """Gets the tags applicable for the found lexical item."""
        tag_strs = []
        tag_strs.append(
            str(fli.article.get_article_len_group()) + '+ characters'
        )
        if fli.article.has_video:
            tag_strs.append('Video')
        return tag_strs


class QueryInstanceResult(object):
    """A single found lexical item instance of a query of the Myaku db."""

    def __init__(
        self, pos: LexicalItemTextPosition, article: JpnArticle
    ) -> None:
        """Populates instance result data using given position in article."""
        sentence, start = article.get_containing_sentence(pos)
        sentence = sentence.rstrip()

        self.pos_percent = round((pos.index / len(article.full_text)) * 100)
        self.sentence_start_text = sentence[:pos.index - start]
        self.instance_text = sentence[
            pos.index - start: pos.index + pos.len - start
        ]
        self.sentence_end_text = sentence[
            pos.index + pos.len - start:
        ]


def index(request: HttpRequest) -> HttpResponse:
    """Search index page handler."""
    if len(request.GET.get('q', '')) > 0:
        match_type = request.GET.get('match_type', 'Starts with')
        query_result_set = QueryArticleResultSet(request.GET['q'])
        return render(
            request, 'search/results.html',
            {
                'display_results': True,
                'match_type_desc': MATCH_TYPE_DESC_MAP[match_type],
                'query_result_set': query_result_set
            }
        )

    return render(request, 'search/index.html', {'display_results': False})
