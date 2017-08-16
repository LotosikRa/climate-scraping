from scrapy_climate.tools.spider import TestingSpider


class TSpider(TestingSpider):

    name = 'testing'
    start_urls = ['http://httpbin.org']
