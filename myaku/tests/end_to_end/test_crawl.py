"""End-to-end test for the Myaku crawler.

Uses a set of mock HTML pages for the source sites supported by Myaku to test
running end-to-end crawl sessions with the Myaku crawler.

Thoroughly checks many aspects of the crawl during the test including:
    - All targeted data is successfully parsed out of all types of source
        pages.
    - All crawled data is correctly stored in the crawl database.
    - The search results first page cache is correctly set with the crawled
        data.
    - No unexpected network requests are attempted by the crawler.
"""

import collections
import copy
import enum
import os
import re
from datetime import datetime
from operator import itemgetter
from typing import Any, Counter, Dict, List, Set
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
        'blog_oid': 'Kakuyomu Series 1',
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
        'blog_oid': 'Kakuyomu Series 1',
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
        'blog_oid': 'Kakuyomu Series 1',
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
        'blog_oid': 'Kakuyomu Series 2',
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
        'blog_oid': 'Kakuyomu Series 2',
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
        'blog_oid': 'Kakuyomu Series 3',
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
    {
        'full_text':
            'Asahi Article 3 (News, Normal)\n\n'
            '　この戦争中、文士は未亡人の恋愛を書くことを禁じられていた。\n\n'
            '　戦争未亡人を挑発堕落させてはいけないという軍人政治家の魂胆で彼'
            '女達に使徒の余生を送らせようと欲していたのであろう。\n\n'
            '　軍人達の悪徳に対する理解力は敏感であって、彼等は女心の変り易さ'
            'を知らなかったわけではなく、知りすぎていたので、こういう禁止項目'
            'を案出に及んだまでであった。',
        'title': 'Asahi Article 3 (News, Normal)',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/3.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-07-15T02:00:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-07-15T02:00:00'),
        'text_hash':
            '4ad18c786f692eb080670703d655d49a27014cf190b04ce08ecf739aee4d9ed1',
        'alnum_count': 179,
        'has_video': False,
        'tags': ['Tag 1', 'Tag 2', 'Tag 3', 'Tag 4'],
        'quality_score': -1000,
    },
    {
        'full_text':
            'Asahi Article 5 (News, Normal, Video)\n\n'
            '昔、四十七士の助命を排して処刑を断行した理由の一つは、彼等が生き'
            'ながらえて生き恥をさらし折角の名を汚す者が現れてはいけないという'
            '老婆心であったそうな。\n\n'
            '現代の法律にこんな人情は存在しない。\n\n'
            'けれども人の心情には多分にこの傾向が残っており、美しいものを美し'
            'いままで終らせたいということは一般的な心情の一つのようだ。',
        'title': 'Asahi Article 5 (News, Normal, Video)',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/5.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-07-14T23:30:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-07-14T23:30:00'),
        'text_hash':
            '6e255ea8731eda163dcbf2dc536657a77c100541f85c4892aaf1b7ce6732f46c',
        'alnum_count': 176,
        'has_video': True,
        'tags': ['Tag 2', 'Tag 4', 'Tag 5'],
        'quality_score': 0,
    },
    {
        'full_text':
            'Asahi Article 8 (Column, Normal)\n\n'
            'けれども私は偉大な破壊を愛していた。運命に従順な人間の姿は奇妙に'
            '美しいものである。\n\n'
            '麹町のあらゆる大邸宅が嘘のように消え失せて余燼をたてており、上品'
            'な父と娘がたった一つの赤皮のトランクをはさんで濠端の緑草の上に'
            '坐っている。\n\n'
            '見出し\n\n'
            '片側に余燼をあげる茫々たる廃墟がなければ、平和なピクニックと全く'
            '変るところがない。',
        'title': 'Asahi Article 8 (Column, Normal)',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/8.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-07-15T09:11:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-07-15T09:11:00'),
        'text_hash':
            '3336d6795dd690824cd1b42901dfc1a2ec9b3752da0dfb46fb47f2f43c59ab1d',
        'alnum_count': 173,
        'has_video': False,
        'tags': ['Tag 4', 'Tag 8', 'Tag 2'],
        'quality_score': -1000,
    },
    {
        'full_text':
            'Asahi Article 14 (Column, Normal, Video)\n\n'
            '見出し\n\n'
            '私は血を見ることが非常に嫌いで、いつか私の眼前で自動車が衝突した'
            'とき、私はクルリと振向いて逃げだしていた。\n\n'
            'けれども、私は偉大な破壊が好きであった。私は爆弾や焼夷弾に戦きな'
            'がら、狂暴な破壊に劇しく亢奮していたが、それにも拘らず、このとき'
            'ほど人間を愛しなつかしんでいた時はないような思いがする。',
        'title': 'Asahi Article 14 (Column, Normal, Video)',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/14.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-07-14T19:45:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-07-14T19:45:00'),
        'text_hash':
            '5500ceb0a076e11039ae8f94fb5f80aec0e465070c413a4797b6293ed335613c',
        'alnum_count': 170,
        'has_video': True,
        'tags': ['Tag 4'],
        'quality_score': 0,
    },
    {
        'full_text':
            'Asahi Editorial 15\n\n'
            '伝統とは何か？　国民性とは何か？　日本人には必然の性格があって、'
            'どうしても和服を発明し、それを着なければならないような決定的な素'
            '因があるのだろうか。',
        'title': 'Asahi Editorial 15',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/15.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-07-14T20:00:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-07-14T20:00:00'),
        'text_hash':
            '42e3c8b557f58a54d1e6cdba15c3cdfa749c9c8cf0de36f10825a8eea6afeafb',
        'alnum_count': 83,
        'has_video': False,
        'tags': None,
        'quality_score': -2500,
    },
    {
        'full_text':
            'Asahi Editorial 16\n\n'
            '　講談を読むと、我々の祖先は甚だ復讐心が強く、乞食となり、草の根'
            'を分けて仇を探し廻っている。\n\n'
            '　そのサムライが終ってからまだ七八十年しか経たないのに、これはも'
            'う、我々にとっては夢の中の物語である。',
        'title': 'Asahi Editorial 16',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/16.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-07-13T20:00:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-07-13T20:00:00'),
        'text_hash':
            '496288f7f1de0129105d0c2970132b375dc5d979fee502fc3d4b61d003ca5b95',
        'alnum_count': 104,
        'has_video': False,
        'tags': None,
        'quality_score': -1000,
    },
    {
        'full_text':
            'Asahi Editorial 17\n\n'
            '　このような眼は日本人には無いのである。\n\n'
            '僕は一度もこのような眼を日本人に見たことはなかった。その後も特に'
            '意識して注意したが、一度も出会ったことがない。\n\n'
            'つまり、このような憎悪が、日本人には無いのである。『三国志』に於'
            'ける憎悪、『チャタレイ夫人の恋人』に於ける憎悪、血に飢え、八ツ裂'
            'きにしても尚あき足りぬという憎しみは日本人には殆んどない。\n\n'
            '昨日の敵は今日の友という甘さが、むしろ日本人に共有の感情だ。\n\n'
            '凡そ仇討にふさわしくない自分達であることを、恐らく多くの日本人が'
            '痛感しているに相違ない。\n\n'
            '長年月にわたって徹底的に憎み通すことすら不可能にちかく、せいぜい'
            '「食いつきそうな」眼付ぐらいが限界なのである。',
        'title': 'Asahi Editorial 17',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/17.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-07-13T20:00:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-07-13T20:00:00'),
        'text_hash':
            '0c3f7d55dd5c3fa8e9f9d7afd97dc10c3cad26940c60c596f3c87cd5f5d811dc',
        'alnum_count': 289,
        'has_video': False,
        'tags': None,
        'quality_score': 500,
    },
    {
        'full_text':
            'Asahi Editorial 18\n\n'
            '伝統とか、国民性とよばれるものにも、時として、このような欺瞞が隠'
            'されている。\n\n'
            '凡そ自分の性情にうらはらな習慣や伝統を、恰も生来の希願のように背'
            '負わなければならないのである。だから、昔日本に行われていたこと'
            'が、昔行われていたために、日本本来のものだということは成立たな'
            'い。',
        'title': 'Asahi Editorial 18',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/18.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-06-29T20:00:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-06-29T20:00:00'),
        'text_hash':
            'f1f13023c3705a021fccd9848145fd7e7af4019629a98a3f61e6a7fa7a748409',
        'alnum_count': 140,
        'has_video': False,
        'tags': None,
        'quality_score': -1000,
    },
    {
        'full_text':
            'Asahi Editorial 19\n\n'
            '外国に於て行われ、日本には行われていなかった習慣が、実は日本人に'
            '最もふさわしいことも有り得るし、日本に於て行われて、外国には行わ'
            'れなかった習慣が、実は外国人にふさわしいことも有り得るのだ。模倣'
            'ではなく、発見だ。',
        'title': 'Asahi Editorial 19',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/19.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-05-30T20:00:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-05-30T20:00:00'),
        'text_hash':
            '30fe029e460f99990fa41bcf987000bf5514fbcbec4f13f9d85200274ddbab09',
        'alnum_count': 113,
        'has_video': False,
        'tags': None,
        'quality_score': -1000,
    },
    {
        'full_text':
            'Asahi Editorial 20\n\n'
            'ゲーテがシェクスピアの作品に暗示を受けて自分の傑作を書きあげたよ'
            'うに、個性を尊重する芸術に於てすら、模倣から発見への過程は最もし'
            'ばしば行われる。インスピレーションは、多く模倣の精神から出発し'
            'て、発見によって結実する。',
        'title': 'Asahi Editorial 20',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/20.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-05-30T20:00:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-05-30T20:00:00'),
        'text_hash':
            'd0c513665c36adadf52baf9babde306f028f66f6d44d3076615b2b5321af30a6',
        'alnum_count': 118,
        'has_video': False,
        'tags': None,
        'quality_score': -1000,
    },
]

# Use deepcopy to avoid modifying any of the contents of the initial docs.
UPDATE_CRAWL_EXPECTED_ARTICLE_DOCS = copy.deepcopy(
    INITIAL_CRAWL_EXPECTED_ARTICLE_DOCS
)
UPDATE_CRAWL_EXPECTED_ARTICLE_DOCS.extend([
    {
        'full_text':
            'Kakuyomu Series 3 Article 2\n\n'
            '吾輩は猫である。名前はまだ無い。\n'
            'どこで生れたかとんと見当がつかぬ。何でも薄暗いじめじめした所で'
            'ニャーニャー泣いていた事だけは記憶している。\n\n'
            '吾輩はここで始めて人間というものを見た。しかもあとで聞くとそれは'
            '書生という人間中で一番獰悪な種族であったそうだ。',
        'title': 'Kakuyomu Series 3 Article 2',
        'author': 'Kakuyomu Author 3v2',
        'source_url': 'https://kakuyomu.jp/series-link-3/article-link-2',
        'source_name': 'Kakuyomu',
        'blog_oid': 'Kakuyomu Series 3',
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
    },
    {
        'full_text':
            'Kakuyomu Series 4 Article 1\n\n'
            'だけど、僕には音楽の素養がないからなア」\n'
            '「音楽なんか、やってるうちに自然と分るようになるわよ。………ねえ、譲'
            '治さんもやらなきゃ駄目。あたし一人でやったって踊りに行けやしない'
            'もの。よう、そうして時々二人でダンスに行こうじゃないの。毎日々々'
            '内で遊んでばかりいたってつまりゃしないわ」',
        'title': 'Kakuyomu Series 4 Article 1',
        'author': 'Kakuyomu Author 4',
        'source_url': 'https://kakuyomu.jp/series-link-4/article-link-1',
        'source_name': 'Kakuyomu',
        'blog_oid': 'Kakuyomu Series 4',
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
    },
    {
        'full_text':
            'Asahi Article 21 (News, Normal)\n\n'
            '　戦争に負けたから堕ちるのではないのだ。人間だから堕ちるのであ'
            'り、生きているから堕ちるだけだ。\n\n'
            '　だが人間は永遠に堕ちぬくことはできないだろう。\n\n'
            '　なぜなら人間の心は苦難に対して鋼鉄の如くでは有り得ない。人間は'
            '可憐であり脆弱であり、それ故愚かなものであるが、堕ちぬくためには'
            '弱すぎる。',
        'title': 'Asahi Article 21 (News, Normal)',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/21.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-08-15T04:10:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-08-15T04:10:00'),
        'text_hash':
            'd14eb96ab7e43ce11df37a4bd7cc4ec4becb37be3b48404040e3bb44f5cada87',
        'alnum_count': 153,
        'has_video': False,
        'tags': ['Tag 3', 'Tag 4'],
        'quality_score': -1000,
    },
    {
        'full_text':
            'Asahi Article 26 (Column, Normal)\n\n'
            'だが、堕落ということの驚くべき平凡さや平凡な当然さに比べると、あ'
            'のすさまじい偉大な破壊の愛情や運命に従順な人間達の美しさも、泡沫'
            'のような虚しい幻影にすぎないという気持がする。',
        'title': 'Asahi Article 26 (Column, Normal)',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/26.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-08-15T07:49:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-08-15T07:49:00'),
        'text_hash':
            'e8ea2623e449ff8020174ef80e3c71814536f70b663eab031c63f5f269b507c8',
        'alnum_count': 109,
        'has_video': False,
        'tags': ['Tag 8', 'Tag 2', 'Tag 7'],
        'quality_score': -1000,
    },
    {
        'full_text':
            'Asahi Editorial 27\n\n'
            'キモノとは何ぞや？　洋服との交流が千年ばかり遅かっただけだ。\n\n'
            'そうして、限られた手法以外に、新らたな発明を暗示する別の手法が与'
            'えられなかっただけである。\n\n'
            '日本人の貧弱な体躯が特にキモノを生みだしたのではない。日本人には'
            'キモノのみが美しいわけでもない。外国の恰幅のよい男達の和服姿が、'
            '我々よりも立派に見えるに極っている。',
        'title': 'Asahi Editorial 27',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/27.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-08-14T20:00:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-08-14T20:00:00'),
        'text_hash':
            '8dedbe687b0a1971943a63a80f49abe608a333492382c21f09356102e4cc7ad4',
        'alnum_count': 163,
        'has_video': False,
        'tags': None,
        'quality_score': -1000,
    },
    {
        'full_text':
            'Asahi Editorial 28\n\n'
            '見たところのスマートだけでは、真に美なる物とはなり得ない。すべて'
            'は、実質の問題だ。\n\n'
            '美しさのための美しさは素直でなく、結局、本当の物ではないのであ'
            'る。要するに、空虚なのだ。そうして、空虚なものは、その真実のもの'
            'によって人を打つことは決してなく、詮ずるところ、有っても無くても'
            '構わない代物である。',
        'title': 'Asahi Editorial 28',
        'author': None,
        'source_url': 'https://www.asahi.com/articles/28.html',
        'source_name': 'Asahi Shinbun',
        'blog_oid': None,
        'blog_article_order_num': None,
        'blog_section_name': None,
        'blog_section_order_num': None,
        'blog_section_article_order_num': None,
        'publication_datetime': datetime.fromisoformat('2018-08-14T20:00:00'),
        'last_updated_datetime': datetime.fromisoformat('2018-08-14T20:00:00'),
        'text_hash':
            'a7c18c4efe2ea932e958e46e5709a204911b55c7c2220b85e66ecd0826268235',
        'alnum_count': 148,
        'has_video': False,
        'tags': None,
        'quality_score': -1000,
    },
])


CRAWL_SKIP_DOC_EXPECTED_FIELD_COUNT = 4
INITIAL_CRAWL_EXPECTED_CRAWL_SKIP_DOCS = [
    {
        'source_url': 'https://www.asahi.com/articles/6.html',
        'source_name': 'Asahi Shinbun',
    },
    {
        'source_url': 'https://www.asahi.com/articles/11.html',
        'source_name': 'Asahi Shinbun',
    },
]
UPDATE_CRAWL_EXPECTED_CRAWL_SKIP_DOCS = INITIAL_CRAWL_EXPECTED_CRAWL_SKIP_DOCS


FLI_DOC_EXPECTED_FIELD_COUNT = 20
INITIAL_CRAWL_EXPECTED_FLI_QUERY_DOCS = {
    '自然': [
        {
            'base_form': '自然',
            'base_form_definite_group': '自然',
            'base_form_possible_group': '自然',
            'article_oid': 'Kakuyomu Series 1 Article 1',
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
            'article_oid': 'Kakuyomu Series 3 Article 1',
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
            'article_oid': 'Kakuyomu Series 1 Article 2',
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
            'article_oid': 'Kakuyomu Series 1 Article 2',
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
        },
        {
            'base_form': 'けれども',
            'base_form_definite_group': 'けれども',
            'base_form_possible_group': 'けれども',
            'article_oid': 'Asahi Article 5 (News, Normal, Video)',
            'found_positions': [{'index': 136, 'len': 4}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['接続詞'],
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
            'article_quality_score': 0,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-07-14T23:30:00'),
            'quality_score_exact': 0,
            'quality_score_definite': 0,
            'quality_score_possible': 0,
        },
        {
            'base_form': 'けれども',
            'base_form_definite_group': 'けれども',
            'base_form_possible_group': 'けれども',
            'article_oid': 'Asahi Article 8 (Column, Normal)',
            'found_positions': [{'index': 34, 'len': 4}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['接続詞'],
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
            'article_quality_score': -1000,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-07-15T09:11:00'),
            'quality_score_exact': -1000,
            'quality_score_definite': -1000,
            'quality_score_possible': -1000,
        },
        {
            'base_form': 'けれども',
            'base_form_definite_group': 'けれども',
            'base_form_possible_group': 'けれども',
            'article_oid': 'Asahi Article 14 (Column, Normal, Video)',
            'found_positions': [{'index': 102, 'len': 4}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['接続詞'],
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
            'article_quality_score': 0,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-07-14T19:45:00'),
            'quality_score_exact': 0,
            'quality_score_definite': 0,
            'quality_score_possible': 0,
        },
    ],
    'だから': [
        {
            'base_form': 'だから',
            'base_form_definite_group': 'だから',
            'base_form_possible_group': 'だから',
            'article_oid': 'Kakuyomu Series 1 Article 3',
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
            'article_oid': 'Kakuyomu Series 3 Article 1',
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
        {
            'base_form': 'だから',
            'base_form_definite_group': 'だから',
            'base_form_possible_group': 'だから',
            'article_oid': 'Asahi Editorial 18',
            'found_positions': [{'index': 107, 'len': 3}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['接続詞'],
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
            'article_quality_score': -1000,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-06-29T20:00:00'),
            'quality_score_exact': -1000,
            'quality_score_definite': -1000,
            'quality_score_possible': -1000,
        },
    ],
    '雪曇り': [
        {
            'base_form': '雪曇り',
            'base_form_definite_group': '雪曇り',
            'base_form_possible_group': '雪曇り',
            'article_oid': 'Kakuyomu Series 2 Article 1',
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
            'article_oid': 'Kakuyomu Series 2 Article 2',
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
    '未亡人': [
        {
            'base_form': '未亡人',
            'base_form_definite_group': '未亡人',
            'base_form_possible_group': '未亡人',
            'article_oid': 'Asahi Article 3 (News, Normal)',
            'found_positions': [
                {'index': 42, 'len': 3},
                {'index': 67, 'len': 3}
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
            'article_quality_score': -1000,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-07-15T02:00:00'),
            'quality_score_exact': -250,
            'quality_score_definite': -250,
            'quality_score_possible': -250,
        },
    ],
    '必然': [
        {
            'base_form': '必然',
            'base_form_definite_group': '必然',
            'base_form_possible_group': '必然',
            'article_oid': 'Asahi Editorial 15',
            'found_positions': [{'index': 42, 'len': 2}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
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
            'quality_score_exact_mod': 0,
            'quality_score_definite_mod': 0,
            'quality_score_possible_mod': 0,
            'article_quality_score': -2500,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-07-14T20:00:00'),
            'quality_score_exact': -2500,
            'quality_score_definite': -2500,
            'quality_score_possible': -2500,
        },
    ],
    '復讐心': [
        {
            'base_form': '復讐心',
            'base_form_definite_group': '復讐心',
            'base_form_possible_group': '復讐心',
            'article_oid': 'Asahi Editorial 16',
            'found_positions': [{'index': 36, 'len': 3}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['名詞', '固有名詞', '一般'],
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
            'article_quality_score': -1000,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-07-13T20:00:00'),
            'quality_score_exact': -1000,
            'quality_score_definite': -1000,
            'quality_score_possible': -1000,
        },
    ],
    '憎悪': [
        {
            'base_form': '憎悪',
            'base_form_definite_group': '憎悪',
            'base_form_possible_group': '憎悪',
            'article_oid': 'Asahi Editorial 17',
            'found_positions': [
                {'index': 108, 'len': 2},
                {'index': 133, 'len': 2},
                {'index': 152, 'len': 2}
            ],
            'found_positions_exact_count': 3,
            'found_positions_definite_count': 3,
            'found_positions_possible_count': 3,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['名詞', 'サ変接続'],
                        'conjugated_type': None,
                        'conjugated_form': None
                    },
                    'jmdict_interp_entry_id': None
                }
            ],
            'interp_position_map': None,
            'quality_score_exact_mod': 1500,
            'quality_score_definite_mod': 1500,
            'quality_score_possible_mod': 1500,
            'article_quality_score': 500,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-07-13T20:00:00'),
            'quality_score_exact': 2000,
            'quality_score_definite': 2000,
            'quality_score_possible': 2000,
        },
    ],
    '模倣': [
        {
            'base_form': '模倣',
            'base_form_definite_group': '模倣',
            'base_form_possible_group': '模倣',
            'article_oid': 'Asahi Editorial 19',
            'found_positions': [{'index': 114, 'len': 2}],
            'found_positions_exact_count': 1,
            'found_positions_definite_count': 1,
            'found_positions_possible_count': 1,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['名詞', 'サ変接続'],
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
            'article_quality_score': -1000,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-05-30T20:00:00'),
            'quality_score_exact': -1000,
            'quality_score_definite': -1000,
            'quality_score_possible': -1000,
        },
        {
            'base_form': '模倣',
            'base_form_definite_group': '模倣',
            'base_form_possible_group': '模倣',
            'article_oid': 'Asahi Editorial 20',
            'found_positions': [
                {'index': 105, 'len': 2},
                {'index': 70, 'len': 2}
            ],
            'found_positions_exact_count': 2,
            'found_positions_definite_count': 2,
            'found_positions_possible_count': 2,
            'possible_interps': [
                {
                    'interp_sources': [1],
                    'mecab_interp': {
                        'parts_of_speech': ['名詞', 'サ変接続'],
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
            'article_quality_score': -1000,
            'article_last_updated_datetime':
                datetime.fromisoformat('2018-05-30T20:00:00'),
            'quality_score_exact': -250,
            'quality_score_definite': -250,
            'quality_score_possible': -250,
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
    'article_oid': 'Kakuyomu Series 4 Article 1',
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
UPDATE_CRAWL_EXPECTED_FLI_QUERY_DOCS['だから'].append({
    'base_form': 'だから',
    'base_form_definite_group': 'だから',
    'base_form_possible_group': 'だから',
    'article_oid': 'Asahi Article 21 (News, Normal)',
    'found_positions': [{'index': 55, 'len': 3}],
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
    'article_quality_score': -1000,
    'article_last_updated_datetime':
        datetime.fromisoformat('2018-08-15T04:10:00'),
    'quality_score_exact': -1000,
    'quality_score_definite': -1000,
    'quality_score_possible': -1000,
})
UPDATE_CRAWL_EXPECTED_FLI_QUERY_DOCS['吾輩'] = [{
    'base_form': '吾輩',
    'base_form_definite_group': '吾輩',
    'base_form_possible_group': '吾輩',
    'article_oid': 'Kakuyomu Series 3 Article 2',
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
UPDATE_CRAWL_EXPECTED_FLI_QUERY_DOCS['恰幅'] = [{
    'base_form': '恰幅',
    'base_form_definite_group': '恰幅',
    'base_form_possible_group': '恰幅',
    'article_oid': 'Asahi Editorial 27',
    'found_positions': [{'index': 150, 'len': 2}],
    'found_positions_exact_count': 1,
    'found_positions_definite_count': 1,
    'found_positions_possible_count': 1,
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
    'quality_score_exact_mod': 0,
    'quality_score_definite_mod': 0,
    'quality_score_possible_mod': 0,
    'article_quality_score': -1000,
    'article_last_updated_datetime':
        datetime.fromisoformat('2018-08-14T20:00:00'),
    'quality_score_exact': -1000,
    'quality_score_definite': -1000,
    'quality_score_possible': -1000,
}]
UPDATE_CRAWL_EXPECTED_FLI_QUERY_DOCS['美しさ'] = [
    {
        'base_form': '美しさ',
        'base_form_definite_group': '美しさ',
        'base_form_possible_group': '美しさ',
        'article_oid': 'Asahi Article 26 (Column, Normal)',
        'found_positions': [{'index': 92, 'len': 3}],
        'found_positions_exact_count': 1,
        'found_positions_definite_count': 1,
        'found_positions_possible_count': 1,
        'possible_interps': [
            {
                'interp_sources': [2, 3],
                'mecab_interp': None,
                'jmdict_interp_entry_id': '2765450'
            }
        ],
        'interp_position_map': None,
        'quality_score_exact_mod': 0,
        'quality_score_definite_mod': 0,
        'quality_score_possible_mod': 0,
        'article_quality_score': -1000,
        'article_last_updated_datetime':
            datetime.fromisoformat('2018-08-15T07:49:00'),
        'quality_score_exact': -1000,
        'quality_score_definite': -1000,
        'quality_score_possible': -1000,
    },
    {
        'base_form': '美しさ',
        'base_form_definite_group': '美しさ',
        'base_form_possible_group': '美しさ',
        'article_oid': 'Asahi Editorial 28',
        'found_positions': [
            {'index': 70, 'len': 3},
            {'index': 63, 'len': 3}
        ],
        'found_positions_exact_count': 2,
        'found_positions_definite_count': 2,
        'found_positions_possible_count': 2,
        'possible_interps': [
            {
                'interp_sources': [2, 3],
                'mecab_interp': None,
                'jmdict_interp_entry_id': '2765450'
            }
        ],
        'interp_position_map': None,
        'quality_score_exact_mod': 750,
        'quality_score_definite_mod': 750,
        'quality_score_possible_mod': 750,
        'article_quality_score': -1000,
        'article_last_updated_datetime':
            datetime.fromisoformat('2018-08-14T20:00:00'),
        'quality_score_exact': -250,
        'quality_score_definite': -250,
        'quality_score_possible': -250,
    },
]


@enum.unique
class SourceUpdateState(enum.Enum):
    """The update state of the content for a source crawled by a crawler.

    Attributes:
        INITIAL: The source is in its initial content state.
        UPDATE: The source has had some updates applied to its content since
            the last crawl.
        NO_CHANGES: Nothing has changed with the source content since its last
            crawl.
    """
    INITIAL = 1
    UPDATE = 2
    NO_CHANGES = 3


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

        'https://www.asahi.com/news/':
            os.path.join(TEST_DIR, 'test_html/asahi/news_top_initial.html'),

        'https://www.asahi.com/rensai/featurelist.html':
            os.path.join(TEST_DIR, 'test_html/asahi/column_top_initial.html'),

        'https://www.asahi.com/news/editorial.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/editorial_top_initial.html'
            ),

        'https://www.asahi.com/articles/3.html':
            os.path.join(TEST_DIR, 'test_html/asahi/news_article_3.html'),

        'https://www.asahi.com/articles/5.html':
            os.path.join(TEST_DIR, 'test_html/asahi/news_article_5.html'),

        'https://www.asahi.com/articles/6.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/news_article_6_silver.html'
            ),

        'https://www.asahi.com/articles/8.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/column_article_8.html'
            ),

        'https://www.asahi.com/articles/11.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/column_article_11_gold.html'
            ),

        'https://www.asahi.com/articles/14.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/column_article_14.html'
            ),

        'https://www.asahi.com/articles/15.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/editorial_article_15.html'
            ),

        'https://www.asahi.com/articles/16.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/editorial_article_16.html'
            ),

        'https://www.asahi.com/articles/17.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/editorial_article_17.html'
            ),

        'https://www.asahi.com/articles/18.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/editorial_article_18.html'
            ),

        'https://www.asahi.com/articles/19.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/editorial_article_19.html'
            ),

        'https://www.asahi.com/articles/20.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/editorial_article_20.html'
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

        'https://www.asahi.com/news/':
            os.path.join(TEST_DIR, 'test_html/asahi/news_top_update.html'),

        'https://www.asahi.com/rensai/featurelist.html':
            os.path.join(TEST_DIR, 'test_html/asahi/column_top_update.html'),

        'https://www.asahi.com/news/editorial.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/editorial_top_update.html'
            ),

        'https://www.asahi.com/articles/21.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/news_article_21.html'
            ),

        'https://www.asahi.com/articles/26.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/column_article_26.html'
            ),

        'https://www.asahi.com/articles/27.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/editorial_article_27.html'
            ),

        'https://www.asahi.com/articles/28.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/editorial_article_28.html'
            ),
    }

    _NO_CHANGES_CRAWL_RESPONSE_HTML = {
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

        # These series pages have a last update date set far in the future so
        # that the crawler will always check them for updates during the UPDATE
        # crawl. Since the last update date for the series is in the future, it
        # means these series pages will be crawled again during the NO_CHANGES
        # crawl even though nothing has changed on them.
        'https://kakuyomu.jp/series-link-1':
            os.path.join(TEST_DIR, 'test_html/kakuyomu/series_1_update.html'),

        'https://kakuyomu.jp/series-link-3':
            os.path.join(TEST_DIR, 'test_html/kakuyomu/series_3_update.html'),

        'https://kakuyomu.jp/series-link-4':
            os.path.join(TEST_DIR, 'test_html/kakuyomu/series_4.html'),

        'https://www.asahi.com/news/':
            os.path.join(TEST_DIR, 'test_html/asahi/news_top_update.html'),

        'https://www.asahi.com/rensai/featurelist.html':
            os.path.join(TEST_DIR, 'test_html/asahi/column_top_update.html'),

        'https://www.asahi.com/news/editorial.html':
            os.path.join(
                TEST_DIR,
                'test_html/asahi/editorial_top_update.html'
            ),
    }

    _RESPONSE_HTML_MAP = {
        SourceUpdateState.INITIAL: _INITIAL_CRAWL_RESPONSE_HTML,
        SourceUpdateState.UPDATE: _UPDATE_CRAWL_RESPONSE_HTML,
        SourceUpdateState.NO_CHANGES: _NO_CHANGES_CRAWL_RESPONSE_HTML,
    }

    _current_update_state: SourceUpdateState = None
    _request_counter: collections.Counter = None

    def __init__(self) -> None:
        """Stub for the init of a requests Session.

        Sets the response HTML to use for this session based on the currently
        set update state for the MockRequestsSession class.
        """
        if self._current_update_state is None:
            raise RuntimeError(
                'MockRequestsSession _current_update_state attribute has not '
                'been set'
            )
        if self._request_counter is None:
            raise RuntimeError(
                'MockRequestsSession _request_counter attribute has not been '
                'set'
            )

        self._response_html = self._RESPONSE_HTML_MAP[
            MockRequestsSession._current_update_state
        ]

    def get(self, url: str, timeout: int) -> requests.Response:
        """Returns a response with the test HTML for the given url."""
        if url not in self._response_html:
            raise AssertionError(
                f'Unexpected request to url "{url}" with source update state '
                f'set to {self._current_update_state}'
            )
        MockRequestsSession._request_counter[url] += 1

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

    @staticmethod
    def start_request_tracking(update_state: SourceUpdateState) -> None:
        """Starts request tracking for all MockRequestsSession instances.

        Resets requests tracking if it had been started previously.

        Args:
            update_state: The update state the sources are in. This is used to
                determine which source URLs should be getting requests during
                the tracking.
        """
        MockRequestsSession._current_update_state = update_state
        MockRequestsSession._request_counter = Counter()

    @staticmethod
    def assert_request_counts() -> None:
        """Asserts that the tracked request counts match the expected counts.

        Checks that every URL that should have been requested for the currently
        set source update state was requested exactly once since the last call
        to start_request_tracking.
        """
        response_html = MockRequestsSession._RESPONSE_HTML_MAP[
            MockRequestsSession._current_update_state
        ]
        for url in response_html:
            assert url in MockRequestsSession._request_counter
            assert MockRequestsSession._request_counter[url] == 1


def assert_doc_field_value(
    field: str, value: Any, expected_doc: _Document,
    oid_map: Dict[str, ObjectId]
) -> None:
    """Asserts a given field value pair for a doc matches an expected doc.

    Args:
        field: A field from a MongoDB doc.
        value: The value for that field from the doc.
        expected_doc: The expected document that the field value pair should
            match.
        oid_map: A mapping from blog and article titles to the ObjectId for the
            blog or article in the db.
    """
    if field.endswith('_oid'):
        # The value for non-None foreign key references in the expected docs is
        # the title of the blog/article that should be referenced by the key,
        # so the oid_map can be used to look up what the key value should be.
        if expected_doc[field] is None:
            assert value is None
        else:
            assert value == oid_map[expected_doc[field]]
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
        raise AssertionError(f'Unexpected field: {field}:{value}')


def assert_blog_db_data(
    db: CrawlDb, blog_expected_docs: List[_Document],
    oid_map: Dict[str, ObjectId]
) -> None:
    """Asserts blog data in db matches the given documents.

    Args:
        db: CrawlDb client to use to access the db data.
        blog_expected:docs: The expected blog document data to be in the db.
            Should be sorted in the order of the expected insertion order of
            the blog documents into the db.
        oid_map: A mapping from blog and article titles to the ObjectId for the
            blog or article in the db.

            The mappings for all blogs in the db will be added to the map in
            this function.
    """
    blog_db_docs = db._blog_collection.find({}).sort(
        '_id', pymongo.ASCENDING
    )
    blog_doc_zip = zip(blog_db_docs, blog_expected_docs)
    for blog_doc, expected_blog_doc in blog_doc_zip:
        assert len(blog_doc) == BLOG_DOC_EXPECTED_FIELD_COUNT
        assert 'title' in blog_doc
        assert '_id' in blog_doc
        oid_map[blog_doc['title']] = blog_doc['_id']

        for field, value in blog_doc.items():
            assert_doc_field_value(field, value, expected_blog_doc, oid_map)


def assert_article_db_data(
    db: CrawlDb, article_expected_docs: List[_Document],
    oid_map: Dict[str, ObjectId]
) -> None:
    """Asserts article data in db matches the given documents.

    Args:
        db: CrawlDb client to use to access the db data.
        article_expected_docs: The expected article document data to be in the
            db. Should be sorted in the order of the expected insertion order
            of the article documents into the db.
        oid_map: A mapping from blog and article titles to the ObjectId for the
            blog or article in the db. All of the blogs in the db must be added
            to the map before giving it to this function.

            The mappings for all articles in the db will be added to the map in
            this function.
    """
    article_db_docs = db._article_collection.find({}).sort(
        '_id', pymongo.ASCENDING
    )
    article_doc_zip = zip(article_db_docs, article_expected_docs)
    for article_doc, expected_article_doc in article_doc_zip:
        assert len(article_doc) == ARTICLE_DOC_EXPECTED_FIELD_COUNT
        assert 'title' in article_doc
        assert '_id' in article_doc
        oid_map[article_doc['title']] = article_doc['_id']

        for field, value in article_doc.items():
            assert_doc_field_value(field, value, expected_article_doc, oid_map)


def assert_found_lexical_item_db_data(
    db: CrawlDb, fli_query_expected_docs: Dict[str, List[_Document]],
    oid_map: Dict[str, ObjectId]
) -> None:
    """Asserts found lexical item data in db matches the given documents.

    Args:
        db: CrawlDb client to use to access the db data.
        fli_query_expected_docs: A dictionary mapping base_form queries to the
            expected found lexical item document data to be in the db for that
            query.

            The document lists should be sorted in the order of the expected
            insertion order of the found lexical item documents into the db.
        oid_map: A mapping from blog and article titles to the ObjectId for the
            blog or article in the db. All of the articles in the db must be
            added to the map before giving it to this function.
    """
    for base_form, expected_fli_docs in fli_query_expected_docs.items():
        cursor = db._found_lexical_item_collection.find(
            {'base_form': base_form}
        )
        fli_db_docs = cursor.sort('_id', pymongo.ASCENDING)
        fli_doc_zip = zip(fli_db_docs, expected_fli_docs)
        for fli_doc, expected_fli_doc in fli_doc_zip:
            assert len(fli_doc) == FLI_DOC_EXPECTED_FIELD_COUNT

            for field, value in fli_doc.items():
                assert_doc_field_value(field, value, expected_fli_doc, oid_map)


def assert_crawl_skip_db_data(
    db: CrawlDb, crawl_skip_expected_docs: List[_Document]
) -> None:
    """Asserts crawl skip data in db matches the given documents.

    Args:
        db: CrawlDb client to use to access the db data.
        crawl_skip_expected_docs: The expected crawl skip document data to be
            in the db. Should be sorted in the order of the expected insertion
            order of the crawl skip documents into the db.
    """
    crawl_skip_db_docs = db._crawl_skip_collection.find({}).sort(
        '_id', pymongo.ASCENDING
    )
    crawl_skip_doc_zip = zip(crawl_skip_db_docs, crawl_skip_expected_docs)
    for crawl_skip_doc, expected_crawl_skip_doc in crawl_skip_doc_zip:
        assert len(crawl_skip_doc) == CRAWL_SKIP_DOC_EXPECTED_FIELD_COUNT

        for field, value in crawl_skip_doc.items():
            assert_doc_field_value(field, value, expected_crawl_skip_doc, {})


def assert_initial_crawl_db_data() -> None:
    """Asserts the db data matches the expected initial crawl data."""
    oid_map: Dict[str, ObjectId] = {}
    with CrawlDb() as db:
        assert_blog_db_data(db, INITIAL_CRAWL_EXPECTED_BLOG_DOCS, oid_map)
        assert_article_db_data(
            db, INITIAL_CRAWL_EXPECTED_ARTICLE_DOCS, oid_map
        )
        assert_found_lexical_item_db_data(
            db, INITIAL_CRAWL_EXPECTED_FLI_QUERY_DOCS, oid_map
        )
        assert_crawl_skip_db_data(db, INITIAL_CRAWL_EXPECTED_CRAWL_SKIP_DOCS)


def assert_update_crawl_db_data() -> None:
    """Asserts the db data matches the expected update crawl data."""
    oid_map: Dict[str, ObjectId] = {}
    with CrawlDb() as db:
        assert_blog_db_data(db, UPDATE_CRAWL_EXPECTED_BLOG_DOCS, oid_map)
        assert_article_db_data(
            db, UPDATE_CRAWL_EXPECTED_ARTICLE_DOCS, oid_map
        )
        assert_found_lexical_item_db_data(
            db, UPDATE_CRAWL_EXPECTED_FLI_QUERY_DOCS, oid_map
        )
        assert_crawl_skip_db_data(db, UPDATE_CRAWL_EXPECTED_CRAWL_SKIP_DOCS)


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
    mocker.patch('sys.argv', ['pytest', 'Kakuyomu,Asahi'])
    mocker.patch('requests.Session', MockRequestsSession)

    # Use small search result page size to ensure not all data crawled gets
    # stored in the first page cache
    mocker.patch(
        'myaku.datastore.database.CrawlDb.SEARCH_RESULTS_PAGE_SIZE', 2
    )

    MockRequestsSession.start_request_tracking(SourceUpdateState.INITIAL)
    run_crawl.main()
    assert_initial_crawl_db_data()
    assert_first_page_cache_data()
    MockRequestsSession.assert_request_counts()

    MockRequestsSession.start_request_tracking(SourceUpdateState.UPDATE)
    run_crawl.main()
    assert_update_crawl_db_data()
    assert_first_page_cache_data()
    MockRequestsSession.assert_request_counts()

    # Run update crawls one more time with the same test HTML to make sure
    # no issues happen during crawls when nothing has changed on the site since
    # the last time it was crawled.
    MockRequestsSession.start_request_tracking(SourceUpdateState.NO_CHANGES)
    run_crawl.main()
    assert_update_crawl_db_data()
    assert_first_page_cache_data()
    MockRequestsSession.assert_request_counts()
