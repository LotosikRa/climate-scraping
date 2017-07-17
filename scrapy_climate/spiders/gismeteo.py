# -*- coding: utf-8 -*-

from scrapy_climate.tools import (
    HeaderExtractor,
    TagExtractor,
    LinkExtractor,
    TextExtractor,
    MediaCounter,
)
from scrapy_climate.tools import SingleSpider


class GismeteoTextExtractor(TextExtractor):

    def extract_from(self, selector):
        selected = self.select_from(selector)
        # FIXME: div inside div
        #if selected.css('div:nth-child(2) > div::attr(id)').extract_first() == 'fb-root':
        #    selected = selected.css('div. > div')
        elements = []
        media_counter = MediaCounter()
        for div in selected:
            link = div.css('div > a::text')
            photo = div.css('div > div.pic-descr::text')
            video = div.css('div > div.pic')
            iframe = div.css('div > iframe')
            text = div.css('div::text').extract_first()
            if link:
                link_extracted = link.extract_first()
                href_extracted = div.css('div > a::attr(href)').extract_first()
                string = ''
                for item in div.css('::text').extract():
                    if item == link_extracted:
                        string += self.hyperlink_format.format(
                            text=link_extracted,
                            link=href_extracted, )
                    else:
                        string += item
                elements.append(string)
            elif photo:
                media_counter.add_photo()
                elements.append(self.photo_format)
            elif video:
                media_counter.add_video()
                elements.append(self.video_format)
            elif iframe:
                media_counter.add_iframe()
            elif self.is_trash(text):
                pass
            elif text:
                elements.append(text)
            else:
                raise ValueError('Uncategorised block: {}'.format(div.extract()))
        counter = media_counter.as_string()
        if counter:
            elements.append(counter)
        formatted = self._convert(elements)
        return formatted


class GismeteoUASpider(SingleSpider):

    name = 'gismeteo_ua'

    _start_path = 'news/'
    _start_domain = 'www.gismeteo.ua'
    _scheme = 'https'

    _link_extractor = LinkExtractor(
        list_of_string_css_selectors=[
            'div.item__title > a::attr(href)',
            'div.container-img > a::attr(href)'])
    _header_extractor = HeaderExtractor('div.article__h > h1::text')
    _tags_extractor = TagExtractor('div.article__tags > a::text')
    _text_extractor = GismeteoTextExtractor('div.article__i > div')

    def _convert_path_to_index(self, path: str) -> str:
        return path.split('/')[-2].split('-')[0]


class GismeteoRUSpider(GismeteoUASpider):

    name = 'gismeteo_ru'

    _start_domain = 'www.gismeteo.ru'
