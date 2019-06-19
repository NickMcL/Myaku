from operator import methodcaller

import reibun.utils as utils
from reibun.database import ReibunDb

JPN_PERIOD = '。'
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

            start = utils.find_jpn_sentene_start(
                item.article.full_text, item.text_pos_abs
            )
            end = utils.find_jpn_sentene_end(
                item.article.full_text,
                item.text_pos_abs + len(item.surface_form)
            )

            print()
            print('{:.0%}: '.format(item.text_pos_percent), end='')
            print(
                item.article.full_text[start:item.text_pos_abs].lstrip(),
                end=''
            )
            print(Color.CYAN + item.article.full_text[
                item.text_pos_abs: item.text_pos_abs + len(item.surface_form)
            ], end='')
            print(Color.END + item.article.full_text[
                item.text_pos_abs + len(item.surface_form):end
            ].rstrip())