import logging

from scrapy.selector import SelectorList


logger = logging.getLogger(__name__)


class Middleware:

    def __init__(self, function, args: tuple =(), kwargs: dict ={}):
        if not isinstance(args, tuple):
            raise TypeError('Given `args` are not `tuple` object.')
        if not isinstance(kwargs, dict):
            raise TypeError('Given `kwargs` are not `dict` object.')
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def call(self, input_value):
        output_value = self.function(input_value, *self.args, **self.kwargs)
        if not type(input_value) == type(output_value):
            msg = 'Outgoing value have different type from incoming value.'
            logger.error(msg)
            raise TypeError(msg)
        return output_value


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


# ====================
#  actual middlewares
# ====================
def select(selector: SelectorList, string_selector: str) -> SelectorList:
    return selector.css(string_selector)


def childes(selector: SelectorList,
            parent_tag: str,
            child_tag: str ='',
            no_selector_string: str =None) -> SelectorList:
    childes = []
    i = 1
    # prepare string_selector
    string_selector_template = '{parent_tag} > {child_tag}'.format(
        parent_tag=parent_tag, child_tag=child_tag,
    ) + ':nth-child({i})'
    if no_selector_string:
        string_selector_template += ':not({})'.format(no_selector_string)
    while True:
        child = selector.css(string_selector_template.format(i=i))
        i += 1
        if child:
            childes.append(child)
        else:
            break
    return SelectorList(childes)
