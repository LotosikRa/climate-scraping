import logging

from scrapy.selector import SelectorList
from scrapy.http import HtmlResponse


logger = logging.getLogger(__name__)


class Middleware:

    _output_type = None
    _input_type = None

    def __init__(self, function, args: tuple =(), kwargs: dict ={},
                 input_type: type =None, output_type: type =None):
        if not isinstance(args, tuple):
            raise TypeError('Given `args` are not `tuple` object.')
        if not isinstance(kwargs, dict):
            raise TypeError('Given `kwargs` are not `dict` object.')
        self.function = function
        self.args = args
        self.kwargs = kwargs
        if not input_type:
            self.input_type = self._input_type
        else:
            self.input_type = input_type
        if not output_type:
            self.output_type = self._output_type
        else:
            self.output_type = output_type

    def call(self, input_value):
        self._check_input(input_value)
        output_value = self.function(input_value, *self.args, **self.kwargs)
        self._check_output(output_value)
        return output_value

    def _check_input(self, value):
        self._check_type(value, self.input_type, 'Input')

    def _check_output(self, value):
        self._check_type(value, self.output_type, 'Output')

    def _check_type(self, value, expected: type, action: str ='Given'):
        if self._is_wrong_type(value, expected):
            self._raise_type_error(action, value, expected)

    def _is_wrong_type(self, value, expected: type):
        return expected is not None and not isinstance(value, expected)

    def _raise_type_error(self, action: str, value, expected_type: type):
        raise TypeError(
            '{action} value type is {actual}, but not {expected}'.format(
                action=action, actual=type(value), expected=expected_type))


class MiddlewaresContainer(list):

    _items_type = 'middleware.Middleware'

    def __init__(self, middlewares: list):
        for middleware in middlewares:
            self._check_type(middleware)
        super().__init__(middlewares)

    def process(self, value):
        for middleware in self:
            value = middleware.call(value)
        else:
            return value

    def _check_type(self, object):
        if not isinstance(object, Middleware):
            raise TypeError('is not `{}` object.'.format(self._items_type))

    def append(self, object):
        self._check_type(object)
        super().append(object)


class SelectMiddleware(Middleware):

    _input_type = SelectorList
    _output_type = SelectorList
SMW = SelectMiddleware


class HTMLMiddleware(Middleware):

    _input_type = HtmlResponse
    _output_type = SelectorList


# ====================
#  actual middlewares
# ====================
def select(selector: SelectorList, string_selector: str) -> SelectorList:
    return selector.css(string_selector)


def childes(selector: SelectorList,
            parent_tag: str,
            child_tag: str ='',
            no_selector_string: str =None) -> SelectorList:
    if not isinstance(child_tag, str):
        raise TypeError('Given `child_tag` is not `str` object.')
    if not isinstance(parent_tag, str):
        raise TypeError('Given `parent_tag` is not `str` object.')
    if no_selector_string is not None and not isinstance(no_selector_string, str):
        raise TypeError('Given `no_selector_string` is not `str` object.')
    childes = []
    started_iteration = False
    i = 1
    # prepare string_selector
    string_selector_template = '{parent_tag} > {child_tag}'.format(
        parent_tag=parent_tag, child_tag=child_tag,
    ) + ':nth-child({i})'
    if no_selector_string:
        string_selector_template += ':not({})'.format(no_selector_string)
    # starting the iteration
    # FIXME: first - collect all childes, second - select
    while True:
        child = selector.css(string_selector_template.format(i=i))
        i += 1
        if child:
            started_iteration = True
            childes.append(child)
        elif started_iteration:
            break
    return SelectorList(childes)
