import logging
from datetime import datetime

import gspread
import scrapy
from oauth2client.service_account import ServiceAccountCredentials as Creds

from scrapy_climate import settings as s
from .args import options


def _to_bool(string: str) -> bool:
    if string in ['True', '1']:
        return True
    elif string in ['False', '0']:
        return False
    else:
        raise ValueError('Unknown string value: ' + string)


class StorageMaster:

    secret_file_name = s.GOOGLE_API_SECRET_FILENAME

    sheet_name = options.spreadsheet_title
    spider_to_worksheet_dict = options.spider_to_worksheet_dict

    def __init__(self):
        self._path_to_secret = options.path_to_config_file(self.secret_file_name)
        self._credentials = self._get_credentials()
        self._client = self._get_client()
        self.spreadsheet = self._client.open(self.sheet_name)

    def _get_credentials(self) -> Creds:
        return Creds.from_json_keyfile_name(
            self._path_to_secret, ['https://spreadsheets.google.com/feeds'])

    def _get_client(self) -> gspread.Client:
        return gspread.authorize(self._credentials)

    def get_worksheet_by_spider(self, spider: scrapy.spiders.Spider) -> gspread.Worksheet:
        try:
            index = self.spider_to_worksheet_dict[spider.name]
        except KeyError:
            raise RuntimeError('No worksheet configured for this spider: {}'.format(spider.name))
        try:
            worksheet = self.spreadsheet.get_worksheet(index)
            assert worksheet is not None
        except AssertionError:
            raise RuntimeError('No worksheet exist for this spider: {}/{}'.format(spider.name, index))
        return worksheet


class StorageSession:

    empty_cell = '-----'
    open_template = options.storage_open_format
    close_template = options.storage_close_format
    date_format = options.storage_datefmt

    open_line = _to_bool(options.storage_close_line)
    close_line = _to_bool(options.storage_open_line)

    def __init__(self, worksheet: gspread.Worksheet, spider: scrapy.spiders.Spider):
        self._spider = spider
        self._worksheet = worksheet
        self._rows = None
        self._job_url = 'https://app.scrapinghub.com/p/{project_id}/{spider_id}/{job_id}'.format(
            project_id=options.current_project_id,
            spider_id=options.current_spider_id,
            job_id=options.current_job_id,
        )

    def open_session(self):
        logging.debug('<<< Session for #{spider_id} spider in "{worksheet_title}" worksheet STARTed.'.format(
            spider_id=options.current_spider_id,
            worksheet_title=self._worksheet.title,
        ))
        if self.open_line:
            self._add_starting_row()
        self._rows = []
        return self

    def append_item(self, item: scrapy.item.Item) -> None:
        self._rows.append(Row(item).as_list())

    def close_session(self) -> None:
        if self.close_line:
            self._add_close_row()
        self._write_data()
        logging.debug('>>> Session for #{spider_id} spider in "{worksheet_title}" worksheet ENDed.'.format(
            spider_id=options.current_spider_id,
            worksheet_title=self._worksheet.title,
        ))

    def _write_data(self) -> None:
        for row in self._rows:
            self._worksheet.append_row(row)

    def _add_starting_row(self):
        self._worksheet.append_row(Row(
            url=self.empty_cell,
            header=self.open_template.format(
                date=self._datetime(),
                name=self._spider.name,
            ),
            tags=self._job_url,
            text=self.empty_cell,
            date=self.empty_cell,
            index=self.empty_cell,
        ).as_list())

    def _add_close_row(self):
        self._rows.append(Row(
            url=self.empty_cell,
            header=self.close_template.format(
                date=self._datetime(),
                count=str(len(self._rows)),
            ),
            tags=self._job_url,
            text=self.empty_cell,
            date=self.empty_cell,
            index=self.empty_cell,
        ).as_list())

    def _datetime(self):
        return datetime.now().strftime(self.date_format)


class Row:
    """ Place to configure fields order in a table"""

    columns_order = ['url', 'header', 'tags', 'text', 'date', 'index']
    hyperlink_template = '=HYPERLINK("{link}";"{text}")'
    format_hyperlinks = False
    empty_cell = '- - -'

    def __init__(self, item: scrapy.item.Item or dict = None,
                 url: str = empty_cell,
                 header: str = empty_cell,
                 tags: str = empty_cell,
                 text: str = empty_cell,
                 date: str = empty_cell,
                 index: str = empty_cell):
        if item is not None:
            self.item = item
        else:
            self.item = dict(url=url, header=header, tags=tags,
                             text=text, date=date, index=index,)

    def as_list(self) -> list:
        lst = []
        for column in self.columns_order:
            value = self.item[column]
            if column in ['text'] and self.format_hyperlinks:
                value = self.format_hyperlink(value)
            lst.append(value)
        return lst

    def format_hyperlink(self, string: str) -> str:
        # TODO: use `regex`
        try:
            text_open = string.find('[')
            text_close = text_open + string[text_open:].find(']')
            link_open = text_close + 1
            link_close = link_open + string[link_open:].find(')')
            assert -1 < text_open < text_close < link_open < link_close
            assert string[link_open] == '('
            text = string[text_open + 1: text_close]
            link = string[link_open + 1: link_close]
            string_before = string[:text_open]
            string_after = string[link_close + 1:]
            hyperlink = self.hyperlink_template.format(link=link, text=text)
            new_string = string_before + hyperlink + string_after
        except AssertionError:
            return string
        else:
            return new_string
