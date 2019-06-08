"""Classes for holding data used across the Reibun project."""

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class FoundLexicalItem(object):
    """A single lexical item found within a block of text.

    In the following descriptions, 'text' refers to the text block where the
    lexical item was found.

    Attributes:
        base_form: The base (dictionary) form of the lecixal item.
        surface_form: The form the lexical item used within the text.
        text_pos_abs: The zero-indexed alnum character offset of the start of
            the lexical item from the start of the text.
        text_pos_percent: The percent of the total alnum characters in the text
            ahead of the lecixal item.
        parts_of_speech: The parts of speech of the lexical item. Possibly
            multiple, so it is a list.
    """
    base_form: str
    surface_form: str
    text_pos_abs: int
    text_pos_percent: float
    parts_of_speech: List[str] = None

    def __str__(self) -> str:
        """Returns all memebers in a string format."""
        return '{}--{}--{}--{.1%}--{}'.format(
            self.base_form,
            self.surface_form,
            self.text_pos_abs,
            self.text_pos_percent,
            self.part_of_speech
        )


@dataclass
class Article(object):
    """The text and metadata for a text article.

    Attributes:
        title: The title of the article.
        full_text: The full text of the article. Includes the title.
        alnum_count: The total count of the alphanumeric characters within
            the full text of the article.
        source_url: The fully qualified URL where the article was found.
        source_name: The human-readable name of the source of the article.
        publication_datetime: The UTC datetime the article was published.
        scraped_datetime: The UTC datetime the article was scraped.
        found_lexical_items: All of the lexical items found within the article.
    """
    title: str = None
    full_text: str = None
    alnum_count: int = None
    source_url: str = None
    source_name: str = None
    publication_datetime: datetime = None
    scraped_datetime: datetime = None

    found_lexical_items: List[FoundLexicalItem] = None

    def __str__(self) -> str:
        """Returns the title and publication time in string format."""
        return '{}--{}'.format(
            self.title,
            self.publication_datetime.isoformat()
        )
