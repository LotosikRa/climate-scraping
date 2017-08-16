from scrapinghub import ScrapinghubClient
from scrapinghub.client.spiders import Spider

from .args import config

import time
import datetime


class CloudInterface:
    """
    Uses `scrapinghub.ScrapinghubClient` class to use Scrapy CLoud API.
    It is expected that it is used only for one spider current running spider,
    and uses only it's resources (job history).
    """

    def __init__(self):
        self.client = ScrapinghubClient(config.api_key)
        self.project = self.client.get_project(config.current_project_id)
        self.spider = self._get_current_spider()

    def _get_current_spider(self) -> Spider:
        """
        Iterates over project's spiders and compares their keys with current.
        :return: `scrapinghub.client.spiders.Spider` object that represents
        currently running spider.
        """
        for spider_dict in self.project.spiders.list():
            spider = self.project.spiders.get(spider_dict['id'])
            if spider.key.split('/')[1] == config.current_spider_id:
                return spider
        else:
            raise RuntimeError('No spider found.')

    def _fetch_week_jobs(self):
        """
        Fetches from Scrapy Cloud all current spider's jobs finished on the
        last week.
        :return: generator of `scrapinghub.client.jobs.Job` objects
        """
        delta_seconds = datetime.timedelta(weeks=1).total_seconds() + 60 * 60
        week_ago = int((time.time() - delta_seconds) * (10 ** 3))
        for job_summary in self.spider.jobs.iter(startts=week_ago,
                                                 state='finished',
                                                 jobmeta=['key']):
            yield self.project.jobs.get(job_summary['key'])

    def fetch_week_items(self):
        """
        Fetches from Scrapy Cloud all items produced by current spider on the
        last week at finished jobs.
        :return: generator of `dict` objects
        """
        for job in self._fetch_week_jobs():
            yield from job.items.iter()

    def fetch_week_indexes(self):
        """
        Generates `str` objects that are in the "index" field of items fetched
        in `_fetch_week_job` method.
        :return: generator of `str` objects
        """
        for item in self.fetch_week_items():
            yield item['index']
