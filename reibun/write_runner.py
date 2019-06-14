import sys
from datetime import datetime

import reibun.utils as utils
from reibun.datatypes import JpnArticle
from reibun.indexdb import ReibunIndexDb
from reibun.japanese_analysis import JapaneseTextAnalyzer
from reibun.sample_text import SAMPLE_TEXT

# From the public domain 桜の森の満開の下 by 坂口安吾
# SAMPLE_TEXT = """
# 桜の花が咲くと人々は酒をぶらさげたり団子をたべて花の下を歩いて絶景だの春ランマンだのと浮かれて陽気になりますが、これは嘘です。なぜ嘘かと申しますと、桜の花の下へ人がより集って酔っ払ってゲロを吐いて喧嘩して、これは江戸時代からの話で、大昔は桜の花の下は怖しいと思っても、絶景だなどとは誰も思いませんでした。近頃は桜の花の下といえば人間がより集って酒をのんで喧嘩していますから陽気でにぎやかだと思いこんでいますが、桜の花の下から人間を取り去ると怖ろしい景色になりますので、能にも、さる母親が愛児を人さらいにさらわれて子供を探して発狂して桜の花の満開の林の下へ来かかり見渡す花びらの陰に子供の幻を描いて狂い死して花びらに埋まってしまう（このところ小生の蛇足）という話もあり、桜の林の花の下に人の姿がなければ怖しいばかりです。

# 　昔、鈴鹿峠にも旅人が桜の森の花の下を通らなければならないような道になっていました。花の咲かない頃はよろしいのですが、花の季節になると、旅人はみんな森の花の下で気が変になりました。できるだけ早く花の下から逃げようと思って、青い木や枯れ木のある方へ一目散に走りだしたものです。一人だとまだよいので、なぜかというと、花の下を一目散に逃げて、あたりまえの木の下へくるとホッとしてヤレヤレと思って、すむからですが、二人連は都合が悪い。なぜなら人間の足の早さは各人各様で、一人が遅れますから、オイ待ってくれ、後から必死に叫んでも、みんな気違いで、友達をすてて走ります。それで鈴鹿峠の桜の森の花の下を通過したとたんに今迄仲のよかった旅人が仲が悪くなり、相手の友情を信用しなくなります。そんなことから旅人も自然に桜の森の下を通らないで、わざわざ遠まわりの別の山道を歩くようになり、やがて桜の森は街道を外れて人の子一人通らない山の静寂へとり残されてしまいました。

# 　そうなって何年かあとに、この山に一人の山賊が住みはじめましたが、この山賊はずいぶんむごたらしい男で、街道へでて情容赦なく着物をはぎ人の命も断ちましたが、こんな男でも桜の森の花の下へくるとやっぱり怖しくなって気が変になりました。そこで山賊はそれ以来花がきらいで、花というものは怖しいものだな、なんだか厭なものだ、そういう風に腹の中では呟いていました。花の下では風がないのにゴウゴウ風が鳴っているような気がしました。そのくせ風がちっともなく、一つも物音がありません。自分の姿と跫音ばかりで、それがひっそり冷めたいそして動かない風の中につつまれていました。花びらがぽそぽそ散るように魂が散っていのちがだんだん衰えて行くように思われます。それで目をつぶって何か叫んで逃げたくなりますが、目をつぶると桜の木にぶつかるので目をつぶるわけにも行きませんから、一そう気違いになるのでした。
# """

OTHER_TEXT = '鯖を読んで五歳ほど若くいう'

TEXT_SRC_URL = 'https://www.aozora.gr.jp/cards/001095/files/42618_21410.html'


if __name__ == '__main__':
    utils.toggle_reibun_debug_log()
    article = JpnArticle(
        title='桜の森の満開の下',
        full_text=SAMPLE_TEXT,
        source_url=TEXT_SRC_URL,
        source_name='Aozora',
        publication_datetime=datetime.utcnow(),
        scraped_datetime=datetime.utcnow()
    )

    with ReibunIndexDb() as db:
        articles = db.filter_to_unstored_articles([article])
        if len(articles) == 0:
            print('\nNo articles!\n')
            sys.exit()

        jta = JapaneseTextAnalyzer()
        items = jta.find_article_lexical_items(article)
        print(f'\nFound {len(items)} lexical items\n')

        db.write_found_lexical_items(items)

    print('\nAll done!\n')
