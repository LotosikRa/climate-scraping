# gismeteo-news-scraping

scrapinghub project for scraping news from https://www.gismeteo.ua/news/

## Status

Now codebase isn't stable and must be refactored into standalone library 
to be use Scrapy's design features like Extensions, Middlewares etc.

Commit history isn't good too, because locally I have some spiders that uses
this API. And I will implement new features only when I need them for them.

When current refactoring iteration will end, I will end this repository, move 
all it's API to library and use it as Extension/Middleware...

## Usage

Project is writen on Python 3 (tested on 3.5).

It have only one spider - `gismeteo`. It scrapes urls (that weren't scraped yet),
and then follows them and scrapes articles to Google Drive Sheet.

#### Google API key

Follow steps [from this page](https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html)
to generate `.json` key and save it to `scrapy_climate` folder with `client-secret.json` name.

#### Deploying

Connection to Scrapy Cloud via GitHub mustn't work because it doesn't support Python 3.
So you need to use `shub` command line tool.

Define your project id for each `shub deploy` call, or edit `scrapinghub.yml`.

#### Running

To run spider you need to create `config.json` in `scrapy_climate` folder.
Use JFON format to define variables like:
```
{
  "SCRAPY_CLOUD_API_KEY": "<scrapy_cloud_api_key>",
  "SCRAPY_CLOUD_PROJECT_ID": "<scrapy_cloud_project_id>",
  "SPREADSHEET_TITLE": "<google_drive_spreadsheet_title>",
  "SPIDER_TO_WORKSHEET_DICTIONARY": {
    "testing": 0,
    "<spider>": <worksheet_id_starting_from_zero>
  }
}
```

This file is ignored by git, but will be deployed to ScrapingHub.

#### Storage

Pipeline gives items to StorageMaster that
appends them to defined in spider `arguments` Google Drive Sheet ordered by
url, header, tags and body of article to worsheet that defined for currently
running spider in `config.json`
worksheet (so it must be created before, or spider will raise an RuntimeError), and when
all items where added, master ends his work with a row that contains
url to job on ScrapingHub, CPU datetime, number of scraped articles
and two `-----` strings.

#### How it scrapes only fresh articles?

When spider scrapes `news` page, first of all it fetches `indexes` list of scraped
articles from last week using Scrapy Cloud API. Then spider iterates over
links to articles and scrapes only articles that aren't in the `indexes` list.

#### Inheriting

In `scrapy_climate/spider.py` Python module it is `TemplateSpider` class
which can be use used as parent for actually running spiders. To make new
spider you will need to configure it's selectors and define name, domain,
and relative path to first page. More about it in the docstrings.
