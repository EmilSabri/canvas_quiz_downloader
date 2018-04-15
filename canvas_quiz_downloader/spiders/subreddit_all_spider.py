import scrapy


class subreddit_all(scrapy.Spider):
    name = 'subreddit_all'

    #allowed_domains = ['https://www.reddit.com/r/PrequelMemes/']
    #allowed_domains = ['https://www.reddit.com/r/lotrmemes/']
    start_urls = [
        'https://www.reddit.com/r/lotrmemes/'
    ]

    def parse(self, response):
        for kenobi in response.css('div.thing'):
            yield {
                'title': kenobi.css('a.title::text').extract_first(),
                'comments': kenobi.css('a.bylink::text').extract_first(),
                'points' : kenobi.css('div.likes::text').extract_first(),
                'date': kenobi.css('p.tagline time::attr(title)').extract_first(),
                'link': kenobi.css('li.first a.bylink::attr(href)').extract_first(),
            }

        day2num = {
            "Sun" : 1
        }


        past24 = response.css('p.tagline time::attr(title)').extract_first()



        next_page = response.css('span.next-button a::attr(href)').extract_first()

        if next_page is not None:
            next_page = response.urljoin(next_page)
            yield {
                'follow-link': next_page
            }
            yield scrapy.Request(next_page, callback=self.parse)




