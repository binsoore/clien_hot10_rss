# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup

import urllib2
import re, string
import config
import MySQLdb
import datetime
import PyRSS2Gen
import sys, os

import logging
import logging.handlers
    
BASEPATH = '/var/www/html/clien/'

LOG = logging.getLogger("mylogger")

def init_logger ( ) :

    if not os.path.isdir('./log') :
        os.mkdir('./log')
        
    # 로거 인스턴스 생성
    logger = logging.getLogger("mylogger")

    # 포매터를 만든다
    # formatter = logging.Formatter('[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')
    formatter = logging.Formatter('[%(asctime)s][%(filename)s:%(lineno)s][%(levelname)s] %(message)s')

    fileMaxByte = 1024 * 1024 * 10  # 10MB

    # 화면, 파일 각각 핸들러 생성
    filename = "./log/clien_rss.log"
    fileHandler = logging.handlers.RotatingFileHandler(filename, maxBytes=fileMaxByte, backupCount=10)

    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    # 핸들러를 생성된 logger 에 추가한다.
    logger.addHandler(fileHandler)
    logger.addHandler(streamHandler)
    logger.setLevel(logging.DEBUG)

    
def makerss () :
    lst_title = []
    lst_category = []
    lst_text = []
    lst_url = []
    lst_pubdate = []
    lst_author = []
    lst_reply = []
    lst_recom = []

    db = MySQLdb.connect(config.mysql_server, config.mysql_id, config.mysql_password, config.mysql_db, charset='utf8')
    curs = db.cursor(MySQLdb.cursors.DictCursor)

    rss = PyRSS2Gen.RSS2(
        title = "clien_hot10",
        link = "http://www.clien.net",
        description = "RSS_clien_hot10",
        lastBuildDate = datetime.datetime.now(),
        items = [] )

    rowcount = curs.execute ( """SELECT * FROM rss order by sn DESC limit 50 """ )

    for r in curs.fetchall() :
        lst_title.append( r['title'] )
        lst_category.append( r['category'] )
        lst_text.append( r['text'] )
        lst_url.append( r['url'] )		
        lst_pubdate.append( r['pubdate'] )
        lst_author.append( r['author'] )

        lst_reply.append( r['reply'] )
        lst_recom.append( r['recom'] )

    
    for i, title in enumerate(lst_title) :
        tt = "[%s][%s]" % ( str(lst_reply[i]), str(lst_recom[i]))
        item = PyRSS2Gen.RSSItem(
            title = lst_title[i] + tt,
            link = 'https://www.clien.net' + lst_url[i],
            guid = PyRSS2Gen.Guid('https://www.clien.net' + lst_url[i]),
            description = lst_text[i],
            # pubDate = datetime.datetime.fromtimestamp(lst_pubdate[i]),
            pubDate = lst_pubdate[i], 
            author = lst_author[i] )
            
        rss.items.append(item)
    
    rss.write_xml(open(BASEPATH + 'rss_clien_hot10.htm',  'w'))

def check_pk (url, reply, recom):
    db = MySQLdb.connect(config.mysql_server, config.mysql_id, config.mysql_password, config.mysql_db, charset='utf8')
    curs = db.cursor(MySQLdb.cursors.DictCursor)
        
    bFind = False
    
    # 같은 주소에 덧글, 공감수 바뀌었나?
    rowcount = curs.execute ( """SELECT reply, recom FROM rss WHERE url = %s """, url )
    data = curs.fetchone()
    if rowcount > 0 :
        bFind = True
        # 값이 변경되었으면 업데이트.
        if ( reply > data['reply']  ) or ( recom  > data['recom'] ) :
            rowcount = curs.execute ( """UPDATE rss SET reply = %s, recom = %s WHERE url = %s""", (int(reply), int(recom), url) )
            db.commit()
        
    return bFind
    
def insert_bbs(category, title, text, url, pubdate, author, reply, recom):
    db = MySQLdb.connect(config.mysql_server, config.mysql_id, config.mysql_password, config.mysql_db, charset='utf8')
    curs = db.cursor(MySQLdb.cursors.DictCursor)
    curs.execute ( u"""INSERT INTO rss (category, title, text, url, pubdate, author, reply, recom)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
        ON DUPLICATE KEY 
        UPDATE reply = %s, recom = %s """, (category, title, text, url, pubdate, author, reply, recom,  reply, recom))
        
    db.commit()

def pasing_url( link ):
    user_agent = "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)" 
    req = urllib2.Request(link) 
    req.add_header("User-agent", user_agent)

    response = urllib2.urlopen(req) 
    headers = response.info().headers
    html = response.read() 

    # BeautifulSoup 로 파싱
    soup = BeautifulSoup(html, "html5lib")
    elements=soup.findAll("div", {"class" : "list_item symph_row"})

    for el in reversed(elements) :
        # 공지사항 제거
        notice_str = ''.join(el.encode('utf-8'))
        if notice_str.find("<span>공지</span>")> -1 :
            continue
        
        title = el.find("a").text
        title = ' '.join(title.split())

        url = el.find('a')['href']
        url = url.strip()
        url = url.split('?')[0]
        print title
        print url		

        try :
            reply = el.findAll("span", {"class" : "rSymph05"})
            reply = int (reply[0].text)
            print reply
        except Exception, e :
            LOG.error ( 'rSymph05 : %s ' % str(e) )
            reply = '0'
            #print '0'

        try :
            symph = el.findAll("div", {"class" : "list_symph view_symph"})
            recom = int (symph[0].text)
            print recom

        except Exception, e :
            LOG.error ( 'list_symph : %s ' % str(e) )
            recom = '0'
            #print '0'

        lst_cate = link.split('/')
        c = lst_cate[-1]
        ca = c.split('?')
        category = ca[0]
        
        # 덧글 10개 이상이면 내용 가져오기

        if ( int(reply) >= 10 ) or ( int (recom) >= 5 ) :
            #기존 저장 된건가? 
            # feedly 에 제목이 두번나온다. 일단 제목에 업데이트 금지.
            if not check_pk (url, reply, recom) :
                
                req = urllib2.Request('https://www.clien.net' + url) 
                req.add_header("User-agent", user_agent)
                response = urllib2.urlopen(req) 
                headers = response.info().headers 
                html = response.read() 		

                # body 가 테그가 매치가 안되어
                # html 을 임의값으로 변경해서, bs4 에서 검색하도록 변경. 
                html = html.replace ('<html>', '<rssclien>')
                html = html.replace ('</html>', '</rssclien>')
                
                # BeautifulSoup 로 파싱
                soup = BeautifulSoup(html, "html5lib")
                
                elements=soup.find("rssclien")
               
                content = elements
                
                content = str(content).replace ("<rssclien>", "")
                content = str(content).replace ("</rssclien>", "")
                
                print content
                
                # 날짜
                pdate = soup.findAll("div", {"class" : "post_author"})
                pdate = pdate[0].text.strip()
                pdate = pdate.split (" ")

                pubdate = pdate[0] + " " + pdate[1]
                pubdate = pubdate.strip()
                print pubdate

                soup2 = BeautifulSoup(html, "html5lib")
                # 글쓴이
                try : 
                    author = soup.find('input', {'id': 'writer'}).get('value')
                    print author
                    # 이전문서 불필요시 삭제가능
                    #pauthor = soup2.findAll("button", {"class" : "button_input"})
                    #auth1 = ''.join(pauthor[0].encode('utf-8'))
                    # 정규식
                    # 문자숫자\w+ 로 시작하고 끝이 따옴표이지만 포함하지 않음
                    #rex = re.search("[\w]+(?=\')", auth1)
                    #author = rex.group()
                    #author = author.strip()
                    
                except Exception, e :
                    LOG.error ( 'author : %s ' % str(e) )
                
                
                try : 
                    insert_bbs(category, title, content, url, pubdate, author, reply, recom )
                except Exception, e :
                    LOG.error ( 'insert_bbs : %s ' % str(e) )
                
                print "INSERT BODY!! "
                    
        continue; 

if __name__ == "__main__":     

    reload(sys)
            
    sys.setdefaultencoding('utf-8')
    
    init_logger()        

    # 검색할 게시판 List
    url_list = []
    url_list.append ('https://www.clien.net/service/board/news')
    url_list.append ( 'https://www.clien.net/service/board/park')
    url_list.append ( 'https://www.clien.net/service/board/lecture')
    url_list.append ( 'https://www.clien.net/service/board/use')
    url_list.append ( 'https://www.clien.net/service/board/jirum')
    url_list.append ( 'https://www.clien.net/service/board/cm_iphonien')
    url_list.append ( 'https://www.clien.net/service/board/cm_car')
    url_list.append ( 'https://www.clien.net/service/board/cm_bike')
    url_list.append ( 'https://www.clien.net/service/board/cm_havehome')
    url_list.append ( 'https://www.clien.net/service/board/cm_nas')
    url_list.append ( 'https://www.clien.net/service/board/cm_vcoin')


    for u in url_list :
        for i in range(3,-1,-1) :
            if i == 0 : 
                print u 
                try :
                    pasing_url(u)
                except :
                    continue

            else :
                # print u + '&po=%d' % i
                try :
                    pasing_url(u + '?&po=%d' % i)
                except Exception, e:
                    
                    print e
                    
                    continue
                
    makerss()
            
#http://feeds.feedburner.com/Clien_hot10_rss

            