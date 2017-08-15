import logging

from .item import ArticleItem
from .args import options
from .cloud import CloudInterface
from .spider import SingleSpider, TestingSpider
from .storage import StorageMaster, StorageSession


def _to_boolean(option: str) -> bool:
    if option in ['True', '1']:
        return True
    elif option in ['False', '0']:
        return False
    else:
        raise RuntimeError('Cannot recognise argument value: {}'
                           .format(option))


ENABLE_STORAGE = _to_boolean(options.enable_gspread)
USE_CLOUD = _to_boolean(options.use_cloud)


class StoragePipeline(object):

    def __init__(self):
        self.storage_session = None
        self.cloud = None

    def open_spider(self, spider: SingleSpider):
        if USE_CLOUD:
            if isinstance(spider, SingleSpider):
                self.cloud = CloudInterface()
                spider.connect_cloud(self.cloud)
            elif isinstance(spider, TestingSpider):
                pass
        if ENABLE_STORAGE:
            self.storage_session = StorageSession(
                StorageMaster().get_worksheet_by_spider(spider), spider)
            self.storage_session.open_session()

    def close_spider(self, spider: SingleSpider):
        if self.storage_session:
            self.storage_session.close_session()

    def process_item(self, item: ArticleItem, spider: SingleSpider):
        if isinstance(item, ArticleItem):
            if self.storage_session:
                self.storage_session.append_item(item)
            return item
        else:
            msg = 'Unknown item type: ' + item.__repr__()
            logging.warning(msg)
            print('WARNING ::', msg)
            return item
