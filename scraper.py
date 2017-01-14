#!/usr/bin/env python3

import urllib.request
import json
import csv
import sys
import re

from bs4 import BeautifulSoup

INIT_URL = 'https://search.jd.com/Search?keyword=' \
           'qnap&enc=utf-8&wq=qnap&pvid=yhzxfuxi.4ocx0a00n52av'
PRODUCT_URL = 'https://item.jd.com/'
GET_PAGE_URL = 'https://search.jd.com/s_new.php?keyword=qnap&enc=utf-8' \
               '&qrst=1&rt=1&stop=1&vt=2&offset=-1&bs=1&wq=qnap&page='
GET_PRICE_URL = 'https://p.3.cn/prices/mgets?skuIds='
GET_STOCK_URL = 'https://c0.3.cn/stock?area=1_72_2799_0&' \
                'extraParam={"originid":"1"}&skuId='
FILE_PATH = 'product_data.csv'


def get_html(url):
    response = urllib.request.urlopen(url)
    return response.read()


def parse_all_products(html, writer):
    print('getting product pages..')
    html = BeautifulSoup(html)
    try:
        page_len = int(html.find('div', id='J_topPage').span.i.text)
    except AttributeError:
        page_len = 1

    products_data = []
    for page in range(1, page_len+1):
        parse_page(page, page_len, products_data, writer)
    return


def parse_page(page, page_len, products_data, writer):
    print('\nparsing page ' + str(page) +
          '/' + str(page_len) + ':')
    html = get_html(GET_PAGE_URL + str(page))
    html = BeautifulSoup(html)
    product_list = html.find('div', {"id": "J_goodsList"}).ul
    products = product_list.find_all('li')

    # collecting products sku to get all product prices at ones than
    products_sku = []
    for product in products:
        products_sku.append('J_' + product.attrs['data-sku'])

    print('getting product prices')
    prices = get_product_prices(products_sku)

    print('gathering product info...')
    iteration = 0
    length = len(products)
    suffix = 'complete'

    for product in products:
        mpn = product['data-sku']
        product_url = PRODUCT_URL + mpn + '.html'
        page_html = get_html(product_url)
        product_page = BeautifulSoup(page_html)

        if product_page:
            product_obj = parse_product_page(product_page, mpn,
                                             product_url, prices)
            if product_obj not in products_data:
                writer.writerow((
                    product_obj['Brand'],
                    product_obj['MPN'],
                    product_obj['URL'],
                    product_obj['Name'],
                    product_obj['Price'],
                    product_obj['Stock'],
                ))
                products_data.append(product_obj)

        iteration += 1
        prefix = 'Progress page ' + str(page) +\
                 ' (' + str(iteration) + '/' + str(length) + ')'
        print_progress(iteration, length, prefix, suffix, bar_length=50)

    return


# Print iterations progress
def print_progress(iteration, total, prefix='', suffix='', decimals=1,
                   bar_length=100, fill='█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        barLength   - Optional  : character length of bar (Int)
    """
    percent = ("{0:." + str(decimals) + "f}")\
        .format(100 * (iteration / float(total)))
    filled_length = int(bar_length * iteration // total)
    bar = fill * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percent,
                                            '%', suffix))
    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()


def get_product_prices(products_sku):
    byte_response = get_html(GET_PRICE_URL + ','.join(products_sku))
    str_response = byte_response.decode("utf-8", errors='ignore').strip()
    jdata = json.loads(str_response)
    prices = {}
    for data in jdata:
        prices[data['id'].replace('J_', '')] = data['p']
    return prices


def get_product_stock(html, mpn):
    cat = parse_product_cat(html)
    byte_response = get_html(GET_STOCK_URL + mpn + cat)
    str_response = byte_response.decode("gb2312", errors='ignore').strip()
    jdata = json.loads(str_response)
    stock_desc = jdata['stock']['stockDesc']
    stock_desc = re.sub('</?strong>', '', stock_desc)
    stock = 1 if '有货' in stock_desc else 0
    return stock


def parse_product_cat(html):
    """Shameful... and weird! method :)
    that parses product categories from html class name
    Didn't find how to get product categories in proper way
    Categories needed to get product stockDesc"""
    try:
        classes = html.find('body')['class']
        cats = []
        for cls in classes:
            if 'cat' in cls:
                cats.append(re.sub('cat-\d+-', '', cls))
    except AttributeError:
        return '&cat=670'
    return '&cat=' + ','.join(cats)


def parse_product_page(html, mpn, url, prices):
    try:
        brand = html.find('ul', id='parameter-brand').li['title']
    except AttributeError:
        brand = ''

    # for some reasons this site has at least two different html templates
    # for product page. And the selector path to the 'Name' attribute varies
    if html.find('div', id='name'):
        try:
            name = html.find('div', id='name').h1.text
        except AttributeError:
            name = ''
    elif html.find('div', class_="sku-name"):
        try:
            name = html.find('div', class_="sku-name").text
        except AttributeError:
            name = ''

    stock = get_product_stock(html, mpn)

    if prices[mpn]:
        price = prices[mpn]
    else:
        price = 0

    product_data = {
        'Brand': brand,
        'MPN': mpn,
        'URL': url,
        'Name': name,
        'Price': price,
        'Stock': stock,
    }
    return product_data


def main():
    with open(FILE_PATH, 'w') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(('Brand', 'MPN', 'URL', 'Name', 'Price', 'Stock'))
        try:
            html = get_html(INIT_URL)
            parse_all_products(html, writer)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    main()
