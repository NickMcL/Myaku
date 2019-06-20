from operator import methodcaller

import reibun.utils as utils
from reibun.database import ReibunDb
from reibun.datatypes import FoundJpnLexicalItem

LOG_FILEPATH = './reibun_read.log'


class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_tags(fli: FoundJpnLexicalItem) -> None:
    tag_strs = []
    tag_strs.append(str(fli.get_article_len_group()) + '+ characters')
    if fli.article.has_video:
        tag_strs.append('Video')
    print('Tags: ' + ', '.join(tag_strs))


if __name__ == '__main__':
    utils.toggle_reibun_debug_log(filepath=LOG_FILEPATH)
    while True:
        query = input('\n\n\nSearch for: ')

        with ReibunDb() as db:
            found_lexical_items = db.read_found_lexical_items(query, True)
        if len(found_lexical_items) == 0:
            print('\nFound 0 results')
            continue

        found_lexical_items.sort(key=methodcaller('quality_key'), reverse=True)

        article_count = len(set(
            i.article.text_hash for i in found_lexical_items
        ))
        results_str = 'Found {} results across {} articles'.format(
            len(found_lexical_items), article_count
        )
        print('\n' + results_str)
        print('=' * len(results_str))

        current = ''
        for item in found_lexical_items:
            if item.article.text_hash != current:
                current = item.article.text_hash
                print('\n\n{} - {}'.format(
                    item.article.metadata.title,
                    item.article.metadata.publication_datetime.strftime(
                        '%b %d, %Y'
                    )
                ))
                s = '{} - {}'.format(
                    item.article.metadata.source_name,
                    item.article.metadata.source_url
                )
                print(s)
                print('-' * len(s))
                print_tags(item)

            sentence, start = item.get_containing_sentence(True)
            item_sentence_pos = item.text_pos_abs - start
            print()
            print('{:.0%}: '.format(item.text_pos_percent), end='')
            print(sentence[:item_sentence_pos], end='')
            print(Color.CYAN + sentence[
                item_sentence_pos: item_sentence_pos + len(item.surface_form)
            ], end='')
            print(Color.END + sentence[
                item_sentence_pos + len(item.surface_form):
            ])
