# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup

import urllib2
import re, string
import config
import MySQLdb
import datetime
import PyRSS2Gen
import sys
    
BASEPATH = '/var/www/html/clien/'

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
		title = "clien_hot10_RSS",
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
		# 값이 변경되었으면 업데이트.
		if ( reply > data['reply']  ) or ( recom  > data['recom'] ) :
			rowcount = curs.execute ( """UPDATE rss SET reply = %s, recom = %s WHERE url = %s""", (int(reply), int(recom), url) )
			db.commit()
			
		bFind = True
		
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
	soup = BeautifulSoup(html)
	elements=soup.findAll("div", {"class" : "item"})

	for el in reversed(elements) :
		# 공지사항 제거
		str = ''.join(el.encode('utf-8'))
		if str.find("<span>공지</span>")> -1 :
			continue
		
		title = el.find("a").text
		title = title.strip()
		url = el.find('a')['href']
		url = url.strip()
		print title
		#print url		

		try :
			reply = el.findAll("span", {"class" : "badge-reply"})
			reply = int (reply[0].text)
			#print reply
		except :
			reply = '0'
			#print '0'

		try :
			symph = el.findAll("div", {"class" : "list-symph"})
			recom = int (symph[0].text)
			#print recom

		except :
			recom = '0'
			#print '0'

		lst_cate = link.split('/')
		c = lst_cate[-1]
		ca = c.split('?')
		category = ca[0]

		
		# 덧글 10개 이상이면 내용 가져오기
		if ( int(reply) >= 10 ) or ( int (recom) >= 5 ) :
			#기존 저장 된건가? 
			if not check_pk (url, reply, recom) :
				req = urllib2.Request('https://www.clien.net' + url) 
				req.add_header("User-agent", user_agent)
				response = urllib2.urlopen(req) 
				headers = response.info().headers 
				html = response.read() 		
				
				# BeautifulSoup 로 파싱
				soup = BeautifulSoup(html)
				elements=soup.findAll("body")
				text = elements[1]
				
				# 날짜
				pdate = soup.findAll("div", {"class" : "post-time"})
				pubdate = pdate[0].text.strip()
				
				#<button class="button-md button-report" onclick="app.articleSingo('samsung');
				
				# 글쓴이
				pauthor = soup.findAll("button", {"class" : "button-md button-report"})
				auth = pauthor[0]
				auth1 = ''.join(auth.encode('utf-8'))
				auth2 = auth1.split("'")
				author = auth2[1]

				insert_bbs(category, title, text, url, pubdate.strip(), author, reply, recom )
				print "INSERT BODY!! "
				
		continue; 

reload(sys)
		
sys.setdefaultencoding('utf-8')		

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


for u in url_list :
	for i in range(3,-1,-1) :
		if i == 0 : 
			print u 
			pasing_url(u)

		else :
			print u + '&po=%d' % i
			pasing_url(u + '?&po=%d' % i)
			
makerss()
			
#http://feeds.feedburner.com/Clien_hot10_rss

			