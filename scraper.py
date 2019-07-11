'''
This is a tool for scraping news websites for their articles.
Supports: Wallstreet Journal Preview, and Yahoo! Finance
Created by: Casey Key, SE Intern
Created: July 19th, 2019
'''
import datetime                     # for filenames with date
import re                           # for regular expressions
import csv                          # for exporting the scraped articles
import sys                          # for command-line url argument
import time                         # for time.sleep()
from urllib.parse import urljoin    # for yahoo news' relative links
import requests                     # for downloading webpages
from bs4 import BeautifulSoup       # for webpage (BS) data structure
from selenium import webdriver      # for scroll() method
from tqdm import tqdm               # for progress bar

'''
Determines the news source (WSJ, Yahoo! Finance)
Returns:
    "wsj"
    "yahoo"
    "unknown news source"
'''
def which_news_is(url):
    wsj = re.compile(r'.*(wsj\.com)+(.*)')
    yahoo = re.compile(r'.*(finance\.yahoo\.com)+(.*)')
    if wsj.search(url):
        return "wsj"
    if yahoo.search(url):
        return "yahoo"
    return "unknown news source"


'''
Determine the news page we will be scraping.
'''
argv = sys.argv
url = input("Please enter a WSJ or Y! Finance news page: ") if len(argv) == 1 else argv[1]
if not url:
    url = "https://finance.yahoo.com/quote/BTC-USD?p=BTC-USD&.tsrc=fin-srch"

source = which_news_is(url)

'''
This method downloads a webpage and returns a BS data structure.
'''
def web_soup(url, scroll=False):
    # Fetch data from url
    response = requests.get(url)
    try:
        assert response.status_code == 200
    except AssertionError as e:
        time.wait(3)
        response = requests.get(url)
        assert response.status_code == 200
    # Parse website data into bs4 data structure
    if scroll:
        soup = scroller(url)
    else:
        soup = BeautifulSoup(response.text,features="html.parser")
    return soup


'''
Extract WSJ links from the bs4 d.s.
'''
def link_soup(soup):
    if source == "wsj":
        return soup.find_all('a', {'href': re.compile(r'(http)+.*(wsj\.com\/articles\/)+(.*)')})
    elif source == "yahoo":
        return soup.find_all('a', {'href': re.compile(r'.*(\/news\/)+(.+)')})
    
    return ()

    
'''
Returns a set of links to articles given a webpage
'''
def get_links(url):	
    html = web_soup(url, scroll=True)
    links = link_soup(html) 
    link_set = set(links)
    link_list = []
    for link in link_set.copy():
        regex = re.compile('(<a class="image")+')
        if regex.search(str(link)):
            print("found image")
            link_set.remove(link)
    return link_set


'''
Saves Wall Street Journal articles as CSV file "wsj-news.csv"
'''
def save_wsj(links):
    print("Scraping now...")

    with open("wsj-news.csv", "a") as f:
        # Write headers if this is a fresh file
        if f.tell() == 0:
            header = ['title', 'article']
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
        
        # Write to file
        writer = csv.writer(f)
        for link in tqdm(links, disable=(len(links)<10)):
            # Extract article title
            title = link.text
            # Visit link to article
            article_soup = web_soup(link['href'])
            # Extract article snippet
            article_snippet = article_soup.find_all('div', {'class': 'wsj-snippet-body'})
            for snippet in article_snippet:
                article = snippet.text.replace("\n", " ")

            # date =
            # author =

            # Write article to CSV file
            writer.writerow([title, article])

    print("...scraping complete.")


'''
Scrolls the true bottom of a website
Returns the bs4 of website
Credit: https://michaeljsanders.com/2017/05/12/scrapin-and-scrollin.html
'''
def scroller(url):

    # I used Firefox; you can use whichever browser you like.
    browser = webdriver.Firefox()

    # Tell Selenium to get the URL you're interested in.
    browser.get(url)

    # Selenium script to scroll to the bottom, wait 3 seconds for the next batch of data to load, then continue scrolling.  It will continue to do this until the page stops loading new data.
    for i in range(18):
        start_height = browser.execute_script('var height=document.documentElement.scrollHeight; return height')
        browser.execute_script('window.scrollTo(0, document.documentElement.scrollHeight);')
        after_height = browser.execute_script('return document.documentElement.scrollHeight')
        print(i)
        time.sleep(1)
            
    # Now that the page is fully scrolled, grab the source code.
    source_data = browser.page_source

    # Throw your source into BeautifulSoup and start parsing!
    bs_data = BeautifulSoup(source_data, features="html.parser")
    
    return bs_data
'''
Saves Yahoo Finance articles as CSV file "yahoo-news.csv"
'''
def save_yahoo(links):
    print('Scraping now...')
    base_url = 'https://finance.yahoo.com'
    now = datetime.datetime.now()
    date = now.strftime('%d-%a-%y')
    filename = 'yahoo-news-' + date + '.csv'
    with open(filename, 'a') as f:
        # Write column titles for a fresh CSV file
        if f.tell() == 0:
            header = ['title', 'article', 'author', 'provider', 'date']
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()

        # Get ready to write a csv file
        writer = csv.writer(f)
        # For each link, extract contents
        for link in tqdm(links, disable=(len(links)<10)):
            rel_link = link.attrs['href']
            article_url = urljoin(base_url, rel_link)
            article_soup = web_soup(article_url)
            article_paragraphs = article_soup.select('article')[0]
            article = ""
            for EachText in article_paragraphs.find_all('p'):
                article += ' ' + EachText.get_text().replace('\n', ' ')
            
            # Find title, author, provider, and date
            title = article_soup.find('h1').text
            auth_prov = article_soup.find_all('div', {'class': 'auth-prov-soc'})
            auth_prov = auth_prov.pop()
            if auth_prov.find(itemprop="name"):#auth_prov.find('a').get("itemprop"):
                author = auth_prov.find(itemprop="name").text
            provider =  auth_prov.find('span', {'class': 'provider-link'}) 
            provider = "None" if not provider else provider.text
            date = auth_prov.time['datetime'] 

            print('Title:', title)
            print('Author:', author)
            print('Provider:', provider)
            print('Published:', date)
            
            writer.writerow([title, article, author, provider, date])
    print("...scraping complete.")


if __name__ == "__main__":
    links = get_links(url)

    #for link in links:
     #   print(link.prettify())

    print("Found", len(links), "news articles.")
    save_yahoo(links) if source == "yahoo" else save_wsj(links)


