import reibun.utils as utils
from reibun.database import ReibunDb

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


def find_sentene_start(text: str, pos: int) -> int:
    prev_period_pos = text.rfind(JPN_PERIOD, 0, pos)
    prev_new_line_pos = text.rfind('\n', 0, pos)
    if prev_period_pos == prev_new_line_pos == -1:
        return 0
    if prev_period_pos > prev_new_line_pos:
        return prev_period_pos + 1
    return prev_new_line_pos + 1


def find_sentene_end(text: str, pos: int, match_len: int) -> int:
    next_period_pos = text.find(JPN_PERIOD, pos + match_len)
    next_new_line_pos = text.find('\n', pos + match_len)
    if next_period_pos == next_new_line_pos == -1:
        return len(text)
    if next_period_pos < next_new_line_pos:
        return next_period_pos + 1
    return next_new_line_pos


if __name__ == '__main__':
    utils.toggle_reibun_debug_log()
    while True:
        query = input('\nSearch for: ')

        with ReibunDb() as db:
            found_lexical_items = db.read_found_lexical_items(query)
        found_lexical_items.sort(key=lambda i: i.text_pos_abs)

        print(f'\nFound {len(found_lexical_items)} results:')
        breakpoint()
        for item in found_lexical_items:
            start = find_sentene_start(
                item.article.full_text, item.text_pos_abs
            )
            end = find_sentene_end(
                item.article.full_text, item.text_pos_abs,
                len(item.surface_form)
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
            print('{} - {}'.format(
                item.article.metadata.title,
                item.article.metadata.publication_datetime.strftime(
                    '%b %d, %Y'
                )
            ))
            print('{} - {}'.format(
                item.article.metadata.source_name,
                item.article.metadata.source_url
            ))
