import json
import os
import sys

from scrapy_climate import settings as s


JOBKEY_DEFAULT = '0/0/0'
_DEVMODE = 'DEVMODE'
_STORAGE_DATEFMT = 'STORAGE_DATEFMT'
_STORAGE_OPEN_FORMAT = 'STORAGE_OPEN_FORMAT'
_STORAGE_CLOSE_FORMAT = 'STORAGE_CLOSE_FORMAT'
_STORAGE_OPEN_LINE = 'STORAGE_OPEN_LINE'
_STORAGE_CLOSE_LINE = 'STORAGE_CLOSE_LINE'


class ArgumentsMaster:
    """ Class for control of given at start arguments, and some environment
    variables. Arguments can be get from spider too.
    **NOTE**: contains only `str` objects."""

    jobkey_env_varname = 'SHUB_JOBKEY'
    options_filename = s.OPTIONS_FILENAME

    def __init__(self):
        self._args_dict = self._parse_arguments()
        self._file_dict = self._parse_file()
        self._shub_jobkey = self._jobkey_handle()

    def get_value(self, key: str,
                  args_only: bool =False,
                  json_only: bool =False,
                  required: bool =True,
                  default=None):
        try:
            from_args = self._args_dict[key]
        except KeyError:
            args_exist = False
        else:
            args_exist = True
        try:
            from_json = self._file_dict[key]
        except KeyError:
            json_exist = False
        else:
            json_exist = True
        # value from `args` must overwrite value fro json
        if args_exist and not json_only:
            return from_args
        elif json_exist and not args_only:
            return from_json
        elif not required:
            return default
        else:
            raise RuntimeError('Unable to find expected argument: ' + key)

    def _jobkey_handle(self):
        from_env = os.getenv(self.jobkey_env_varname, None)
        from_args = self._args_dict.get(_DEVMODE, None)
        if from_env is not None:
            value = from_env
        elif from_args is not None:
            value = from_args
        else:
            value = JOBKEY_DEFAULT
        tupl = value.split('/')
        return {
            'CURRENT_PROJECT_ID': tupl[0],
            'CURRENT_SPIDER_ID': tupl[1],
            'CURRENT_JOB_ID': tupl[2],
        }

    def _parse_arguments(self) -> dict:
        arguments = sys.argv
        dictionary = {}
        for i in range(len(arguments)):
            if arguments[i] == '-a':
                args = arguments[i+1].split('=')
                dictionary[args[0]] = args[1]
        return dictionary

    def _parse_file(self) -> dict:
        return json.load(open(self.path_to_config_file(self.options_filename), 'r'))

    @staticmethod
    def path_to_config_file(file_name: str) -> str:
        # function that returns parent directory for given path
        def p(path):
            return os.path.abspath(os.path.join(path, os.pardir))
        # 3 times up
        return os.path.join(p(p(p(__file__))), file_name)

    @property
    def current_project_id(self) -> str:
        return self._shub_jobkey['CURRENT_PROJECT_ID']

    @property
    def current_spider_id(self) -> str:
        return self._shub_jobkey['CURRENT_SPIDER_ID']

    @property
    def current_job_id(self) -> str:
        return self._shub_jobkey['CURRENT_JOB_ID']

    @property
    def enable_gspread(self) -> str:
        return self.get_value('ENABLE_GSPREAD', args_only=True,
                              default='True', required=False)

    @property
    def spreadsheet_title(self) -> str:
        return self.get_value('SPREADSHEET_TITLE', json_only=True)

    @property
    def spider_to_worksheet_dict(self) -> str:
        return self.get_value('SPIDERS', json_only=True)

    @property
    def storage_open_format(self) -> str:
        return self.get_value(
            _STORAGE_OPEN_FORMAT,
            default='{date} / START "{name}" spider',
            required=False)

    @property
    def storage_close_format(self) -> str:
        return self.get_value(
            _STORAGE_CLOSE_FORMAT,
            default='{date} / {count} articles scraped',
            required=False)

    @property
    def storage_datefmt(self) -> str:
        return self.get_value(
            _STORAGE_DATEFMT,
            default='%d.%m %a %H:%M',
            required=False)

    @property
    def storage_open_line(self) -> str:
        return self.get_value(
            _STORAGE_OPEN_LINE,
            default='True',
            required=False
        )

    @property
    def storage_close_line(self) -> str:
        return self.get_value(
            _STORAGE_CLOSE_LINE,
            default='True',
            required=False
        )

    @property
    def use_cloud(self) -> str:
        return self.get_value(
            'USE_CLOUD',
            default='True',
            required=False,
            args_only=True,
        )

    @property
    def api_key(self) -> str:
        return self.get_value('SCRAPY_CLOUD_API_KEY')


options = ArgumentsMaster()
