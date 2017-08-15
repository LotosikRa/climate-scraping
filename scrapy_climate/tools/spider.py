# -*- coding: utf-8 -*-
""" Module for spider class templates.

    Entities:
    * news-list page - page on the web-site that have HTML tag (e. g.
    "news-list tag") with multiple childes, where every child HTML tag
    contains a link to an "article page"
    * news-list tag - HTML tag  with multiple childes, where every child HTML
    tag contains a link to an "article page"
    * article page - page on the same web-site that have HTML tag (e. g.
    "article tag") with childes that have all needed data as header, tags etc.
    * article tag - HTML tag  with childes that have all data for scraping
    * index - part of the article page URL that can be used to identify the
    article page to not scrape it twice
    * callback - method which takes request and yields another request or item
"""

import random
import logging
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import requests

from scrapy import Spider
from scrapy.http import Response, Request

from .item import ArticleItem
from .cloud import CloudInterface
from .parser import Parser, MediaCounter, ElementsChain
from .storage import COLUMNS_TUPLE
from .extractor import (
    CSSExtractor,
    LinkExtractor,
    TextExtractor,
    HeaderExtractor,
    TagsExtractor,
    VoidExtractor,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

LOCAL_EMPTY_INDEX = 'LocalEmptyIndex'


class IndexesContainer(frozenset):

    def __repr__(self):
        return '<Indexes: {}>'.format(self)

    def __str__(self):
        return ', '.join(self)


class ProxyManager:

    list_of_proxies_url = 'https://proxy-spider.com/api/proxies.example.txt'

    def __init__(self):
        response = requests.get(self.list_of_proxies_url)
        if response.status_code != 200:
            raise RuntimeError('Can not retrieve list of proxies')
        self.text = response.content.decode('utf-8')
        self.proxies = tuple(self.parse(self.text))

    @classmethod
    def parse(cls, text):
        yield from text.split('\n')

    @property
    def random(self):
        i = random.randint(0, len(self.proxies)-1)
        return self.proxies[i]


class ExtractManager:

    def __init__(self, link_extractor: LinkExtractor =None,
                 header_extractor: HeaderExtractor =None,
                 text_extractor: TextExtractor =None,
                 tags_extractor: TagsExtractor =None, ):
        self._check_type('link_extractor', link_extractor, LinkExtractor)
        self._check_type('header_extractor', header_extractor, HeaderExtractor)
        self._check_type('text_extractor', text_extractor, TextExtractor)
        self._check_type('tags_extractor', tags_extractor, TagsExtractor)

    def _check_type(self, name: str, variable, parent: type):
        if isinstance(variable, VoidExtractor):
            logger.warning(
                '`{}` initialised with `extractor.VoidExtractor` '
                'class and will not return any useful data.'.format(name))
        elif not isinstance(variable, parent):
            raise TypeError('Passed `{}` variable must be `{}` type.'
                            .format(name, parent.__class__))
        self.__setattr__(name, variable)


class SingleSpider(Spider):
    """
    This class must not be used properly, only for inheritance.

    It implements Scrapy spider callbacks for scraping articles from news-like
    web-site, without duplicates (see `fetch_scraped_indexes` function in the
    `tools` module.)

    What must be implemented for usage?
    * class fields: `name`, `_start_path`, `_start_domain`, `_scheme`
    * methods: `_convert_path_to_index`

    How it works at all:
    1. first request is to `start_urls`'s first (and only) URL, that depends
    on `_start_path` and `_start_domain` and `_scheme` class fields.
    2. `parse` callback spider calls `fetch_scraped_indexes` to get
    list of scraped yet articles and stores it
    3. then `_yield_requests_from_response` extracts links to "article pages"
    from response by calling `_find_news_list_in_response` to locate the
    "news-list tag" and `_extract_ul_or_path` to get URL or path to an
    "article page" that passes to `_yield_request` method
    4. `_yield_request` method parses given `url_or_path` argument to yield
    request to "article page" with `parse_article` callback
    5. `parse_article` finds `article` selector and passes extracted header,
    tags etc. to `_yield_article_item` method
    6. `_yield_article_item` method ads to item arguments that can be
    extracted just from response.
    """

    # Just a spider name used by Scrapy to identify it.
    # Must be a string.
    name = None

    # URL path to the "news-list page". Used for `start_urls` field.
    # Must be a string. Minimal value: ''
    _start_path = None

    # URL host of the web-site. Used for `allowed_domains` field.
    # Must be a string. Example: 'www.example.com'
    _start_domain = None

    # URL scheme. Allowed values: 'http', 'https'
    _scheme = None

    # Extractors used to extract needed data from HTML
    # Must be `Extractor` instances.
    _link_extractor = None
    _header_extractor = None
    _tags_extractor = None
    _text_extractor = None

    _extract_manager = None

    _article_item_class = ArticleItem
    _date_format_template = '%d %B %Y'

    _use_proxy = False
    _default_request_meta = {}

    def __init__(self, *args, **kwargs):
        self.cloud = None
        self._scraped_indexes = frozenset()
        # call it to check
        self.extract_manager
        # check proxy
        if self._use_proxy:
            self.proxy_manager = ProxyManager()
        super().__init__(*args, **kwargs)

    def connect_cloud(self, cloud: CloudInterface):
        """
        binds `cloud` argument as `cloud` attribute and calls it's
        `fetch_week_indexes` method to store the result as list in
        `_scraped_indexes` attribute to use it the future for filtering
        duplicates.
        :param cloud: instance of `cloud.CloudInterface`
        :return: None
        """
        self.cloud = cloud
        # use `frozenset` here because we will iterate over
        # `self._scraped_indexes` many times and iterating right now might
        # reduce the traffic
        self._scraped_indexes = IndexesContainer(cloud.fetch_week_indexes())
        # log it
        logger.info('Scraped indexes: {};'.format(self._scraped_indexes))

    # =================
    #  "parse" methods
    # =================
    # there are "callbacks" that scrapes data from page (response)
    def parse(self, response: Response):
        """
        "callback" for "news-list page" that yields requests to "article pages"
        with `parse_article` "callback".
        :param response: `scrapy.http.Response` from "news-list page"
        :return: yields requests to "article pages"
        """
        # parse response and yield requests with `parse_article` "callback"
        yield from self._yield_requests_from_response(response)

    def parse_article(self, response: Response):
        """
        "callback" for "article page" that yields `ArticleItem` items.
        :param response: `Scrapy.http.Response` instance from "article page"
        :return: yields `ArticleItem` instance
        """
        logger.info('Started extracting from {}'.format(response.url))
        order = [
            ('text', self._text_extractor),
            ('header', self._header_extractor),
            ('tags', self._tags_extractor),
        ]
        kwargs = {}
        for name, extractor in order:
            extracted = extractor.safe_extract_from(response)
            kwargs[name] = extracted
        # produce item
        yield from self._yield_article_item(response, **kwargs)

    # ============
    #  generators
    # ============
    # these methods are used to yield requests of items
    def _yield_request(self, path_or_url: str):
        """
        Yields `scrapy.http.Request` with `parse_article` "callback" and meta
        "index" if "index" wasn't scraped yet. Method checks if passed
        `path_or_url` argument is an URL or URL path, but in both cases method
        know both URL and path, because URL is required to instantiate request
        and path is required to extract "index" from it.
        :param path_or_url: URL itself or URL path
        :return: yields `scrapy.http.Request` with `parse_article` "callback"
        """
        if '://' in path_or_url:
            url = path_or_url
            path = urlparse(url)[2]
        else:
            path = path_or_url
            url = urlunparse([self._scheme, self._start_domain, path,
                              None, None, None])
        index = self._convert_path_to_index(path)
        if index not in self._scraped_indexes:
            meta = self.request_meta
            meta.update({'index': index})
            yield Request(url=url,
                          callback=self.parse_article,
                          meta=meta)

    def _yield_requests_from_response(self, response: Response):
        """
        Parses response from "news-list page" and yields requests to
        "article pages" that aren't scraped yet.
        :param response: `scrapy.http.Response` from "news-list page"
        :return: yield `scrapy.http.Request` instance
        """
        for link in self._link_extractor.safe_extract_from(response):
            yield from self._yield_request(link)

    def _yield_article_item(self, response: Response, **kwargs):
        """
        Yields `ArticleItem` instances with `url` and `index` arguments
        extracted from given `response` object.
        :param response: `scrapy.http.Response` from "article page"
        :param kwargs: fields for `ArticleItem`
        :return: yields `ArticleItem` instance
        """
        try:
            index = response.meta['index']
        except KeyError:
            # case when used with `crawl` command
            index = LOCAL_EMPTY_INDEX
        yield self._article_item_class(
            url=response.url,
            index=index,
            date=self._format_date(),
            **kwargs
        )

    # ============
    #  properties
    # ============
    # these properties checks if child class has implemented all needed fields
    @property
    def allowed_domains(self):
        return [self._check_field_implementation('_start_domain'), ]

    def start_requests(self):
        url = '{}://{}/{}'.format(
            self._check_field_implementation('_scheme'),
            self._check_field_implementation('_start_domain'),
            self._check_field_implementation('_start_path'))
        request = Request(url, callback=self.parse, meta=self.request_meta)
        yield request

    @property
    def request_meta(self):
        meta = self._default_request_meta.copy()
        if self._use_proxy:
            meta.update({'proxy': self.proxy_manager.random})
        return meta

    @property
    def extract_manager(self):
        extractors = [self._text_extractor, self._tags_extractor,
                self._header_extractor, self._link_extractor]
        if isinstance(self._extract_manager, ExtractManager):
            return self._extract_manager
        elif all(extractors):
            return ExtractManager(
                link_extractor=self._link_extractor,
                header_extractor=self._header_extractor,
                tags_extractor=self._tags_extractor,
                text_extractor=self._text_extractor,
            )
        else:
            raise RuntimeError('nor `_extract_manager` nor `_*_extractor` '
                               'are not defined.')

    # =========
    #  helpers
    # =========
    def _format_date(self):
        now = datetime.now()
        return now.strftime(self._date_format_template)

    def _convert_path_to_index(self, path: str) -> str:
        """
        Extracts "index" (see entities in the `TemplateSpider` class'
        docstring) from given URL path.
        :param path: URL path string
        :return: `index` string
        """
        raise NotImplementedError

    def _check_field_implementation(self, field_name: str):
        """
        Checks if class have implemented field (attribute) with given name
        (string value of `field_name`)
        :param field_name: string that matches class field name
        :raises NotImplementedError: if class doesn't have implemented field
        with `field_name` name
        :return: value if field value isn't `None`, else raises exception
        """
        value = self.__getattribute__(field_name)
        if value is not None:
            return value
        else:
            raise NotImplementedError('Need to define "{}" field.'
                                      .format(field_name))


class TestingSpider(Spider):

    _message = 'testing'

    def parse(self, response: Response):
        yield ArticleItem(**{key: self._message for key in COLUMNS_TUPLE})
