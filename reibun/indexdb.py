"""Handles CRUD operations with the article index.

The public members of this module are defined generically so that the
implementation of the article index can be changed freely while the access
interface remains consistent.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Article:
    """Contains the text and metadata for a given text article.

    Attributes:
        title: The title of the article.
        body_text: The full body text of the article. Does not include the
            title.
        character_count: The total count of the alphanumeric characters within
            the title and body of the article.
        source_url: The fully qualified URL where the article was found.
        source_name: The human-readable name of the source of the article.
        publication_datetime: The UTC datetime the article was published.
        scraped_datetime: The UTC datetime the article was scraped.
    """
    title: str = None
    body_text: str = None
    character_count: int = None
    source_url: str = None
    source_name: str = None
    publication_datetime: datetime = None
    scraped_datetime: datetime = None
