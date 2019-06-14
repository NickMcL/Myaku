import reibun.utils as utils
from reibun.indexdb import ReibunIndexDb

JPN_PERIOD = '。'


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
    utils.toggle_reibun_debug_log()
    while True:
        query = input('\nSearch for: ')

        with ReibunIndexDb() as db:
            found_lexical_items = db.read_found_lexical_items(query)

        print(f'\nFound {len(found_lexical_items)} results:')
        for item in found_lexical_items:
            start = item.article.full_text.rfind(
                JPN_PERIOD, 0, item.text_pos_abs
            )
            start += 1

            end = item.article.full_text.find(JPN_PERIOD, item.text_pos_abs)
            if end == -1:
                end = len(item.article.full_text) - 1
            end += 1

            print()
            print(item.article.full_text[start:item.text_pos_abs], end='')
            print(Color.CYAN + item.article.full_text[
                item.text_pos_abs: item.text_pos_abs + len(item.surface_form)
            ], end='')
            print(Color.END + item.article.full_text[
                item.text_pos_abs + len(item.surface_form):end
            ])
            print(
                f'{item.article.title} - {item.article.source_name} - '
                f'{item.article.source_url}'
            )
