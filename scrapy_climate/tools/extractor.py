from scrapy.selector import SelectorList


class Extractor:
    """
    Extracts data from HTML using `scrapy.selector.SelectorList.css` method.
    It's more useful than old `ParseMixin` class implementation because
    allows you to you inheritance between extractors and customize them for
    every spider.
    """

    name = None

    replace_with = []
    allowed_ends = []

    def __init__(self, string_css_selector: str =None,
                 list_of_string_css_selectors: list =None,
                 **kwargs):
        """
        :param string_css_selector: string that can be used for
        `scrapy.selector.SelectorList.css` method
        :param list_of_string_css_selectors: list of string as
        `string_css_selector`
        :param kwargs: `dict` object
        """
        if string_css_selector:
            self._check_string_selector(string_css_selector)
            self.list_of_string_selectors = [string_css_selector]
        elif list_of_string_css_selectors:
            for item in list_of_string_css_selectors:
                self._check_string_selector(item)
            self.list_of_string_selectors = list_of_string_css_selectors
        self.kwargs = self.parse_kwargs(kwargs)

    def parse_kwargs(self, kwargs: dict) -> dict:
        """
        Parses input keyword arguments to use them in the future.
        :param kwargs: `dict` object
        :return: `dict` object
        """
        return kwargs

    def _check_string_selector(self, string_selector: str):
        """
        Checks if given `string_selector` ends with strings defined in
        `allowed_ends` class field.
        :param string_selector: string CSS selector
        :exception ValueErrir: raises if non of strings in `self.allowed_ends`
        list are at the end of given `string_selector` string
        :return: None
        """
        if not isinstance(string_selector, str):
            raise TypeError('Given `string_selector` argument isn\'t `str`.')
        for end in self.allowed_ends:
            if string_selector.endswith(end):
                break
        else:
            raise ValueError(
                'Given `string_selector` (="{}") argument'
                .format(string_selector))

    def _format(self, text: str) -> str:
        """
        Formats given `text` string be iterating over tuples from
        `replace_with` field list's pairs in format
        `(what_to_replace, replace_with)`
        :param text: `str` object
        :return: `str` object
        """
        for before, after in self.replace_with:
            text = text.replace(before, after)
        return text

    def select_from(self, selector: SelectorList) -> SelectorList:
        """
        Uses `list_of_string_selectors` attribute to create new selector from
        the given one.
        :param selector: `SelectorList` object from what method selects using
        initial arguments
        :return: selected `SelectorList` object
        """
        raise NotImplementedError

    def extract_from(self, selector: SelectorList) -> str:
        """
        Extracts data from given selector using initial arguments.
        Must used from `spider.SingleSpider`.
        :param selector: `SelectorList` object from what method selects and
        extracts data.
        :return: `str` object
        """
        raise NotImplementedError


class MediaCounter:

    open_sequense = '<'
    close_sequense = '>'
    separator = '; '

    photo_fmt = 'photo: {}'
    video_fmt = 'video: {}'
    iframe_fmt = 'iframe: {}'

    def __init__(self):
        self.video = 0
        self.photo = 0
        self.iframe = 0
        self.string = ''

    @property
    def order(self):
        return [
            [self.photo, self.photo_fmt],
            [self.video, self.video_fmt],
            [self.iframe, self.iframe_fmt],
        ]

    def add_video(self):
        self.video += 1

    def add_photo(self):
        self.photo += 1

    def add_iframe(self):
        self.iframe += 1

    def to_list(self):
        sequence = [i[1].format(i[0]) if i[0] > 0 else None for i in self.order]
        for string in sequence:
            if string:
                yield string

    def as_string(self) -> str:
        sequence = list(self.to_list())
        lenght = len(sequence)
        string = ''
        if lenght == 0:
            return string
        else:
            string += self.open_sequense
            string += sequence[0]
            if lenght > 1:
                for i in sequence[1:]:
                    string += self.separator + i
            string += self.close_sequense
        self.string = string
        return string


# ===================
#  actual extractors
# ===================
class HeaderExtractor(Extractor):
    """
    Expects to be used for extracting header from "article" page.
    Must take only one string or list with only one string.
    """

    name = 'header'

    allowed_ends = ['::text']

    def select_from(self, selector: SelectorList) -> SelectorList:
        return selector.css(self.list_of_string_selectors[0])

    def extract_from(self, selector: SelectorList) -> str:
        extracted = self.select_from(selector).extract_first()
        formatted = self._format(extracted)
        return formatted


class TagExtractor(HeaderExtractor):
    """
    Expects to be used for extracting tags from "article" page.
    Can take list with many strings.
    """

    name = 'tag'

    default = ''
    separator = ', '

    def _convert(self, lst: list) -> str:
        """
        Converts given list of strings to string by formatting every item in
        the `lst` list and joining them with `self.separator`
        :param lst: list of `str` objects
        :return: `str` object. If given list is empty returns `self.default`
        """
        if len(lst) == 0:
            return self.default
        string = self._format(lst[0])
        for item in lst[1:]:
            formatted = self._format(item)
            if formatted:
                string += self.separator + self._format(item)
        return string

    def select_from(self, selector: SelectorList) -> SelectorList:
        """
        Instead of parent `HeaderExtactor` we expect that it can be many
        selectors given at initialising, but method must return selector only
        from one place.
        :exception RuntimeError: if it is no entry for selectors from
        `self.list_of_string_selectors` or it is more then one entry.
        """
        found_list = []
        found_indexes = []
        for i, string_selector in enumerate(self.list_of_string_selectors):
            selected = selector.css(string_selector)
            if selected:
                found_indexes.append(i)
                found_list.append(selected)
            else:
                found_list.append(None)
        if len(found_indexes) == 1:
            return found_list[found_indexes[0]]
        elif len(found_indexes) > 1:
            raise RuntimeError('Found more than one "{name}" containers: {lst}'
                               .format(lst=found_list, name=self.name))
        else:
            raise RuntimeError('Not found any "{}" containers.'
                               .format(self.name))

    def extract_from(self, selector: SelectorList) -> str:
        extracted = self.select_from(selector).extract()
        converted = self._convert(extracted)
        return converted


class TextExtractor(TagExtractor):
    """
    Expects to be used for extracting text from "article" page.
    Can take list with many strings.
    """

    name = 'text'

    separator = '\n'
    replace_with = [
        ('\xa0', ' '),
        ('\r\n\t', ''),
        ('\t', ' '),
        ('\n', ' '),
    ]
    allowed_ends = ['div']

    hyperlink_format = '[{text}]({link})'
    photo_format = '<photo>'
    video_format = '<video>'
    iframe_format = '<iframe>'

    def is_trash(self, string: str) -> bool:
        lst = [' ']
        for i, _ in self.replace_with:
            lst.append(i)
        for i in lst:
            string.replace(i, '')
        if string == '':
            return True
        else:
            return False

    def extract_from(self, selector: SelectorList):
        """
        In this case it can be multiple child HTML tags and method must iterate
        over them and check if there can be hyperlinks, photos etc.
        """
        raise NotImplementedError()


class LinkExtractor(Extractor):
    """
    The only extractor that returns generator instead `str` object.
    Expects to be used for extracting hyperlinks ro "article" pages from
    "news-list" page.
    Can take list with many strings.
    """

    name = 'link'

    replace_with = []
    allowed_ends = ['a::attr(href)']

    def select_from(self, selector: SelectorList):
        """
        :param selector: `SelectorList` object from what we selects data
        :exception RuntimeError: if even one string selector in
        `self.list_of_string_selectors` fails
        :return: generator of `Selector` objects
        """
        for string_selector in self.list_of_string_selectors:
            selected = selector.css(string_selector)
            if selected:
                for item in selected:
                    yield item
            else:
                raise RuntimeError(
                    '`{}` selector failed'.format(string_selector))

    def extract_from(self, selector: SelectorList):
        """
        Expects to be called from `spider.SingleSpider._yield_requests_from_response`
        method.
        :param selector: `SelectorList` object (HTML)
        :return: generator of `str` objects
        """
        for selected in self.select_from(selector):
            yield self._format(selected.extract())
