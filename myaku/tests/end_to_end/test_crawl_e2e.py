"""End-to-end tests for the Myaku crawl scenarios."""

import copy
import os
import re
from collections import defaultdict
from datetime import datetime
from operator import itemgetter
from typing import Any, DefaultDict, Dict, List, Set
from unittest.mock import Mock

import pymongo
import requests
from bson.objectid import ObjectId

from myaku import utils
from myaku.crawlers import kakuyomu
from myaku.datastore import JpnArticleSearchResult
from myaku.datastore.cache import FirstPageCache
from myaku.datastore.database import CrawlDb, _Document
from myaku.datatypes import ArticleTextPosition
from myaku.runners import run_crawl

TEST_DIR = os.path.dirname(os.path.relpath(__file__))

ARTICLE_CACHED_ATTRS = [
    'source_name',
    'source_url',
    'publication_datetime',
    'last_updated_datetime',
    'title',
    'full_text',
    'text_hash',
    'alnum_count',
    'has_video',
]

VERSION_DOC_EXPECTED_FIELD_COUNT = 4
VERSION_DOC_REGEXES = {
    'myaku_python_package': re.compile(r'^\d+\.\d+\.\d+$'),
    'MeCab': re.compile(r'^\d+\.\d+$'),
    'JMdict': re.compile(r'^\d\d\d\d\.\d\d\.\d\d$'),
    'ipadic-NEologd': re.compile(r'^\d\d\d\d\.\d\d\.\d\d$'),
}

BLOG_DOC_EXPECTED_FIELD_COUNT = 19
INITIAL_CRAWL_EXPECTED_BLOG_DOCS = [
    {
        'title': 'Kakuyomu Series 1',
        'author': 'Kakuyomu Author 1',
        'source_name': 'Kakuyomu',
        'source_url': 'https://kakuyomu.jp/series-link-1',
        'publication_datetime': datetime.fromisoformat('2018-04-28T01:10:28'),
        'last_updated_datetime': datetime.fromisoformat('2019-09-05T13:13:24'),
        'rating': 521,
        'rating_count': 221,
        'tags': ['Nonfiction', 'Watch out!', 'Tag 1', 'Tag 2', 'Tag 3'],
        'catchphrase': 'Catchy catchphrase',
        'introduction':
            'Intoduction text\nAfter a br\nA little bit more\n'
            'This bit is hidden behind show rest\nA bit more after that\n\n',
        'article_count': 3,
        'total_char_count': 30182,
        'comment_count': 60,
        'follower_count': 1023,
        'in_serialization': True,
    },
    {
        'title': 'Kakuyomu Series 2',
        'author': 'Kakuyomu Author 2',
        'source_name': 'Kakuyomu',
        'source_url': 'https://kakuyomu.jp/series-link-2',
        'publication_datetime': datetime.fromisoformat('2015-02-20T08:10:47'),
        'last_updated_datetime': datetime.fromisoformat('2018-03-21T03:43:01'),
        'rating': 0,
        'rating_count': 0,
        'tags': ['Nonfiction'],
        'catchphrase': None,
        'introduction': None,
        'article_count': 2,
        'total_char_count': 620,
        'comment_count': 0,
        'follower_count': 0,
        'in_serialization': False,
    },
    {
        'title': 'Kakuyomu Series 3',
        'author': 'Kakuyomu Author 3',
        'source_name': 'Kakuyomu',
        'source_url': 'https://kakuyomu.jp/series-link-3',
        'publication_datetime': datetime.fromisoformat('2015-07-11T11:47:00'),
        'last_updated_datetime': datetime.fromisoformat('2017-12-01T20:00:00'),
        'rating': 12,
        'rating_count': 5,
        'tags': ['Nonfiction', 'Tag 4'],
        'catchphrase': '自業自得',
        'introduction': None,
        'article_count': 1,
        'total_char_count': 1333,
        'comment_count': None,
        'follower_count': 9,
        'in_serialization': True,
    },
]

# Use deepcopy to avoid modifying any of the contents of the initial docs.
UPDATE_CRAWL_EXPECTED_BLOG_DOCS = copy.deepcopy(
    INITIAL_CRAWL_EXPECTED_BLOG_DOCS
)
UPDATE_CRAWL_EXPECTED_BLOG_DOCS[2] = {
    'title': 'Kakuyomu Series 3',
    'author': 'Kakuyomu Author 3v2',
    'source_name': 'Kakuyomu',
    'source_url': 'https://kakuyomu.jp/series-link-3',
    'publication_datetime': datetime.fromisoformat('2015-07-11T11:47:00'),
    'last_updated_datetime': datetime.fromisoformat('2037-09-06T15:30:28'),
    'rating': 17,
    'rating_count': 6,
    'tags': ['Nonfiction', 'Tag 4'],
    'catchphrase': '自業自得',
    'introduction': None,
    'article_count': 2,
    'total_char_count': 2145,
    'comment_count': None,
    'follower_count': 13,
    'in_serialization': False,
}
UPDATE_CRAWL_EXPECTED_BLOG_DOCS.append({
    'title': 'Kakuyomu Series 4',
    'author': 'Kakuyomu Author 4',
    'source_name': 'Kakuyomu',
    'source_url': 'https://kakuyomu.jp/series-link-4',
    'publication_datetime': datetime.fromisoformat('2037-09-06T09:18:02'),
    'last_updated_datetime': datetime.fromisoformat('2037-09-06T09:18:02'),
    'rating': 3,
    'rating_count': 1,
    'tags': ['Nonfiction', 'Watch out!'],
    'catchphrase': None,
    'introduction':
        '　これは僕の短い序文です。\n\n宜しくお願いします。\n          ',
    'article_count': 1,
    'total_char_count': 421,
    'comment_count': 1,
    'follower_count': 1,
    'in_serialization': True,
})


ARTICLE_DOC_EXPECTED_FIELD_COUNT = 20
INITIAL_CRAWL_EXPECTED_ARTICLE_DOCS = [
    {
        'full_text':
            'Kakuyomu Series 1 Article 1\n\n'
            '　桜の花が咲くと人々は酒をぶらさげたり団子だんごをたべて花の下を'
            '歩いて絶景だの春ランマンだのと浮かれて陽気になりますが、これは嘘'
            'です。\n'
            '　なぜ嘘かと申しますと、桜の花の下へ人がより集って酔っ払ってゲロ'
            'を吐いて喧嘩けんかして、これは江戸時代からの話で、大昔は桜の花の'
            '下は怖しいと思っても、絶景だなどとは誰も思いませんでした。近頃は'
            '桜の花の下といえば人間がより集って酒をのんで喧嘩していますから陽'
            '気でにぎやかだと思いこんでいますが、桜の花の下から人間を取り去る'
            'と怖ろしい景色になりますので、能にも、さる母親が愛児を人さらいに'
            'さらわれて子供を探して発狂して桜の花の満開の林の下へ来かかり見渡'
            'す花びらの陰に子供の幻を描いて狂い死して花びらに埋まってしまう'
            '（このところ小生の蛇足だそく）という話もあり、桜の林の花の下に人'
            'の姿がなければ怖しいばかりです。\n'
            '　昔、鈴鹿峠にも旅人が桜の森の花の下を通らなければならないような'
            '道になっていました。花の咲かない頃はよろしいのですが、花の季節に'
            'なると、旅人はみんな森の花の下で気が変になりました。\n\n\n'
            'なぜなら人間の足の早さは各人各様で、一人が遅れますから、オイ待っ'
            'てくれ、後から必死に叫んでも、みんな気違いで、友達をすてて走りま'
            'す。それで鈴鹿峠の桜の森の花の下を通過したとたんに今迄仲のよかっ'
            'た旅人が仲が悪くなり、相手の友情を信用しなくなります。\n\n'
            'そんなことから旅人も自然に桜の森の下を通らないで、わざわざ遠まわ'
            'りの別の山道を歩くようになり、やがて桜の森は街道を外はずれて人の'
            '子一人通らない山の静寂へとり残されてしまいました。',
        'title': 'Kakuyomu Series 1 Article 1',
        'author': 'Kakuyomu Author 1',
        'source_url': 'https://kakuyomu.jp/series-link-1/article-link-1',
        'source_name': 'Kakuyomu',
        'blog_oid': 1,  # Should match first blog inserted
        'blog_article_order_num': 1,
        'blog_section_name': 'Chapter 1',
        'blog_section_order_num': 1,
        'blog_section_article_order_num': 1,
        'publication_datetime': datetime.fromisoformat('2018-05-28T16:10:16'),
        'last_updated_datetime': datetime.fromisoformat('2018-05-28T16:10:16'),
        'text_hash':
            'ae098c2b815b0bdb3a07ecfbc3df2ec26c65c5c6eba14a68c7de3fbc27e612cb',
        'alnum_count': 662,
        'has_video': False,
        'tags': None,
        'quality_score': 5400,
    },
    {
        'full_text':
            'Kakuyomu Series 1 Article 2\n\n'
            '　けれども山賊は落付いた男で、後悔ということを知らない男ですか'
            'ら、これはおかしいと考えたのです。\nひとつ、来年、考えてやろう。'
            'そう思いました。今年は考える気がしなかったのです。そして、来年、'
            '花がさいたら、そのときじっくり考えようと思いました。\n'
            '毎年そう考えて、もう十何年もたち、今年も亦また、来年になったら考'
            'えてやろうと思って、又、年が暮れてしまいました。\n\n'
            '　そう考えているうちに、始めは一人だった女房がもう七人にもなり、'
            '八人目の女房を又街道から女の亭主の着物と一緒にさらってきました。'
            '女の亭主は殺してきました。\n'
            '山賊は女の亭主を殺す時から、どうも変だと思っていました。いつもと'
            '勝手が違うのです。どこということは分らぬけれども、変てこで、けれ'
            'ども彼の心は物にこだわることに慣れませんので、そのときも格別深く'
            '心にとめませんでした。',
        'title': 'Kakuyomu Series 1 Article 2',
        'author': 'Kakuyomu Author 1',
        'source_url': 'https://kakuyomu.jp/series-link-1/article-link-2',
        'source_name': 'Kakuyomu',
        'blog_oid': 1,  # Should match first blog inserted
        'blog_article_order_num': 2,
        'blog_section_name': 'Chapter 1',
        'blog_section_order_num': 1,
        'blog_section_article_order_num': 2,
        'publication_datetime': datetime.fromisoformat('2019-01-13T01:17:00'),
        'last_updated_datetime': datetime.fromisoformat('2019-01-13T01:17:00'),
        'text_hash':
            '97297e800cc6918a0163b59bdf229a07c63cb87da039190fa8db2b5058e695a5',
        'alnum_count': 352,
        'has_video': False,
        'tags': None,
        'quality_score': 3500,
    },
    {
        'full_text':
            'Kakuyomu Series 1 Article 3\n\n'
            '「いいかい。お前の目に見える山という山、木という木、谷という谷、'
            'その谷からわく雲まで、みんな俺のものなんだぜ」\n'
            '「早く歩いておくれ。私はこんな岩コブだらけの崖の下にいたくないの'
            'だから」',
        'title': 'Kakuyomu Series 1 Article 3',
        'author': 'Kakuyomu Author 1',
        'source_url': 'https://kakuyomu.jp/series-link-1/article-link-3',
        'source_name': 'Kakuyomu',
        'blog_oid': 1,  # Should match first blog inserted
        'blog_article_order_num': 3,
        'blog_section_name': 'Chapter 2',
        'blog_section_order_num': 2,
        'blog_section_article_order_num': 1,
        'publication_datetime': datetime.fromisoformat('2019-08-29T09:21:29'),
        'last_updated_datetime': datetime.fromisoformat('2019-09-05T13:13:24'),
        'text_hash':
            '2cb65de88d1af15a1e49ca2e5a6d84a5c712d6e878df2147f93d6c0d840d9ac9',
        'alnum_count': 104,
        'has_video': False,
        'tags': None,
        'quality_score': 2500,
    },
    {
        'full_text':
            'Kakuyomu Series 2 Article 1\n\n'
            '或曇った冬の日暮である。私は横須賀発上り二等客車の隅に腰を下し'
            'て、ぼんやり発車の笛を待っていた。\n'
            'とうに電燈のついた客車の中には、珍らしく私の外に一人も乗客はいな'
            'かった。外を覗くと、うす暗いプラットフォオムにも、今日は珍しく見'
            '送りの人影さえ跡を絶って、唯、檻に入れられた小犬が一匹、時々悲し'
            'そうに、吠え立てていた。\n\n'
            'これらはその時の私の心もちと、不思議な位似つかわしい景色だっ'
            'た。\n'
            '私の頭の中には云いようのない疲労と倦怠とが、まるで雪曇りの空のよ'
            'うなどんよりした影を落していた。私は外套のポッケットへじっと両手'
            'をつっこんだまま、そこにはいっている夕刊を出して見ようと云う元気'
            'さえ起らなかった。\n　',
        'title': 'Kakuyomu Series 2 Article 1',
        'author': 'Kakuyomu Author 2',
        'source_url': 'https://kakuyomu.jp/series-link-2/article-link-1',
        'source_name': 'Kakuyomu',
        'blog_oid': 2,  # Should match second blog inserted
        'blog_article_order_num': 1,
        'blog_section_name': None,
        'blog_section_order_num': 0,
        'blog_section_article_order_num': 1,
        'publication_datetime': datetime.fromisoformat('2015-02-23T10:19:11'),
        'last_updated_datetime': datetime.fromisoformat('2015-02-23T10:19:11'),
        'text_hash':
            'c7ee027e8c8794b3da782c0366e4c2f27571f5ce16220c412125ff671649d485',
        'alnum_count': 298,
        'has_video': False,
        'tags': None,
        'quality_score': -400,
    },
    {
        'full_text':
            'Kakuyomu Series 2 Article 2\n\n'
            'が、やがて発車の笛が鳴った。私はかすかな心の寛くつろぎを感じなが'
            'ら、後の窓枠へ頭をもたせて、眼の前の停車場がずるずると後ずさりを'
            '始めるのを待つともなく待ちかまえていた。',
        'title': 'Kakuyomu Series 2 Article 2',
        'author': 'Kakuyomu Author 2',
        'source_url': 'https://kakuyomu.jp/series-link-2/article-link-2',
        'source_name': 'Kakuyomu',
        'blog_oid': 2,  # Should match second blog inserted
        'blog_article_order_num': 2,
        'blog_section_name': 'The Real Beginning',
        'blog_section_order_num': 1,
        'blog_section_article_order_num': 1,
        'publication_datetime': datetime.fromisoformat('2018-03-21T03:43:01'),
        'last_updated_datetime': datetime.fromisoformat('2018-03-21T03:43:01'),
        'text_hash':
            '455b7dc21aa9fd730adec86236e2bb43ba273ce3c1965d70a6ba5fb155a1650d',
        'alnum_count': 102,
        'has_video': False,
        'tags': None,
        'quality_score': -2000,
    },
    {
        'full_text':
            'Kakuyomu Series 3 Article 1\n\n'
            '私はその人を常に先生と呼んでいた。だからここでもただ先生と書くだ'
            'けで本名は打ち明けない。\n'
            'これは世間を憚かる遠慮というよりも、その方が私にとって自然だから'
            'である。\n　\n'
            '私はその人の記憶を呼び起すごとに、すぐ「先生」といいたくなる。筆'
            'を執っても心持は同じ事である。\nよそよそしい頭文字などはとても使'
            'う気にならない。\n',
        'title': 'Kakuyomu Series 3 Article 1',
        'author': 'Kakuyomu Author 3',
        'source_url': 'https://kakuyomu.jp/series-link-3/article-link-1',
        'source_name': 'Kakuyomu',
        'blog_oid': 3,  # Should match third blog inserted
        'blog_article_order_num': 1,
        'blog_section_name': None,
        'blog_section_order_num': 0,
        'blog_section_article_order_num': 1,
        'publication_datetime': datetime.fromisoformat('2015-07-11T11:47:00'),
        'last_updated_datetime': datetime.fromisoformat('2017-12-01T20:00:00'),
        'text_hash':
            '9dcd23a4c6a29dd9d2d85b7c573c573d9e55c167fb8384e8af66ae748f1305a2',
        'alnum_count': 164,
        'has_video': False,
        'tags': None,
        'quality_score': -500,
    },
]

# Use deepcopy to avoid modifying any of the contents of the initial docs.
UPDATE_CRAWL_EXPECTED_ARTICLE_DOCS = copy.deepcopy(
    INITIAL_CRAWL_EXPECTED_ARTICLE_DOCS
)
UPDATE_CRAWL_EXPECTED_ARTICLE_DOCS.append({
    'full_text':
        'Kakuyomu Series 3 Article 2\n\n'
        '吾輩は猫である。名前はまだ無い。\n'
        'どこで生れたかとんと見当がつかぬ。何でも薄暗いじめじめした所でニャー'
        'ニャー泣いていた事だけは記憶している。\n\n'
        '吾輩はここで始めて人間というものを見た。しかもあとで聞くとそれは書生'
        'という人間中で一番獰悪な種族であったそうだ。',
    'title': 'Kakuyomu Series 3 Article 2',
    'author': 'Kakuyomu Author 3v2',
    'source_url': 'https://kakuyomu.jp/series-link-3/article-link-2',
    'source_name': 'Kakuyomu',
    'blog_oid': 3,
    'blog_article_order_num': 2,
    'blog_section_name': None,
    'blog_section_order_num': 0,
    'blog_section_article_order_num': 2,
    'publication_datetime': datetime.fromisoformat('2037-09-06T15:30:28'),
    'last_updated_datetime': datetime.fromisoformat('2037-09-06T15:30:28'),
    'text_hash':
        '29a6ffddce745f00cc781fe48eade12f0d3542e27896830dc89d44a7d5f96d42',
    'alnum_count': 142,
    'has_video': False,
    'tags': None,
    'quality_score': 500,
})
UPDATE_CRAWL_EXPECTED_ARTICLE_DOCS.append({
    'full_text':
        'Kakuyomu Series 4 Article 1\n\n'
        'だけど、僕には音楽の素養がないからなア」\n'
        '「音楽なんか、やってるうちに自然と分るようになるわよ。………ねえ、譲治さ'
        'んもやらなきゃ駄目。あたし一人でやったって踊りに行けやしないもの。よ'
        'う、そうして時々二人でダンスに行こうじゃないの。毎日々々内で遊んでば'
        'かりいたってつまりゃしないわ」',
    'title': 'Kakuyomu Series 4 Article 1',
    'author': 'Kakuyomu Author 4',
    'source_url': 'https://kakuyomu.jp/series-link-4/article-link-1',
    'source_name': 'Kakuyomu',
    'blog_oid': 4,
    'blog_article_order_num': 1,
    'blog_section_name': None,
    'blog_section_order_num': 0,
    'blog_section_article_order_num': 1,
    'publication_datetime': datetime.fromisoformat('2037-09-06T09:18:02'),
    'last_updated_datetime': datetime.fromisoformat('2037-09-06T09:18:02'),
    'text_hash':
        '89517ffc51ce622beef8bc430ad29b8394d97a6b79bdf853b36b1dbf47c896b7',
    'alnum_count': 148,
    'has_video': False,
    'tags': None,
    'quality_score': 500,
})


FLI_DOC_EXPECTED_FIELD_COUNT = 20
INITIAL_CRAWL_EXPECTED_FLI_QUERY_DOCS = {
    '自然': [
        {
            'base_form': '自然',
            'base_form_definite_group': '自然',
            'base_form_possible_group': '自然',
            'article_oid': 1,
            'found_positions': [{'index': 629, 'len': 2}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['名詞', '形容動詞語幹'],
                        'conjugated_type': None,
                        'conjugated_form': None
                    },
                    'jmdict_interp_entry_id': None
                }
            ],
            'interp_position_map': None,
            'quality_score_exact_mod': 0,
            'quality_score_definite_mod': 0,
            'quality_score_possible_mod': 0,
            'article_quality_score': 5400,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-05-28T16:10:16'),
            'quality_score_exact': 5400,
            'quality_score_definite': 5400,
            'quality_score_possible': 5400,
        },
        {
            'base_form': '自然',
            'base_form_definite_group': '自然',
            'base_form_possible_group': '自然',
            'article_oid': 6,
            'found_positions': [{'index': 101, 'len': 2}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['名詞', '形容動詞語幹'],
                        'conjugated_type': None,
                        'conjugated_form': None
                    },
                    'jmdict_interp_entry_id': None
                }
            ],
            'interp_position_map': None,
            'quality_score_exact_mod': 0,
            'quality_score_definite_mod': 0,
            'quality_score_possible_mod': 0,
            'article_quality_score': -500,
            'article_last_updated_datetime':
                datetime.fromisoformat('2017-12-01T20:00:00'),
            'quality_score_exact': -500,
            'quality_score_definite': -500,
            'quality_score_possible': -500,
        },
    ],
    '山賊': [
        {
            'base_form': '山賊',
            'base_form_definite_group': '山賊',
            'base_form_possible_group': '山賊',
            'article_oid': 2,
            'found_positions': [
                {'index': 287, 'len': 2},
                {'index': 34, 'len': 2}
            ],
            'found_positions_exact_count': 2,
            'found_positions_definite_count': 2,
            'found_positions_possible_count': 2,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['名詞', '一般'],
                        'conjugated_type': None,
                        'conjugated_form': None
                    },
                    'jmdict_interp_entry_id': None
                }
            ],
            'interp_position_map': None,
            'quality_score_exact_mod': 750,
            'quality_score_definite_mod': 750,
            'quality_score_possible_mod': 750,
            'article_quality_score': 3500,
            'article_last_updated_datetime':
                datetime.fromisoformat('2019-01-13T01:17:00'),
            'quality_score_exact': 4250,
            'quality_score_definite': 4250,
            'quality_score_possible': 4250,
        },
    ],
    'けれども': [
        {
            'base_form': 'けれども',
            'base_form_definite_group': 'けれども',
            'base_form_possible_group': 'けれども',
            'article_oid': 2,
            'found_positions': [
                {'index': 30, 'len': 4},
                {'index': 349, 'len': 4},
                {'index': 339, 'len': 4}
            ],
            'found_positions_exact_count': 3,
            'found_positions_definite_count': 3,
            'found_positions_possible_count': 3,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['接続詞'],
                        'conjugated_type': None,
                        'conjugated_form': None
                    },
                    'jmdict_interp_entry_id': None
                },
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['助詞', '接続助詞'],
                        'conjugated_type': None,
                        'conjugated_form': None
                    },
                    'jmdict_interp_entry_id': None
                }
            ],
            'interp_position_map': {
                '0': [
                    {'index': 30, 'len': 4},
                    {'index': 349, 'len': 4}
                ],
                '1': [{'index': 339, 'len': 4}]
            },
            'quality_score_exact_mod': 1500,
            'quality_score_definite_mod': 1500,
            'quality_score_possible_mod': 1500,
            'article_quality_score': 3500,
            'article_last_updated_datetime':
                datetime.fromisoformat('2019-01-13T01:17:00'),
            'quality_score_exact': 5000,
            'quality_score_definite': 5000,
            'quality_score_possible': 5000,
        }
    ],
    'だから': [
        {
            'base_form': 'だから',
            'base_form_definite_group': 'だから',
            'base_form_possible_group': 'だから',
            'article_oid': 3,
            'found_positions': [{'index': 117, 'len': 3}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
            'possible_interps': [
                {
                    'interp_sources': [3, 4],
                    'mecab_interp': None,
                    'jmdict_interp_entry_id': '1007310'
                }
            ],
            'interp_position_map': None,
            'quality_score_exact_mod': 0,
            'quality_score_definite_mod': 0,
            'quality_score_possible_mod': 0,
            'article_quality_score': 2500,
            'article_last_updated_datetime':
                datetime.fromisoformat('2019-09-05T13:13:24'),
            'quality_score_exact': 2500,
            'quality_score_definite': 2500,
            'quality_score_possible': 2500,
        },
        {
            'base_form': 'だから',
            'base_form_definite_group': 'だから',
            'base_form_possible_group': 'だから',
            'article_oid': 6,
            'found_positions': [
                {'index': 46, 'len': 3},
                {'index': 103, 'len': 3}
            ],
            'found_positions_exact_count': 2,
            'found_positions_definite_count': 2,
            'found_positions_possible_count': 2,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['接続詞'],
                        'conjugated_type': None,
                        'conjugated_form': None
                    },
                    'jmdict_interp_entry_id': None
                },
                {
                    'interp_sources': [3, 4],
                    'mecab_interp': None,
                    'jmdict_interp_entry_id': '1007310'
                }
            ],
            'interp_position_map': {
                '0': [{'index': 46, 'len': 3}],
                '1': [{'index': 103, 'len': 3}]
            },
            'quality_score_exact_mod': 750,
            'quality_score_definite_mod': 750,
            'quality_score_possible_mod': 750,
            'article_quality_score': -500,
            'article_last_updated_datetime':
                datetime.fromisoformat('2017-12-01T20:00:00'),
            'quality_score_exact': 250,
            'quality_score_definite': 250,
            'quality_score_possible': 250,
        },
    ],
    '雪曇り': [
        {
            'base_form': '雪曇り',
            'base_form_definite_group': '雪曇り',
            'base_form_possible_group': '雪曇り',
            'article_oid': 4,
            'found_positions': [{'index': 246, 'len': 3}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
            'possible_interps': [
                {
                    'interp_sources': [2, 3],
                    'mecab_interp': None,
                    'jmdict_interp_entry_id': '2098190'
                }
            ],
            'interp_position_map': None,
            'quality_score_exact_mod': 0,
            'quality_score_definite_mod': 0,
            'quality_score_possible_mod': 0,
            'article_quality_score': -400,
            'article_last_updated_datetime':
                datetime.fromisoformat('2015-02-23T10:19:11'),
            'quality_score_exact': -400,
            'quality_score_definite': -400,
            'quality_score_possible': -400,
        },
    ],
    '窓枠': [
        {
            'base_form': '窓枠',
            'base_form_definite_group': '窓枠',
            'base_form_possible_group': '窓枠',
            'article_oid': 5,
            'found_positions': [{'index': 65, 'len': 2}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
            'possible_interps': [
                {
                    'interp_sources': [2, 3, 4],
                    'mecab_interp': None,
                    'jmdict_interp_entry_id': '1401460'
                }
            ],
            'interp_position_map': None,
            'quality_score_exact_mod': 0,
            'quality_score_definite_mod': 0,
            'quality_score_possible_mod': 0,
            'article_quality_score': -2000,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-03-21T03:43:01'),
            'quality_score_exact': -2000,
            'quality_score_definite': -2000,
            'quality_score_possible': -2000,
        },
    ],
}

# Use deepcopy to avoid modifying any of the contents of the initial docs.
UPDATE_CRAWL_EXPECTED_FLI_QUERY_DOCS = copy.deepcopy(
    INITIAL_CRAWL_EXPECTED_FLI_QUERY_DOCS
)
UPDATE_CRAWL_EXPECTED_FLI_QUERY_DOCS['自然'].append({
    'base_form': '自然',
    'base_form_definite_group': '自然',
    'base_form_possible_group': '自然',
    'article_oid': 8,
    'found_positions': [{'index': 64, 'len': 2}],
    'found_positions_exact_count': 1,
    'found_positions_definite_count': 1,
    'found_positions_possible_count': 1,
    'possible_interps': [
        {
            'interp_sources': [1],
            'mecab_interp': {
                'parts_of_speech': ['名詞', '形容動詞語幹'],
                'conjugated_type': None,
                'conjugated_form': None
            },
            'jmdict_interp_entry_id': None
        }
    ],
    'interp_position_map': None,
    'quality_score_exact_mod': 0,
    'quality_score_definite_mod': 0,
    'quality_score_possible_mod': 0,
    'article_quality_score': 500,
    'article_last_updated_datetime':
        datetime.fromisoformat('2037-09-06T09:18:02'),
    'quality_score_exact': 500,
    'quality_score_definite': 500,
    'quality_score_possible': 500,
})
UPDATE_CRAWL_EXPECTED_FLI_QUERY_DOCS['吾輩'] = [{
    'base_form': '吾輩',
    'base_form_definite_group': '吾輩',
    'base_form_possible_group': '吾輩',
    'article_oid': 7,
    'found_positions': [{'index': 101, 'len': 2}],
    'found_positions_exact_count': 1,
    'found_positions_definite_count': 1,
    'found_positions_possible_count': 1,
    'possible_interps': [
        {
            'interp_sources': [1],
            'mecab_interp': {
                'parts_of_speech': ['名詞', '代名詞', '一般'],
                'conjugated_type': None,
                'conjugated_form': None
            },
            'jmdict_interp_entry_id': None
        }
    ],
    'interp_position_map': None,
    'quality_score_exact_mod': 0,
    'quality_score_definite_mod': 0,
    'quality_score_possible_mod': 0,
    'article_quality_score': 500,
    'article_last_updated_datetime':
        datetime.fromisoformat('2037-09-06T15:30:28'),
    'quality_score_exact': 500,
    'quality_score_definite': 500,
    'quality_score_possible': 500,
}]


class MockRequestsSession(object):
    """Mocks a requests session used by a crawler."""

    _INITIAL_CRAWL_RESPONSE_HTML = {
        'https://kakuyomu.jp/search?genre_name=nonfiction'
        '&order=last_episode_published_at&page=1':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_search_p1_initial.html'
            ),

        'https://kakuyomu.jp/search?genre_name=nonfiction'
        '&order=last_episode_published_at&page=2':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_search_p2_initial.html'
            ),

        'https://kakuyomu.jp/series-link-1':
            os.path.join(TEST_DIR, 'test_html/kakuyomu/series_1_initial.html'),

        'https://kakuyomu.jp/series-link-1/article-link-1':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_1_article_1.html'
            ),

        'https://kakuyomu.jp/series-link-1/article-link-1/episode_sidebar':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_1_article_1_sidebar.html'
            ),

        'https://kakuyomu.jp/series-link-1/article-link-2':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_1_article_2.html'
            ),

        'https://kakuyomu.jp/series-link-1/article-link-2/episode_sidebar':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_1_article_2_sidebar.html'
            ),

        'https://kakuyomu.jp/series-link-1/article-link-3':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_1_article_3.html'
            ),

        'https://kakuyomu.jp/series-link-1/article-link-3/episode_sidebar':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_1_article_3_sidebar.html'
            ),

        'https://kakuyomu.jp/series-link-2':
            os.path.join(TEST_DIR, 'test_html/kakuyomu/series_2.html'),

        'https://kakuyomu.jp/series-link-2/article-link-1':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_2_article_1.html'
            ),

        'https://kakuyomu.jp/series-link-2/article-link-1/episode_sidebar':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_2_article_1_sidebar.html'
            ),

        'https://kakuyomu.jp/series-link-2/article-link-2':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_2_article_2.html'
            ),

        'https://kakuyomu.jp/series-link-2/article-link-2/episode_sidebar':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_2_article_2_sidebar.html'
            ),

        'https://kakuyomu.jp/series-link-3':
            os.path.join(TEST_DIR, 'test_html/kakuyomu/series_3_initial.html'),

        'https://kakuyomu.jp/series-link-3/article-link-1':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_3_article_1.html'
            ),

        'https://kakuyomu.jp/series-link-3/article-link-1/episode_sidebar':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_3_article_1_sidebar.html'
            ),
    }

    _UPDATE_CRAWL_RESPONSE_HTML = {
        'https://kakuyomu.jp/search?genre_name=nonfiction'
        '&order=last_episode_published_at&page=1':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_search_p1_update.html'
            ),

        'https://kakuyomu.jp/search?genre_name=nonfiction'
        '&order=last_episode_published_at&page=2':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_search_p2_update.html'
            ),

        'https://kakuyomu.jp/series-link-1':
            os.path.join(TEST_DIR, 'test_html/kakuyomu/series_1_update.html'),

        'https://kakuyomu.jp/series-link-3':
            os.path.join(TEST_DIR, 'test_html/kakuyomu/series_3_update.html'),

        'https://kakuyomu.jp/series-link-3/article-link-2':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_3_article_2.html'
            ),

        'https://kakuyomu.jp/series-link-3/article-link-2/episode_sidebar':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_3_article_2_sidebar.html'
            ),

        'https://kakuyomu.jp/series-link-4':
            os.path.join(TEST_DIR, 'test_html/kakuyomu/series_4.html'),

        'https://kakuyomu.jp/series-link-4/article-link-1':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_4_article_1.html'
            ),

        'https://kakuyomu.jp/series-link-4/article-link-1/episode_sidebar':
            os.path.join(
                TEST_DIR,
                'test_html/kakuyomu/series_4_article_1_sidebar.html'
            ),
    }

    def __init__(self, is_update_crawl: bool) -> None:
        """Specifies which set of responses should be given by the mock.

        Args:
            is_update_crawl: If False, the mock will give responses for the
                sites in their initial test state. If True, the mock will give
                responses for the sites as if they had received a partial
                update from the initial test state.
        """
        self._response_html = self._INITIAL_CRAWL_RESPONSE_HTML
        if is_update_crawl:
            self._response_html.update(self._UPDATE_CRAWL_RESPONSE_HTML)

    def get(self, url: str, timeout: int) -> requests.Response:
        """Returns a response with the test HTML for the given url."""
        with open(self._response_html[url], 'r') as html_file:
            html_content = html_file.read().encode('utf-8')

        mock_response = Mock(
            requests.Response,
            content=html_content,
            status_code=200,
            raise_for_status=lambda: None
        )
        return mock_response

    def close(self) -> None:
        """Stub for Session close function."""
        pass


def assert_doc_field_value(
    field: str, value: Any, expected_doc: _Document,
    oid_map: Dict[str, List[ObjectId]]
) -> None:
    """Asserts a given field value pair for a doc matches an expected doc.

    Args:
        field: A field from a MongoDB doc.
        value: The value for that field from the doc.
        expected_doc: The expected document that the field value pair should
            match.
        oid_map: A mapping from a documente type (e.g. blog) to the list of
            ObjectIds for that document type in the db in order of insertion
            into the db. Used to check that foreign key references are pointing
            to the correct document.
    """
    if field.endswith('_oid'):
        # The value for foreign key references in the expected docs is an int
        # (or None) that specifies which foreign doc this one should map to
        # based on the foreign doc insertion order (with 1 being the first
        # inserted)
        if expected_doc[field] is None:
            assert value is None
        else:
            assert value == oid_map[field[:-4]][expected_doc[field] - 1]
    elif field in expected_doc:
        assert value == expected_doc[field]
    elif field == '_id':
        # _id will change every test run, so we can't check it against a static
        # value. Instead, just check that it's an ObjectId 12 bytes long as
        # expected.
        assert isinstance(value, ObjectId)
        assert len(value.binary) == 12
    elif field == 'last_crawled_datetime':
        # last_crawled_datetime will also be different every test run, so just
        # check that the time is within 5 minutes of now.
        assert (datetime.utcnow() - value).seconds < (60 * 5)
    elif field == 'myaku_version_info':
        assert len(value) == VERSION_DOC_EXPECTED_FIELD_COUNT
        for key, version in value.items():
            assert VERSION_DOC_REGEXES[key].match(version) is not None
    else:
        assert False, f'Unexpected field: {field}:{value}'


def assert_blog_db_data(
    db: CrawlDb, blog_expected_docs: List[_Document],
    oid_map: DefaultDict[str, List[ObjectId]]
) -> None:
    """Asserts blog data in db matches the given documents.

    Args:
        db: CrawlDb client to use to access the db data.
        blog_expected:docs: The expected blog document data to be in the db.
            Should be sorted in the order of the expected insertion order of
            the blog documents into the db.
        oid_map: A mapping from a documente type (e.g. blog) to the list of
            ObjectIds for that document type in the db in order of insertion
            into the db.

            Will be updated with the blog ObjectIds in the function.
    """
    blog_db_docs = db._blog_collection.find({}).sort(
        '_id', pymongo.ASCENDING
    )
    blog_doc_zip = zip(blog_db_docs, blog_expected_docs)
    for blog_doc, expected_blog_doc in blog_doc_zip:
        assert len(blog_doc) == BLOG_DOC_EXPECTED_FIELD_COUNT
        assert '_id' in blog_doc
        oid_map['blog'].append(blog_doc['_id'])

        for field, value in blog_doc.items():
            assert_doc_field_value(field, value, expected_blog_doc, oid_map)


def assert_article_db_data(
    db: CrawlDb, article_expected_docs: List[_Document],
    oid_map: DefaultDict[str, List[ObjectId]]
) -> None:
    """Asserts article data in db matches the given documents.

    Args:
        db: CrawlDb client to use to access the db data.
        article_expected_docs: The expected article document data to be in the
            db. Should be sorted in the order of the expected insertion order
            of the article documents into the db.
        oid_map: A mapping from a documente type (e.g. blog) to the list of
            ObjectIds for that document type in the db in order of insertion
            into the db. Must have the blog ObjectId mappings set before
            passing to this function.

            Will be updated with the article ObjectIds in the function.
    """
    article_db_docs = db._article_collection.find({}).sort(
        '_id', pymongo.ASCENDING
    )
    article_doc_zip = zip(article_db_docs, article_expected_docs)
    for article_doc, expected_article_doc in article_doc_zip:
        assert len(article_doc) == ARTICLE_DOC_EXPECTED_FIELD_COUNT
        assert '_id' in article_doc
        oid_map['article'].append(article_doc['_id'])

        for field, value in article_doc.items():
            assert_doc_field_value(field, value, expected_article_doc, oid_map)


def assert_found_lexical_item_db_data(
    db: CrawlDb, fli_query_expected_docs: Dict[str, List[_Document]],
    oid_map: DefaultDict[str, List[ObjectId]]
) -> None:
    """Asserts found lexical item data in db matches the given documents.

    Args:
        db: CrawlDb client to use to access the db data.
        fli_query_expected_docs: A dictionary mapping base_form queries to the
            expected found lexical item document data to be in the db for that
            query.

            The document lists should be sorted in the order of the expected
            insertion order of the found lexical item documents into the db.
        oid_map: A mapping from a documente type (e.g. blog) to the list of
            ObjectIds for that document type in the db in order of insertion
            into the db. Must have the article ObjectId mappings set before
            passing to this function.

            Will be updated with the found lexical item ObjectIds in the
            function.
    """
    for base_form, expected_fli_docs in fli_query_expected_docs.items():
        cursor = db._found_lexical_item_collection.find(
            {'base_form': base_form}
        )
        fli_db_docs = cursor.sort('_id', pymongo.ASCENDING)
        fli_doc_zip = zip(fli_db_docs, expected_fli_docs)
        for fli_doc, expected_fli_doc in fli_doc_zip:
            assert len(fli_doc) == FLI_DOC_EXPECTED_FIELD_COUNT
            assert '_id' in fli_doc
            oid_map['found_lexical_item'].append(fli_doc['_id'])

            for field, value in fli_doc.items():
                assert_doc_field_value(field, value, expected_fli_doc, oid_map)


def assert_initial_crawl_db_data() -> None:
    """Asserts the db data matches the expected initial crawl data."""
    oid_map: DefaultDict[str, List[ObjectId]] = defaultdict(list)
    with CrawlDb() as db:
        assert_blog_db_data(db, INITIAL_CRAWL_EXPECTED_BLOG_DOCS, oid_map)
        assert_article_db_data(
            db, INITIAL_CRAWL_EXPECTED_ARTICLE_DOCS, oid_map
        )
        assert_found_lexical_item_db_data(
            db, INITIAL_CRAWL_EXPECTED_FLI_QUERY_DOCS, oid_map
        )


def assert_update_crawl_db_data() -> None:
    """Asserts the db data matches the expected update crawl data."""
    oid_map: DefaultDict[str, List[ObjectId]] = defaultdict(list)
    with CrawlDb() as db:
        assert_blog_db_data(db, UPDATE_CRAWL_EXPECTED_BLOG_DOCS, oid_map)
        assert_article_db_data(
            db, UPDATE_CRAWL_EXPECTED_ARTICLE_DOCS, oid_map
        )
        assert_found_lexical_item_db_data(
            db, UPDATE_CRAWL_EXPECTED_FLI_QUERY_DOCS, oid_map
        )


def assert_search_results(
    search_results: List[JpnArticleSearchResult], fli_docs: List[_Document]
) -> None:
    """Asserts search results match a list of found lexical item documents."""
    assert len(search_results) == len(fli_docs)
    for search_result, fli_doc in zip(search_results, fli_docs):
        assert search_result.article.database_id == str(fli_doc['article_oid'])

        assert (len(search_result.found_positions)
                == len(fli_doc['found_positions']))
        found_positions_zip = zip(
            search_result.found_positions, fli_doc['found_positions']
        )
        for result_pos, fli_pos_doc in found_positions_zip:
            fli_pos = ArticleTextPosition(
                fli_pos_doc['index'], fli_pos_doc['len']
            )
            assert result_pos == fli_pos


def assert_first_page_cache_query_keys(
    cache: FirstPageCache, db: CrawlDb
) -> Set[ObjectId]:
    """Asserts first page cache query keys are consistent with db data.

    Args:
        cache: First page cache whose query keys to check.
        db: Crawl db client to use to get the db data to check the query keys
            against.

    Returns:
        A set of all of the article object IDs that were referenced in the
        first page search results for at least one query in the cache.
    """
    article_oids: Set[ObjectId] = set()

    base_form_cursor = db._found_lexical_item_collection.aggregate([
        {'$group': {'_id': '$base_form'}}
    ])
    for doc in base_form_cursor:
        search_results = cache.get(doc['_id'])
        assert search_results is not None

        fli_cursor = db._found_lexical_item_collection.find(
            {'base_form': doc['_id']}
        )
        ranked_fli_docs = sorted(
            fli_cursor, key=itemgetter('quality_score_exact'), reverse=True
        )[:CrawlDb.SEARCH_RESULTS_PAGE_SIZE]
        article_oids |= {d['article_oid'] for d in ranked_fli_docs}

        assert_search_results(search_results, ranked_fli_docs)

    # Make sure every query key maps to something in the crawl db
    for query_key in cache._redis_client.keys('query:*'):
        assert db._found_lexical_item_collection.find_one(
            {'base_form': query_key[6:].decode()}
        ) is not None

    return article_oids


def assert_first_page_cache_article_keys(
    cache: FirstPageCache, db: CrawlDb, expected_article_oids: Set[ObjectId]
) -> None:
    """Asserts first page cache article keys are consistent with db data.

    Args:
        cache: First page cache whose query keys to check.
        db: Crawl db client to use to get the db data to check the query keys
            against.
        expected_article_oids: Set of the article object IDs expected to have
            keys with article data in the first page cache.
    """
    for doc in db._article_collection.find({}):
        cached_article = cache._get_article(doc['_id'])
        if doc['_id'] not in expected_article_oids:
            assert cached_article is None
            continue
        else:
            assert cached_article is not None

        for attr in ARTICLE_CACHED_ATTRS:
            assert getattr(cached_article, attr) == doc[attr]

    # Make sure every article key maps to something in the crawl db
    for article_key in cache._redis_client.keys('article:*'):
        assert db._article_collection.find_one(
            {'_id': ObjectId(article_key[8:].decode())}
        ) is not None


def assert_first_page_cache_data() -> None:
    """Asserts first page cache data is consistent with crawl db data."""
    cache = FirstPageCache()
    with CrawlDb() as db:
        expected_article_oids = assert_first_page_cache_query_keys(cache, db)
        assert_first_page_cache_article_keys(cache, db, expected_article_oids)


def test_crawl_end_to_end(mocker, monkeypatch) -> None:
    """Test a series of full end-to-end crawling sessions.

    Mocks out the web requests done by the crawlers so that they get test HTML
    pages in response, but other than that, runs through the full crawl
    scenario with no other parts mocked out.
    """
    monkeypatch.setenv(utils._NO_RATE_LIMIT_ENV_VAR, '1')
    monkeypatch.setenv(kakuyomu._PAGES_TO_CRAWL_ENV_VAR, '2')
    mocker.patch('sys.argv', ['pytest', 'Kakuyomu'])

    # Use small search result page size to ensure not all data crawled gets
    # stored in the first page cache
    mocker.patch(
        'myaku.datastore.database.CrawlDb.SEARCH_RESULTS_PAGE_SIZE', 2
    )

    mocker.patch('requests.Session', lambda: MockRequestsSession(False))
    run_crawl.main()
    assert_initial_crawl_db_data()
    assert_first_page_cache_data()

    mocker.patch('requests.Session', lambda: MockRequestsSession(True))
    run_crawl.main()
    assert_update_crawl_db_data()
    assert_first_page_cache_data()
