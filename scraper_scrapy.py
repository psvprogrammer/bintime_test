import scrapy
import json
import csv
import re

from scrapy.crawler import CrawlerProcess


INIT_URL = 'https://search.jd.com/Search?keyword=' \
           'qnap&enc=utf-8&wq=qnap&pvid=yhzxfuxi.4ocx0a00n52av'
PRODUCT_URL = 'https://item.jd.com/'
GET_PAGE_URL = 'https://search.jd.com/s_new.php?keyword=qnap&enc=utf-8' \
               '&qrst=1&rt=1&stop=1&vt=2&offset=-1&bs=1&wq=qnap&page='
GET_PRICE_URL = 'https://p.3.cn/prices/mgets?skuIds='
GET_STOCK_URL = 'https://c0.3.cn/stock?area=1_72_2799_0&' \
                'extraParam={"originid":"1"}&skuId='
FILE_PATH = 'product_data.csv'


class ProductsSpider(scrapy.Spider):
    name = 'products'
    start_urls = [INIT_URL]

    def __init__(self, *args, **kwargs):
        super(ProductsSpider, self).__init__(*args, **kwargs)
        self.sku_list = []
        self.prices_list = {}

    def parse(self, response):
        page_len = response.xpath(
            "//div[@id='J_topPage']/span/i/text()"
        ).extract_first()
        if page_len:
            page_urls = [GET_PAGE_URL + str(page) for page in
                         range(1, int(page_len)+1)]
            for url in page_urls:
                yield scrapy.Request(url, callback=self.parse_page_sku_list)

            # remove duplicates in sku_list
            self.sku_list = list(set(self.sku_list))

            yield self.get_prices()

            with open(FILE_PATH, 'w') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(
                    ('Brand', 'MPN', 'URL', 'Name', 'Price', 'Stock')
                )
            for sku in self.sku_list:
                mpn = sku.replace('J_', '')
                product_url = PRODUCT_URL + mpn + '.html'
                yield scrapy.Request(
                    product_url,
                    callback=self.parse_product_page(mpn, product_url, writer)
                )

    def parse_page_sku_list(self, response):
        page_sku_list = response.xpath(
            "//div[@id='J_goodsList']/ul/li"
        ).extract()
        for sku in page_sku_list:
            self.sku_list.append('J_' + sku.xpath("/@data-sku/text()"))

    def get_prices(self):
        if len(self.sku_list) > 100:
            # divide list on parts by 100 units (max possible)
            products_sku = [self.sku_list[i:i + 100]
                            for i in range(0, len(self.sku_list), 100)]
            for part in products_sku:
                yield scrapy.Request(GET_PRICE_URL + ','.join(part),
                                     callback=self.parse_prices_page())

    def parse_prices_page(self, response):
        str_response = response.decode("utf-8", errors='ignore').strip()
        jdata = json.loads(str_response)
        for data in jdata:
            self.prices_list[data['id'].replace('J_', '')] = data['p']

    def parse_product_page(self, response, mpn, product_url, writer):
        try:
            brand = response.xpath("//ul[@id='parameter-brand']/li/@title")
        except AttributeError:
            brand = ''

        # for some reasons this site has at least two different html templates
        # for product page. And the selector path
        # to the 'Name' attribute varies
        if response.xpath("div[@id='name']"):
            try:
                name = response.xpath("div[@id='name']/h1/text()")
            except AttributeError:
                name = ''
        elif response.xpath("div[@class='sku-name']"):
            try:
                name = response.xpath("div[@class='sku-name']/text()")
            except AttributeError:
                name = ''

        stock = self.get_product_stock(response, mpn)

        try:
            price = self.prices_list[mpn]
        except KeyError:
            price = 0

        writer.writerow((
            brand,
            mpn,
            product_url,
            name,
            price,
            stock,
        ))

    def get_product_stock(self, response, mpn):
        cat = self.parse_product_cat(response)
        stock = yield from scrapy.Request(GET_STOCK_URL + mpn + cat,
                                          callback=self.parse_product_stock)
        return stock

    def parse_product_stock(self, response):
        str_response = response.decode("gb2312", errors='ignore').strip()
        jdata = json.loads(str_response)
        stock_desc = jdata['stock']['stockDesc']
        stock_desc = re.sub('</?strong>', '', stock_desc)
        stock = 1 if '有货' in stock_desc else 0
        return stock


if __name__ == '__main__':
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    })
    process.crawl(ProductsSpider)
    process.start()
