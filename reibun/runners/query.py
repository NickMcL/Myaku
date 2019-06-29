from operator import methodcaller

import reibun.utils as utils
from reibun.database import ReibunDb
from reibun.datatypes import FoundJpnLexicalItem

LOG_NAME = 'query'


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
    tag_strs.append(str(fli.article.get_article_len_group()) + '+ characters')
    if fli.article.has_video:
        tag_strs.append('Video')
    print('Tags: ' + ', '.join(tag_strs))


def main(search_term: str = None) -> None:
    utils.toggle_reibun_package_log(filename_base=LOG_NAME)
    while True:
        if not search_term:
            query = input('\n\n\nSearch for: ')
        else:
            query = search_term

        with ReibunDb() as db:
            found_lexical_items = db.read_found_lexical_items(query, True)
        if len(found_lexical_items) == 0:
            print('\nFound 0 results')
            if not search_term:
                continue

        found_lexical_items.sort(key=methodcaller('quality_key'), reverse=True)

        instance_count = sum(
            len(item.found_positions) for item in found_lexical_items
        )
        results_str = 'Found {} instances across {} articles'.format(
            instance_count, len(found_lexical_items)
        )
        print('\n' + results_str)
        print('=' * len(results_str))

        for item in found_lexical_items:
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
            print('Total instances: {}'.format(len(item.found_positions)))
            print_tags(item)

            for pos in item.found_positions:
                sentence, start = item.article.get_containing_sentence(pos)
                sentence = sentence.rstrip()
                print()
                print(
                    '{:.0%}: '.format(pos.index / len(item.article.full_text)),
                    end=''
                )
                print(sentence[:pos.index - start], end='')
                print(Color.CYAN + sentence[
                    pos.index - start: pos.index + pos.len - start
                ], end='')
                print(Color.END + sentence[
                    pos.index + pos.len - start:
                ])

        if search_term:
            return


if __name__ == '__main__':
    main()
