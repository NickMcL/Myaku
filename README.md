# Myaku: Learning Japanese _from Context_

[![Build Status](https://travis-ci.org/FriedRice/Myaku.svg?branch=master)](https://travis-ci.org/FriedRice/Myaku)

A search engine for finding high quality Japanese news and blog articles on the
web that show native usage of a searched Japanese term to assist in learning
Japanese.

Live now at [myaku.org](https://myaku.org).

## What can Myaku do?

Searching for any Japanese term on Myaku will return a ranked list of links to
news and blog articles that demonstrate _when_ and _where_ Japanese people use
that term.

These articles can then be read to build a deeper and more natural
understanding for how the searched term is used in Japanese than can be
gained from looking at definitions or sample sentences alone.

To make finding high quality articles for learning easier, the article links
returned for a search are ranked using a scoring system with a variety of
different factors such as publication recency, blog/news article rating, article
length, and more so that the highest qualiy articles are at the top of the
search results.

Additionally, beyond just individual words, Myaku can also be used to search for
articles demonstrating usage of more complex bits of language such as set
phrases, sayings, idioms, and more!

For an explanation of the benefits of using Myaku to search for Japanese
articles for learning instead of a normal searche engine such as Google, check
out [this page][1] in the Myaku project wiki.


## Myaku Project Architecture

All components of the Myaku project are containerized and run as Docker services,
and a single Docker Swarm stack is used to deploy all of those services (except
the test runner). See the Docker compose files and other configuration files in
the [docker][2] directory for full details on this configuration.

Here are brief overviews of the most important services in the project:

### Crawler

Web crawler that routinely crawls articles from a small set of Japanese news and
blog websites to build the search index for Myaku. Also handles the Japanese
analysis and quality scoring of crawled articles.

Implemented in the myaku Python module (see the [myaku][3] module directory).
Uses MongoDB for storage of the search index as well as Redis for caching search
result pages.

#### Search Index MongoDB Database

MongoDB database for storing the search index and associated data created by the
Crawler service.

### MyakuWeb Search API

REST API for making searches for articles using the search index.

Implemented with Python using Django (see the [myakuweb-apiserver][4] directory).
Uses celery for async tasks and Redis for caching search results. Served using
uWSGI.

### Search Index Redis Caches

Redis caches used by the MyakuWeb Search API and Crawler services to cache search
results for faster retreival than query the full search index stored with MongoDB.

The project uses two Redis caches. One is used to perputually cache the first page
of search results for every search query so that the first page can always be
retreived quickly, and the other is used to preemptively cache pages of search
results that are likely to be requested by a user based on their recent requests.

### Nginx Reverse Proxy Server

Nginx server that serves as the entrypoint for all external requests to one of the
project's services.

Handles forwarding search API requests to the search API service, and directly
handles serving the static file requests for the MyakuWeb React client app.

The React client app itself is implemented in TypeScript (see the
[myakuweb-clientapp][5] directory).

### Article Rescorer

Service that periodically runs a task to update the quality scores of articles in
the search index. This periodic rescoring is necessary because how well articles
score for some score factors such as publication recency changes over time causing
the quality score of previously crawled articles to change since they were first
indexed.

Implemented in the myaku Python module (see the [myaku][3] module directory).

### Search Index Backup Service

Service that periodically creates a full backup of the search index MongoDB
database and uploads it to AWS S3.

Implemented as a Python script (see the [docker/mongobackup][6] directory).

### Test Runner

Runner for all of the test suites for all of the different components of the
project. This includes running the PyTest tests for the Python myaku module, the
Jest tests for the MyakuWeb React client app, and the Selenium tests for the
delivery and rendering of the client app.

Implemented as a Python script (see the [docker/myaku_run-tests][7] directory).

## License Info

Myaku is licensed under the GNU Affero General Public License v3.0 license.

Myaku uses the [JMdict][8] dictionary files in accordance with the
[licence provisions][9] of the [Electronic Dictionaries Research Group][10].

[1]: https://github.com/FriedRice/Myaku/wiki/Why-not-just-use-a-normal-web-search-engine-like-Google%3F
[2]: https://github.com/FriedRice/Myaku/tree/master/docker
[3]: https://github.com/FriedRice/Myaku/tree/master/myaku
[4]: https://github.com/FriedRice/Myaku/tree/master/myakuweb-apiserver
[5]: https://github.com/FriedRice/Myaku/tree/master/myakuweb-clientapp
[6]: https://github.com/FriedRice/Myaku/tree/master/docker/mongobackup
[7]: https://github.com/FriedRice/Myaku/tree/master/docker/myaku_run-tests
[8]: http://www.edrdg.org/jmdict/j_jmdict.html
[9]: http://www.edrdg.org/edrdg/licence.html
[10]: http://www.edrdg.org/
