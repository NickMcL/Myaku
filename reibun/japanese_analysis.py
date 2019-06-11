"""Utilities for analyzing Japanese text."""

import gzip
import logging
import os
import shutil
import subprocess
import sys
import urllib
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass
from typing import Any, List, Tuple, Union
from xml.etree import ElementTree

import MeCab

import reibun.utils as utils
from reibun.datatypes import FoundJpnLexicalItem, JpnArticle

_log = logging.getLogger(__name__)

_RESOURCE_FILE_DIR = os.path.dirname(os.path.realpath(__file__))
_JMDICT_XML_FILEPATH = os.path.join(_RESOURCE_FILE_DIR, 'JMdict_e.xml')
_JMDICT_GZ_FILEPATH = os.path.join(_RESOURCE_FILE_DIR, 'JMdict_e.gz')
_JMDICT_LATEST_FTP_URL = 'ftp://ftp.monash.edu.au/pub/nihongo/JMdict_e.gz'


def update_resources() -> None:
    """Downloads the latest versions of resources used for JPN analysis."""
    _update_jmdict_files()


def _update_jmdict_files() -> None:
    """Downloads and unpacks the latest JMdict files."""
    _log.debug(
        f'Downloading JMdict gz file from "{_JMDICT_LATEST_FTP_URL}" to '
        f'"{_JMDICT_GZ_FILEPATH}"'
    )
    with closing(urllib.request.urlopen(_JMDICT_LATEST_FTP_URL)) as response:
        with open(_JMDICT_GZ_FILEPATH, 'wb') as jmdict_gz_file:
            shutil.copyfileobj(response, jmdict_gz_file)

    _log.debug(
        f'Decompressing "{_JMDICT_GZ_FILEPATH}" to "{_JMDICT_XML_FILEPATH}"'
    )
    with gzip.open(_JMDICT_GZ_FILEPATH, 'rb') as jmdict_decomp_file:
        with open(_JMDICT_XML_FILEPATH, 'wb') as jmdict_xml_file:
            shutil.copyfileobj(jmdict_decomp_file, jmdict_xml_file)

    _log.debug(f'Removing "{_JMDICT_GZ_FILEPATH}"')
    os.remove(_JMDICT_GZ_FILEPATH)


class ResourceLoadError(Exception):
    """Raised if a necessary external resource fails to load.

    For example, an analyzer fails to load a dictionary file necessary for
    its operation.
    """
    pass


class ResourceNotReadyError(Exception):
    """Raised if a resource is used before it is ready to be used.

    For example, trying to use an external resource such as a dictionary before
    it has been loaded.
    """
    pass


class TextAnalysisError(Exception):
    """Raised if an unexpected error occurs related to text analysis."""
    pass


@utils.flyweight_class
@utils.add_method_debug_logging
class JapaneseTextAnalyzer(object):
    """Analyzes Japanese text to determine used lexical items."""

    _SYMBOL_PART_OF_SPEECH = '\u8a18\u53f7'  # Japanese word for symbol (kigou)

    def __init__(self) -> None:
        """Loads the external resources needed for text analysis."""
        self._jmdict = JMdict(_JMDICT_XML_FILEPATH)
        self._mecab_tagger = MecabTagger()

    def find_article_lexical_items(self, article: JpnArticle) -> None:
        """Finds all Japanese lexical items in an article.

        Adds all of the found lexical items to the found_lexical_items list
        attr of the given JpnArticle.

        Args:
            article: Japnaese article whose full_text will be analyzed to find
                lexical items.
        """
        article_blocks = article.full_text.splitlines()
        text_blocks = [b for b in article_blocks if len(b) > 0]
        _log.debug(f'Article "{article}" split into {len(text_blocks)} blocks')

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

            offset += utils.get_alnum_count(text_block)

    def _find_lexical_items(
        self, text: str, offset: int, article_alnum_count: int
    ) -> List[FoundJpnLexicalItem]:
        """Finds all Japanese lexical items in a block of text.

        Args:
            text: Text block that will be analyzed for lexical items.
            offset: The alnum character offset of the text block in its
                article.
            article_alnum_count: The total number of alnum characters in the
                article for the text block.

        Returns:
            The found Japanese lexical items in the text.
        """
        mecab_lexical_items = self._mecab_tagger.parse(text)

        found_lexical_items = []
        for mecab_li in mecab_lexical_items:
            # Mecab includes symbols such as periods and commas in the output
            # of its parse. Strictly speaking, these aren't lexical items, so
            # we discard them here.
            if self._is_symbol(mecab_li):
                offset += utils.get_alnum_count(mecab_li.surface_form)
                continue

            mecab_li.text_pos_abs = offset
            mecab_li.text_pos_percent = offset / article_alnum_count
            found_lexical_items.append(mecab_li)

            offset += utils.get_alnum_count(mecab_li.surface_form)

        return found_lexical_items

    @utils.skip_method_debug_logging
    def _is_symbol(self, lexical_item: FoundJpnLexicalItem) -> bool:
        """Returns True if the Japanese lexical item is a non-alnum symbol.

        Symbols include things like periods, commas, quote characters, etc.
        """
        for part_of_speech in lexical_item.parts_of_speech:
            if part_of_speech == self._SYMBOL_PART_OF_SPEECH:
                return True
        return False


@dataclass
class JMdictEntry(object):
    """Stores the data for an entry from JMdict.

    This class does NOT map exactly to the format official JMdict XML uses to
    store entries. A proper entry from JMdict XML contains all text form
    representations (readings and writings) of an entry, but this class holds
    only a single text form from an entry and the subset of info from that
    entry related to that text form. This form is used because it is easier to
    work with for text analysis.

    Attributes:
        entry_id: The unique ID of the JMdict XML entry that the data for this
            entry came from.
        text_form: The Japanese text representation of the entry. The defining
            part of the entry.
        text_form_info: Info related to this specific text form that may not
            apply to other text forms of the same entry.
        text_form_freq: Info related to how frequently this entry is used in
            Japanese. See JMdict schema for how to decode this info.
        parts_of_speech: Parts of speech that apply to this entry.
        fields: The fields of application for this entry (e.g. food term,
            baseball term, etc.)
        dialect: The dialects that apply for this entry (e.g. kansaiben).
        misc: Other miscellaneous info recorded for this entry from JMdict.
    """
    entry_id: str = None
    text_form: str = None
    text_form_info: Tuple[str, ...] = None
    text_form_freq: Tuple[str, ...] = None
    parts_of_speech: Tuple[str, ...] = None
    fields: Tuple[str, ...] = None
    dialects: Tuple[str, ...] = None
    misc: Tuple[str, ...] = None


@utils.flyweight_class
@utils.add_method_debug_logging
class JMdict(object):
    """Object representation of a JMdict dictionary."""

    _REPR_ELEMENT_TAGS = {
        'k_ele',  # Kanji representation
        'r_ele',  # Reading (kana) representation
    }

    _SENSE_ELEMENT_TAG = 'sense'

    _ENTRY_ID_TAG = 'ent_seq'

    _REPR_TEXT_FORM_TAG = {
        'k_ele': 'keb',
        'r_ele': 'reb',
    }

    _REPR_OPTIONAL_TAGS = {
        'k_ele': [
            'ke_inf',  # Text form information
            'ke_pri',  # Text form frequency
        ],
        'r_ele': [
            're_inf',
            're_pri',
        ],
    }

    _SENSE_OPTIONAL_TAGS = {
        'stagk',  # Applicable kanji representation
        'stagr',  # Applicable reading (kana) representation
        'pos',  # Part of speech
        'field',  # Field of application (e.g. food, baseball, etc.)
        'misc',  # Categorized extra info
        'dial',  # Dialect
        's_inf',  # Uncategorized extra info
    }

    _TAG_TO_OBJ_ATTR_MAP = {
        'ent_seq': 'entry_id',
        'keb': 'text_form',
        'reb': 'text_form',
        'ke_inf': 'text_form_info',
        're_inf': 'text_form_info',
        'ke_pri': 'text_form_freq',
        're_pri': 'text_form_freq',
        'stagk': 'applicable_elements',
        'stagr': 'applicable_elements',
        'pos': 'parts_of_speech',
        'field': 'fields',
        'misc': 'misc',
        'dial': 'dialects',
        's_inf': 'misc',
    }

    # These tags can have more than one element per entry, so their info should
    # be stored in a tuple of strings rather than a single string.
    _TUPPLE_TAGS = {
        'ke_inf',
        're_inf',
        'ke_pri',
        're_pri',
        'stagk',
        'stagr',
        'pos',
        'field',
        'misc',
        'dial',
        's_inf',
    }

    @dataclass
    class _JMdictSense(object):
        """Stores the data for a sense element for a JMdict entry.

        A sense of a JMdict entry holds various info about the entry that can
        apply to some or all of the representational elements of the entry.

        This class is only used during processing internal to the JMdict class.
        This information is then exposed publicly via the JMdictEntry class.

        Attributes:
            applicable_reprs: Tuple of representations of the entry that this
                sense applys to. If empty, applies to all reprs of the entry.
            parts_of_speech: Parts of speech that the entry can be.
            fields: The fields of application for this entry (e.g. food term,
                baseball term, etc.)
            dialect: The dialects that apply for this entry (e.g. kansaiben).
            misc: Other miscellaneous info recorded for this entry in JMdict.
        """
        applicable_elements: Tuple[str, ...] = None
        parts_of_speech: Tuple[str, ...] = None
        fields: Tuple[str, ...] = None
        dialects: Tuple[str, ...] = None
        misc: Tuple[str, ...] = None

    def __init__(self, jmdict_xml_filepath: str = None) -> None:
        self._entry_map = None
        self._mecab_decomp_map = None
        self._mecab_tagger = MecabTagger()

        if jmdict_xml_filepath is not None:
            self.load_jmdict(jmdict_xml_filepath)

    @utils.skip_method_debug_logging
    def _parse_entry_xml(
        self, entry: ElementTree.Element
    ) -> List[JMdictEntry]:
        """Parse all elements from a given JMdict XML entry.

        Because many Japanese words can be written using kanji as well as kana,
        there are often different ways to write the same word. JMdict entries
        include each of these representations as separate elements, so this
        function parses all of these elements plus the corresponding sense
        information and merges the info together into JMdictEntry objects.

        Args:
            entry: An XML entry element from a JMdict XML file.

        Returns:
            A list of all of the elements for the given entry.

        Raises:
            ResourceLoadError: The passed entry had malformed JMdict XML, so it
            could not be parsed.
        """
        repr_objs = []
        sense_objs = []
        for element in entry:
            if element.tag in self._REPR_ELEMENT_TAGS:
                repr_obj = JMdictEntry()
                self._parse_text_elements(
                    repr_obj, entry, [self._ENTRY_ID_TAG], required=True
                )
                self._parse_text_elements(
                    repr_obj, element, [self._REPR_TEXT_FORM_TAG[element.tag]],
                    required=True
                )
                self._parse_text_elements(
                    repr_obj, element, self._REPR_OPTIONAL_TAGS[element.tag],
                    required=False
                )
                repr_objs.append(repr_obj)

            elif element.tag == self._SENSE_ELEMENT_TAG:
                sense_obj = self._JMdictSense()
                self._parse_text_elements(
                    sense_obj, element, self._SENSE_OPTIONAL_TAGS,
                    required=False
                )
                sense_objs.append(sense_obj)

            elif element.tag != self._ENTRY_ID_TAG:
                entry_str = ElementTree.tostring(entry).decode('utf-8')
                utils.log_and_raise(
                    _log, ResourceLoadError,
                    f'Malformed JMdict XML. Unknown tag "{element.tag}" found '
                    f'with "{entry.tag}" tag: "{entry_str}"'
                )

        self._add_sense_data(repr_objs, sense_objs)
        return repr_objs

    @utils.skip_method_debug_logging
    def _add_sense_data(
        self, entries: List[JMdictEntry], senses: List['JMdict._JMdictSense']
    ) -> None:
        """Adds the data from the sense objs to the entry objs."""
        for sense in senses:
            for entry in entries:
                if (sense.applicable_elements is not None
                        and len(sense.applicable_elements) > 0
                        and entry.text_form not in sense.applicable_elements):
                    continue

                entry.parts_of_speech = sense.parts_of_speech
                entry.fields = sense.fields
                entry.dialects = sense.dialects
                entry.misc = sense.misc

    @utils.skip_method_debug_logging
    def _parse_text_elements(
        self, storage_obj: Any, parent_element: ElementTree.Element,
        element_tags: List[str], required: bool = False
    ) -> None:
        """Parses text-containing elements and stores the data in a object.

        Args:
            storage_obj: An object with attribute names mapped to by the
                _TAG_TO_OBJ_ATTR_MAP.
            parent_element: The XML element whose children to parse for the
                text-containing elements.
            element_tags: The tags of the elements to parse.
            required: If True, will raise an error if any of the elements are
                not found within the children of the parent element.

        Raises:
            ResourceLoadError: A required element was not found, or an element
                was found with no parsable text within it.
        """
        for tag in element_tags:
            if required:
                elements = self._find_all_raise_if_none(tag, parent_element)
            else:
                elements = parent_element.findall(tag)

            for ele in elements:
                self._raise_if_no_text(ele, parent_element)
                if tag in self._TUPPLE_TAGS:
                    self._append_to_tuple_attr(
                        storage_obj, self._TAG_TO_OBJ_ATTR_MAP[tag], ele.text
                    )
                else:
                    setattr(
                        storage_obj, self._TAG_TO_OBJ_ATTR_MAP[tag], ele.text
                    )

    @utils.skip_method_debug_logging
    def _append_to_tuple_attr(
        self, storage_obj: Any, attr_name: str, append_item: str
    ) -> None:
        """Creates new tuple for attr of storage object with item appended."""
        current_val = getattr(storage_obj, attr_name)
        if current_val is None:
            setattr(storage_obj, attr_name, (append_item,))
        else:
            setattr(storage_obj, attr_name, current_val + (append_item,))

    @utils.skip_method_debug_logging
    def _find_all_raise_if_none(
        self, tag: str, parent_element: ElementTree.Element
    ) -> List[ElementTree.Element]:
        """Finds all tag elements in parent, and raises error if none.

        Raises ResourceLoadError if no tag elements are found.
        """
        elements = parent_element.findall(tag)
        if len(elements) == 0:
            parent_str = ElementTree.tostring(parent_element).decode('utf-8')
            utils.log_and_raise(
                _log, ResourceLoadError,
                f'Malformed JMdict XML. No "{tag}" element within '
                f'"{parent_element.tag}" element: "{parent_str}"'
            )

        return elements

    @utils.skip_method_debug_logging
    def _raise_if_no_text(
        self, element: ElementTree.Element, parent_element: ElementTree.Element
    ) -> None:
        """Raises ResourceLoadError if no accessible text in element."""
        if element.text is not None and len(element.text) > 0:
            return

        parent_str = ElementTree.tostring(parent_element).decode('utf-8')
        utils.log_and_raise(
            _log, ResourceLoadError,
            f'Malformed JMdict XML. No accessible text within "{element.tag}" '
            f'element: "{parent_str}"'
        )

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
                f'JMdict file not found at "{_JMDICT_XML_FILEPATH}"'
            )

        _log.debug(f'Reading JMdict XML file at "{_JMDICT_XML_FILEPATH}"')
        tree = ElementTree.parse(xml_filepath)
        _log.debug('Reading of JMdict XML file complete')

        self._entry_map = defaultdict(list)
        self._mecab_decomp_map = defaultdict(list)
        root = tree.getroot()
        for entry_element in root:
            entry_objs = self._parse_entry_xml(entry_element)
            for entry_obj in entry_objs:
                mecab_decomp = self._get_mecab_decomb(entry_obj)
                self._mecab_decomp_map[mecab_decomp].append(entry_obj)
                self._entry_map[entry_obj.text_form].append(entry_obj)

    @utils.skip_method_debug_logging
    def _get_mecab_decomb(self, entry: JMdictEntry) -> Tuple[str, ...]:
        """Get the MeCab decomposition of the text form of the entry."""
        lexical_items = self._mecab_tagger.parse(entry.text_form)
        return tuple(item.base_form for item in lexical_items)

    def contains_entry(self, entry: Union[str, Tuple[str, ...]]) -> bool:
        """Tests if entry is in the JMdict entries.

        Args:
            entry: value to check for in the loaded JMdict entries. If a
                string, checks if an entry with that text form exists. If a
                tuple, checks if an entry with that Mecab decomposition exists.

        Returns:
            True if the entry is in the loaded JMdict entries, False otherwise.

        Raises:
            ResourceNotReadyError: JMdict data has not been loaded into this
                JMdict object yet.
        """
        if self._entry_map is None or self._mecab_decomp_map is None:
            utils.log_and_raise(
                _log, ResourceNotReadyError,
                'JMdict object used before loading any JMdict data.'
            )

        if isinstance(entry, str):
            return entry in self._entry_map
        return entry in self._mecab_decomp_map

    def __contains__(self, entry: Union[str, Tuple[str, ...]]) -> bool:
        """Simply calls self.contains_entry."""
        return self.contains_entry(entry)

    def get_entries(
        self, entry: Union[str, Tuple[str, ...]]
    ) -> List[JMdictEntry]:
        """Gets the list of JMdict entries that match the give entry.

        Args:
            entry: value to get matching JMdict entries for. If a string, gets
                entries with matching text form. If a tuple, gets entries with
                matching Mecab decomposition.

        Returns:
            A list of the matching JMdict entries.

        Raises:
            ResourceNotReadyError: JMdict data has not been loaded into this
                JMdict object yet.
        """
        if self._entry_map is None or self._mecab_decomp_map is None:
            utils.log_and_raise(
                _log, ResourceNotReadyError,
                'JMdict object used before loading any JMdict data.'
            )

        if isinstance(entry, str):
            return self._entry_map.get(entry, [])
        return self._mecab_decomp_map.get(entry, [])

    def __getitem__(
        self, entry: Union[str, Tuple[str, ...]]
    ) -> List[JMdictEntry]:
        """Simply calls self.get_entries."""
        return self.get_entries(entry)


@utils.flyweight_class
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
    _TOKEN_SPLITTER = '\t'
    _EXPECTED_TOKEN_TAG_COUNTS = {4, 5, 6}

    def __init__(self, use_default_ipadic: bool = False) -> None:
        """Inits the MeCab tagger wrapper.

        Unless use_default_ipadic is True, uses the ipadic-NEologd dictionary
        and will raise a ResourceLoadError if NEologd is not available on the
        system.

        Args:
            use_default_ipadic: If True, forces tagger to use the default
                ipadic dictionary instead of the ipadic-NEologd dictionary.
        """
        self._mecab_tagger = None

        if use_default_ipadic:
            self._mecab_tagger = MeCab.Tagger('-Ochasen')
        else:
            neologd_path = self._get_mecab_neologd_dict_path()
            self._mecab_tagger = MeCab.Tagger(f'-Ochasen -d {neologd_path}')

    @utils.skip_method_debug_logging
    def parse(self, text: str) -> List[FoundJpnLexicalItem]:
        """Returns the lexical items found by MeCab in the text.

        Raises:
            TextAnalysisError: MeCab gave an unexpected output when parsing the
                text.
        """
        mecab_out = self._mecab_tagger.parse(text)
        parsed_tokens = self._parse_mecab_output(mecab_out)

        found_lexical_items = []
        for parsed_token_tags in parsed_tokens:
            if (len(parsed_token_tags) == 1
                    and parsed_token_tags[0] == self._END_OF_SECTION_MARKER):
                continue

            if len(parsed_token_tags) not in self._EXPECTED_TOKEN_TAG_COUNTS:
                utils.log_and_raise(
                    _log, TextAnalysisError,
                    f'Unexpected number of MeCab tags '
                    f'({len(parsed_token_tags)}) for token '
                    f'{parsed_token_tags} in "{text}"'
                )

            found_lexical_item = FoundJpnLexicalItem(
                surface_form=parsed_token_tags[0],
                reading=parsed_token_tags[1],
                base_form=parsed_token_tags[2],
                parts_of_speech=parsed_token_tags[3].split(self._POS_SPLITTER)
            )
            if len(parsed_token_tags) >= 5:
                found_lexical_item.conjugated_type = parsed_token_tags[4]
            if len(parsed_token_tags) >= 6:
                found_lexical_item.conjugated_form = parsed_token_tags[5]

            found_lexical_items.append(found_lexical_item)

        return found_lexical_items

    @utils.skip_method_debug_logging
    def _parse_mecab_output(self, output: str) -> List[List[str]]:
        """Parses the individual tags from MeCab chasen output.

        Args:
            output: MeCab chasen output.

        Returns:
            A list where each entry is a list of the tokens parsed from one
            line of the output.
        """
        parsed_tokens = []
        for line in output.splitlines():
            if len(line) == 0:
                continue
            tokens = line.split(self._TOKEN_SPLITTER)

            # Very rarely, MeCab will give a blank base form for some proper
            # nouns. In these cases, set the base form to be the same as the
            # surface form.
            if (len(tokens) >= 3
                    and len(tokens[2]) == 0
                    and tokens[0] == tokens[1]):
                tokens[2] = tokens[0]

            tokens = [t for t in tokens if len(t) > 0]
            parsed_tokens.append(tokens)

        return parsed_tokens

    def _get_mecab_neologd_dict_path(self) -> str:
        """Finds the path to the NEologd dict in the system.

        Returns:
            The path to the directory containing the NEologd dictionary.

        Raises:
        """
        output = subprocess.run(
            ['mecab-config', '--version'], capture_output=True
        )
        if output.returncode != 0:
            utils.log_and_raise(
                _log, ResourceLoadError,
                'MeCab is not installed on this system, so the '
                'mecab-ipadic-NEologd dictionary cannot be used'
            )

        output = subprocess.run(
            ['mecab-config', '--dicdir'], capture_output=True
        )
        if output.returncode != 0:
            utils.log_and_raise(
                _log, ResourceLoadError,
                'MeCab dictionary directory could not be retrieved, so the '
                'mecab-ipadic-NEologd dictionary cannot be used'
            )

        neologd_path = os.path.join(
            output.stdout.decode(sys.stdout.encoding).strip(),
            self._MECAB_NEOLOGD_DIR_NAME
        )
        if not os.path.exists(neologd_path):
            utils.log_and_raise(
                _log, ResourceLoadError,
                'mecab-ipadic-NEologd is not installed on this system, so the '
                'mecab-ipadic-NEologd dictionary cannot be used'
            )

        return neologd_path
