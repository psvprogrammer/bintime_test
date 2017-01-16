import scrapy

GET_PAGE_URL = 'https://search.jd.com/s_new.php?keyword=qnap&enc=utf-8' \
               '&qrst=1&rt=1&stop=1&vt=2&offset=-1&bs=1&wq=qnap&page='


class ProductsSpider(scrapy.Spider):
    name = 'products'

    def __init__(self, page_count, *args, **kwargs):
        super(ProductsSpider, self).__init__(*args, **kwargs)
        self.page_count = page_count

    def start_requests(self):
        urls = [GET_PAGE_URL + str(page) for page in range(1, self.page_count)]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        pass
