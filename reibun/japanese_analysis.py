"""Utilities for analyzing Japanese text."""

import gzip
import logging
import os
import shutil
import subprocess
import sys
import urllib
from contextlib import closing
from dataclasses import dataclass
from typing import List, Optional, Set
from xml.etree import ElementTree

import MeCab

import reibun.utils as utils
from reibun.datatypes import Article, FoundLexicalItem

_log = logging.getLogger(__name__)

_RESOURCE_FILE_DIR = os.path.dirname(os.path.realpath(__file__))
_JMDICT_XML_FILEPATH = os.path.join(_RESOURCE_FILE_DIR, 'JMdict_e.xml')
_JMDICT_GZ_FILEPATH = os.path.join(_RESOURCE_FILE_DIR, 'JMdict_e.gz')
_JMDICT_LATEST_FTP_URL = 'ftp://ftp.monash.edu.au/pub/nihongo/JMdict_e.gz'

utils.toggle_reibun_debug_log()


def update_resources() -> None:
    """Downloads the latest versions of resources used for JPN analysis."""
    _update_jmdict_files()


def _update_jmdict_files() -> None:
    """Downloads and unpacks the latest JMdict files."""
    _log.debug(
        f'Downloading JMdict gz file from {_JMDICT_LATEST_FTP_URL} to '
        f'{_JMDICT_GZ_FILEPATH}'
    )
    with closing(urllib.request.urlopen(_JMDICT_LATEST_FTP_URL)) as response:
        with open(_JMDICT_GZ_FILEPATH, 'wb') as jmdict_gz_file:
            shutil.copyfileobj(response, jmdict_gz_file)

    _log.debug(
        f'Decompressing {_JMDICT_GZ_FILEPATH} to {_JMDICT_XML_FILEPATH}'
    )
    with gzip.open(_JMDICT_GZ_FILEPATH, 'rb') as jmdict_decomp_file:
        with open(_JMDICT_XML_FILEPATH, 'wb') as jmdict_xml_file:
            shutil.copyfileobj(jmdict_decomp_file, jmdict_xml_file)

    _log.debug(f'Removing {_JMDICT_GZ_FILEPATH}')
    os.remove(_JMDICT_GZ_FILEPATH)


class ResourceLoadError(Exception):
    """Raised if a necessary external resource fails to load.

    For example, if an analyzer fails to load a dictionary file necessary for
    its operation, this exception will be raised.
    """
    pass


class ResourceNotReadyError(Exception):
    """Raised if a resource is used before it is ready to be used.

    For example, trying to use an external resource such as a dictionary before
    it has been loaded.
    """
    pass


class TextAnalysisError(Exception):
    """Raised if an unexpected error occurs during text analysis."""
    pass


@utils.add_method_debug_logging
class JapaneseTextAnalyzer(object):
    """Analyzes Japanese text to determine used lexical items."""

    # Parts of speech considered non-lexical items
    _NONLEXICAL_ITEM_POS = {
        '\u8a18\u53f7',  # Symbols (kigou)
    }

    def __init__(self) -> None:
        """Inits the resources needed for text analysis."""
        self._jmdict = JMdict(_JMDICT_XML_FILEPATH)
        self._mecab_tagger = MecabTagger()

    def find_article_lexical_items(self, article: Article) -> None:
        """Finds all lexical items in an article.

        Adds all of the found lexical items to the found_lexical_items list
        attr of the given Article.

        Args:
            article: Article whose full_text will be analyzed to find lexical
                items.
        """
        text_blocks = [b for b in article.full_text.splitlines() if b != '']
        _log.debug(f'Article {article} split into {len(text_blocks)} blocks')

        if article.found_lexical_items is None:
            article.found_lexical_items = []

        offset = 0
        for text_block in text_blocks:
            found_lexical_items = self._find_lexical_items(
                text_block, offset, article.alnum_count
            )

            _log.debug(
                f'Found {len(found_lexical_items)} lexical items in block '
                f'"{utils.shorten_str(text_block, 15)}"'
            )
            article.found_lexical_items.extend(found_lexical_items)

            offset += utils.alnum_count(text_block)

    def _find_lexical_items(
        self, text: str, offset: int, article_len: int
    ) -> List[FoundLexicalItem]:
        """Finds all lexical items in a block of text.

        Args:
            text: Text block that will be analyzed for lexical items.
            offset: The alnum character offset of the text block in its
                article.
            article_len: The total number of alnum characters in the article
                for the text block.

        Returns:
            The found lexical items in the text.
        """
        mecab_tokens = self._mecab_tagger.parse(text)

        found_lexical_items = []
        for token in mecab_tokens:
            is_nonlexical = any(
                t in self._NONLEXICAL_ITEM_POS for t in token.parts_of_speech
            )
            if is_nonlexical:
                offset += utils.alnum_count(token.surface_form)
                continue

            found_lexical_item = FoundLexicalItem(
                token.base_form, token.surface_form, offset,
                offset / article_len, token.parts_of_speech
            )
            found_lexical_items.append(found_lexical_item)

            offset += utils.alnum_count(token.surface_form)

        return found_lexical_items


@utils.add_method_debug_logging
class JMdict(object):
    """Object representation of a JMdict dictionary."""

    # JMdict entries can have several representations stored as sub-elements of
    # different types within the entry XML. This map maps the tag for each of
    # these sub-element types to the tag within that sub-element that holds the
    # string representation for that representation of the entry.
    _JMDICT_ELEMENT_REPR_MAP = {
        'k_ele': 'keb',  # kanji representation sub-element
        'r_ele': 'reb'   # kana representation sub-element
    }

    def __init__(self, jmdict_xml_filepath: str = None) -> None:
        self._jmdict_entries = None

        if jmdict_xml_filepath is not None:
            self.load_jmdict(jmdict_xml_filepath)

    @utils.skip_method_debug_logging
    def _parse_jmdict_reprs(
        self, jmdict_entry: ElementTree.Element
    ) -> Set[str]:
        """Parse all string representations for a given JMdict XML entry.

        Because many Japanese words can be written using kanji as well as kana,
        there are often different ways to write the same word. JMdict entries
        include each of these representations as separate elements, so this
        function parses all of the representations for a given entry and
        returns them in a set.

        Args:
            jmdict_entry: An XML entry element from a JMdict XML file.

        Returns:
            A set of all of the string representations of the given entry.

        Raises:
            ResourceLoadError: The passed entry had malformed JMdict XML, so it
            could not be parsed.
        """
        repr_strs = set()
        repr_elements = (
            e for e in jmdict_entry if e.tag in self._JMDICT_ELEMENT_REPR_MAP
        )

        for element in repr_elements:
            repr_str = element.findtext(
                self._JMDICT_ELEMENT_REPR_MAP[element.tag]
            )
            if repr_str is None or repr_str == '':
                element_str = ElementTree.tostring(jmdict_entry).decode()
                utils.log_and_raise(
                    _log, ResourceLoadError,
                    f'Malformed JMdict XML. No '
                    f'{self._JMDICT_ELEMENT_REPR_MAP[element.tag]} element or '
                    f'text found within {element.tag} element: {element_str}'
                )

            repr_strs.add(repr_str)

        if len(repr_strs) == 0:
            element_str = ElementTree.tostring(jmdict_entry).decode()
            repr_element_tags = list(self._JMDICT_ELEMENT_REPR_MAP.keys())
            utils.log_and_raise(
                _log, ResourceLoadError,
                f'Malformed JMdict XML. No {repr_element_tags} elements found '
                f'within {jmdict_entry.tag} element: {element_str}'
            )

        return repr_strs

    def load_jmdict(self, xml_filepath: str) -> None:
        """Loads data from a JMdict XML file.

        Args:
            xml_filepath: Path to an JMdict XML file.

        Raises:
            ResourceLoadError: There was an issue with the passed JMdict XML
                file that prevented it from being loaded.
        """
        if not os.path.exists(xml_filepath):
            utils.log_and_raise(
                _log, ResourceLoadError,
                f'JMdict file not found at {_JMDICT_XML_FILEPATH}'
            )

        _log.debug(f'Reading JMdict XML file at {_JMDICT_XML_FILEPATH}')
        tree = ElementTree.parse(xml_filepath)
        _log.debug('Reading of JMdict XML file complete')

        self._jmdict_entries = set()
        root = tree.getroot()
        for entry in root:
            self._jmdict_entries.update(self._parse_jmdict_reprs(entry))

    def contains_entry(self, entry: str) -> bool:
        """Tests if entry is in the loaded JMdict entries.

        Args:
            entry: entry to check for in the loaded JMdict entries.

        Returns:
            True if the entry is in the loaded JMdict entries, False otherwise.

        Raises:
            ResourceNotReadyError: JMdict data has not been loaded into this
                JMdict object yet.
        """
        if self._jmdict_entries is None:
            utils.log_and_raise(
                _log, ResourceNotReadyError,
                'JMdict object used before loading any JMdict data.'
            )
        return entry in self._jmdict_entries

    def __contains__(self, entry) -> bool:
        """Simply calls self.contains_entry."""
        return self.contains_entry(entry)


@dataclass
class MecabToken:
    """A text token with tags from MeCab.

    Note that all of the attributes will generally contain all Japanese
    characters since MeCab's tags are in Japanese.

    Attributes:
        surface_form: The form of the token used in the text.
        reading: The (best guess) reading of the token in katakana.
        base_form: The base (dictionary) form of the token.
        parts_of_speech: The parts of speech of the token. Possibly multiple,
            so it is a list.
        conjugated_type: The name of the conjugation type of the token.
        conjugated_form: The name of the conjugated form of the token.
    """
    surface_form: str
    reading: str
    base_form: str
    parts_of_speech: List[str]
    conjugated_type: str = None
    conjugated_form: str = None


@utils.add_method_debug_logging
class MecabTagger:
    """Object representation of a MeCab tagger.

    mecab-python3 provides a wrapper for MeCab in the MeCab module, but that
    wrapper doesn't handle many things such as configuring MeCab settings or
    parsing MeCab tagger output, so this class builds on top of that wrapper to
    make the MeCab tagger easier to work with in Python.
    """
    _MECAB_NEOLOGD_DIR_NAME = 'mecab-ipadic-neologd'
    _END_OF_SECTION_MARKER = 'EOS'
    _POS_SPLITTER = '-'
    _EXPECTED_TOKEN_TAG_COUNTS = {4, 5, 6}

    def __init__(self, use_default_ipadic: bool = False) -> None:
        """Inits the MeCab tagger wrapper.

        Unless use_default_ipadic is True, attempts to use the ipadic-NEologd
        dictionary if available on the system. Logs warning if NEologd cannot
        be used and then uses the default ipadic dictionary instead.

        Args:
            use_default_ipadic: If True, forces tagger to use the default
                ipadic dictionary instead of the ipadic-NEologd dictionary.
        """
        self._mecab_tagger = None

        if use_default_ipadic:
            neologd_path = None
        else:
            neologd_path = self._get_mecab_neologd_dict_path()

        if neologd_path is None:
            self._mecab_tagger = MeCab.Tagger('-Ochasen')
        else:
            self._mecab_tagger = MeCab.Tagger(f'-Ochasen -d {neologd_path}')

    def parse(self, text: str) -> List[MecabToken]:
        """Parses the text with MeCab and returns the resulting tokens.

        Raises:
            TextAnalysisError: MeCab gave an unexpected output when parsing the
                text.
        """
        mecab_out = self._mecab_tagger.parse(text)
        parsed_tokens = (
            line.split() for line in mecab_out.splitlines() if line != ''
        )

        mecab_tokens = []
        for parsed_token_tags in parsed_tokens:
            if (len(parsed_token_tags) == 1
                    and parsed_token_tags[0] == self._END_OF_SECTION_MARKER):
                continue

            if len(parsed_token_tags) not in self._EXPECTED_TOKEN_TAG_COUNTS:
                utils.log_and_raise(
                    _log, TextAnalysisError,
                    f'Unexpected number of MeCab tags '
                    f'({len(parsed_token_tags)}) for token '
                    f'{parsed_token_tags} in {text}'
                )

            mecab_token = MecabToken(
                parsed_token_tags[0], parsed_token_tags[1],
                parsed_token_tags[2],
                parsed_token_tags[3].split(self._POS_SPLITTER)
            )
            if len(parsed_token_tags) >= 5:
                mecab_token.conjugated_type = parsed_token_tags[4]
            if len(parsed_token_tags) >= 6:
                mecab_token.conjugated_form = parsed_token_tags[5]

            mecab_tokens.append(mecab_token)

        return mecab_tokens

    def _get_mecab_neologd_dict_path(self) -> Optional[str]:
        """Attempts to find the path to the NEologd dict in the system.

        This function is best effort. Logs warning if NEologd dictionary cannot
        be found on the system and then returns None.

        Returns:
            The path to the directory containing the NEologd dictionary, or
            None if the NEologd dictionary could not be found.
        """
        output = subprocess.run(
            ['mecab-config', '--version'], capture_output=True
        )
        if output.returncode != 0:
            _log.warning(
                'MeCab is not installed on this system, so the '
                'mecab-ipadic-NEologd dictionary cannot be used.'
            )
            return None

        output = subprocess.run(
            ['mecab-config', '--dicdir'], capture_output=True
        )
        if output.returncode != 0:
            _log.warning(
                'MeCab dictionary directory could not be retrieved, so the '
                'mecab-ipadic-NEologd dictionary cannot be used.'
            )
            return None

        neologd_path = os.path.join(
            output.stdout.decode(sys.stdout.encoding).strip(),
            self._MECAB_NEOLOGD_DIR_NAME
        )
        if not os.path.exists(neologd_path):
            _log.warning(
                'mecab-ipadic-NEologd is not installed on this system, so the '
                'mecab-ipadic-NEologd dictionary cannot be used.'
            )
            return None

        return neologd_path
