from flask import Flask, jsonify, request, render_template

import requests
import hashlib
import os
from urllib.parse import urlparse, quote_plus
import glob

from fuzzywuzzy import fuzz
from strsimpy.levenshtein import Levenshtein
#import nltk
from config import ORIGINAL_DOMAIN_HTML_FOLDER_PATH, FAKE_DOMAIN_HTML_FOLDER_PATH, HEADERS, DB_FOLDER_PATH, DB_NAME, DOMAIN_THREASHOULD, CONTENT_THREASHOULD, IMAGE_THREASHOULD, ORIGINAL_DOMAIN_IMG_FOLDER_PATH, FAKE_DOMAIN_IMG_FOLDER_PATH
import html2text
from database import *
#from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.sql import text
# env = Environment(loader=FileSystemLoader('%s/templates/' % os.path.dirname(__file__)))


app = Flask(__name__,
			static_folder='' ,
			template_folder='%s/templates/' % os.path.dirname(__file__)
	)

app.config ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}.sqlite3'.format(os.path.join(DB_FOLDER_PATH,DB_NAME))


db.init_app(app) # to add the app inside SQLAlchemy()


def get_clean_html(html):
	return html2text.html2text(html)

def check_domain_similarity(original_domain, fake_domain):

	fuzz_ratio 				= 	fuzz.ratio(original_domain, fake_domain)
	fuzz_parital_ratio		=	fuzz.partial_ratio(original_domain, fake_domain)
	fuzz_token_sort_ratio	=	fuzz.token_sort_ratio(original_domain, fake_domain)
	fuzz_token_set_ratio	=	fuzz.token_set_ratio(original_domain, fake_domain)
	levenshtein_distance	=	Levenshtein().distance(original_domain, fake_domain)

	return fuzz_ratio, fuzz_parital_ratio, fuzz_token_sort_ratio, fuzz_token_set_ratio, levenshtein_distance

def check_content_similarity(original_content, fake_content):
	fuzz_ratio 					= fuzz.ratio(original_content, fake_content)


	return fuzz_ratio


def save_file(data, file_name):
	try:
		mode = "wb+" if isinstance(data,bytes) else "w+"
		with open(file_name, mode) as f:
			f.write(data)

	except Exception as e:
		app.logger.error('Error while save_file. Error - {}'.format(e))


def load_file(file_name):
	try:
		with open(file_name, "rb") as f:
			data = f.read()

		return data
	except Exception as e:
		app.logger.error('Error while load_file. Error - {}'.format(e))
		return ""

@app.route("/")
def index():
	#return jsonify({"status":"success"})
	return render_template('search.html')

@app.route("/result")
def result():
	return render_template('result.html')


@app.route("/result/all")
def result_all():
	#return jsonify({"status":"success"})
	previous_scan_results = Verdict.query.all()
	# for scan in previous_scan_results:
	# 	print(scan)
	#print(previous_scan_results)
	return render_template('result.html',previous_scan_results=previous_scan_results)

@app.route("/safe")
def safe_add():
	return render_template('safe_add.html')



@app.route("/safe/add")
def add_safe_site():
	safe_domain = request.args.get('domain')
	if not safe_domain:
		return   jsonify({
				"status":"failed",
				"message":"Required domain.",
			})

	safe_domain = safe_domain.replace("https://","")
	safe_domain = safe_domain.replace("http://","")

	safe_domain = safe_domain.replace("wwww.","") if safe_domain.startswith("www.") else safe_domain
	safe_domain = "https://{}".format(safe_domain) if not safe_domain.startswith("http") else safe_domain
	

	domain = urlparse(safe_domain).netloc
	domain = domain.replace("wwww.","") if domain.startswith("www.") else domain
	app.logger.info("Got {} domain".format(domain))
	domain_hash = hashlib.sha1(domain.encode()).hexdigest()

	is_domain_exists = SafeDomain.query.filter_by(hash=domain_hash).count()

	if is_domain_exists:
		app.logger.info('{} domain present in db.'.format( safe_domain))
		
		return jsonify({
			"status":"success",
			"message":"Domain already present.",
			"results":{
				"domain":safe_domain,
				"hash":domain_hash
			}
		})


	live_test = requests.get(safe_domain, headers=HEADERS,timeout=5,allow_redirects=True)
	
	if live_test.status_code in [200,301,302,303]:
		app.logger.info('{} domain is live.'.format( safe_domain))

	else:
		app.logger.warning('{} domain is not live.'.format( safe_domain))
		return jsonify({
			"status":"failed",
			"message":"Domain is not live.",
		})



	html_file_path = os.path.join(ORIGINAL_DOMAIN_HTML_FOLDER_PATH,"{}_raw.html".format(domain_hash))
	save_file(live_test.content, html_file_path)


	_clean_html = get_clean_html(live_test.text)  
	_clean_html_file_path = os.path.join(ORIGINAL_DOMAIN_HTML_FOLDER_PATH,"{}_clean.html".format(domain_hash))
	save_file(_clean_html.encode("utf-8"), _clean_html_file_path)

	# take screenshot

	# SCREENSHOT_URL = 'https://mini.s-shot.ru/1024x0/JPEG/1024/Z100/?{}'.format(quote_plus(domain)) # you can modify size, format, zoom

	# screenshot_response = requests.get(SCREENSHOT_URL, headers=HEADERS,timeout=10,stream=True)
	# img_file_path = os.path.join(ORIGINAL_DOMAIN_IMG_FOLDER_PATH,"{}.jpg".format(domain_hash))
	# if screenshot_response.status_code == 200:
	# 	with open(img_file_path, 'wb') as file:
	# 		for chunk in screenshot_response:
	# 			file.write(chunk)	

	_domain = SafeDomain(domain=domain, hash=domain_hash, html_file_path=html_file_path, clean_html_file_path=_clean_html_file_path, 
		#img_file_path=img_file_path
		)
	db.session.add(_domain)
	db.session.commit()

	return   jsonify({
			"status":"success",
			"message":"Domain is live.",
			"results":{
				"domain":safe_domain,
				"hash":domain_hash
			}
		})



@app.route("/fake/test")
def test_fake_sites():


	fake_domain = request.args.get('domain')
	if not fake_domain:
		return   jsonify({
				"status":"failed",
				"message":"Required domain.",
			})

	fake_domain = fake_domain.replace("https://","")
	fake_domain = fake_domain.replace("http://","")

	fake_domain = fake_domain.replace("wwww.","") if fake_domain.startswith("www.") else fake_domain
	fake_domain = "https://{}".format(fake_domain) if not fake_domain.startswith("http") else fake_domain


	domain = urlparse(fake_domain).netloc
	domain = domain.replace("wwww.","") if domain.startswith("www.") else domain

	app.logger.info("Got {} domain".format(domain))
	
	domain_hash = hashlib.sha1(domain.encode()).hexdigest()

	is_safe_domain_exists = SafeDomain.query.filter_by(hash=domain_hash).count()

	if is_safe_domain_exists:
		app.logger.info('{} domain present in db.'.format( is_safe_domain_exists))
		
		return jsonify({
			"status":"success",
			"message":"Domain is safe.",
			"results":{
				"domain":fake_domain,
				"hash":domain_hash
			}
		})	

	is_domain_exists = FakeDomain.query.filter_by(hash=domain_hash).count()


	if is_domain_exists:
		
		app.logger.info('{} domain present in db.'.format( fake_domain))
		is_domain_exists = Verdict.query.filter_by(fake_domain_hash=domain_hash)
		_results = [
			{
				"id":result.id,
				"original_domain":result.original_domain,
				"fake_domain":result.fake_domain,
				"content_similarity_score":result.content_similarity_score,
				"domain_similarity_score":result.domain_similarity_score,
				"verdict":result.verdict,

			} 
			for result in is_domain_exists
		]
		return jsonify({
			"status":"success",
			"message":"Domain looks suspicious.",
			"results":{
				"domain":fake_domain,
				"hash":domain_hash,
				"results": _results
			}
		})
	app.logger.info("Testing {} for fake domain".format(fake_domain))
	live_test = requests.get(fake_domain, headers=HEADERS,timeout=5,allow_redirects=True)
	
	if live_test.status_code in [200,301,302,303]:
		app.logger.info('{} domain is live.'.format( fake_domain))

	else:
		app.logger.warning('{} domain is not live.'.format( fake_domain))
		return jsonify({
			"status":"failed",
			"message":"Domain is not live.",
			"results":{
				"original_domain"		:"",
				"fake_domain"			:fake_domain,
				"content_similarity"	: 0,
				#"img_similarity"		: 0,

			}
		})



	html_file_path = os.path.join(FAKE_DOMAIN_HTML_FOLDER_PATH,"{}_raw.html".format(domain_hash))
	save_file(live_test.content, html_file_path)		
	

	_clean_html = get_clean_html(live_test.text)  
	_clean_html_file_path = os.path.join(ORIGINAL_DOMAIN_HTML_FOLDER_PATH,"{}_clean.html".format(domain_hash))
	save_file(_clean_html.encode("utf-8"), _clean_html_file_path)



	_domain = FakeDomain(domain=fake_domain, hash=domain_hash, html_file_path=html_file_path, clean_html_file_path=_clean_html_file_path)	
	db.session.add(_domain)
	db.session.commit()
	




	all_html_files = glob.glob(os.path.join(ORIGINAL_DOMAIN_HTML_FOLDER_PATH,"*.html")) 
	html_content = []

	for _file in all_html_files:


		html_content.append({
			'file'		: _file,
			'hash'		: _file.split("\\")[-1].replace("_clean.html","").replace("_raw.html",""),
			"content" 	: load_file(_file)
		})

	results = []
	for h in html_content:
		app.logger.info("*"*30)
		#app.logger.info(h['hash'])
		
		is_domain_exists = SafeDomain.query.filter_by(hash=h['hash']).first()
		#print(is_domain_exists)
		if is_domain_exists:
			app.logger.info("is_domain_exists - {}".format(is_domain_exists.domain))
		
		
			fuzz_ratio, fuzz_parital_ratio, fuzz_token_sort_ratio, fuzz_token_set_ratio, levenshtein_distance = check_domain_similarity(is_domain_exists.domain, fake_domain)
			app.logger.info("Domain Parameters : ")
			app.logger.info("\toriginal_domain : {}".format( is_domain_exists.domain))
			app.logger.info("\tfake_domain : {}".format( fake_domain))
			app.logger.info("\tfuzz_ratio : {}".format( fuzz_ratio)),
			app.logger.info("\tfuzz_parital_ratio : {}".format( fuzz_parital_ratio))
			app.logger.info("\tfuzz_token_sort_ratio : {}".format( fuzz_token_sort_ratio))
			app.logger.info("\tfuzz_token_set_ratio : {}".format( fuzz_token_set_ratio))
			app.logger.info("\tlevenshtein_distance : {}".format( levenshtein_distance))


			print()
			app.logger.info("Content Parameters: ")
			content_fuzz_ratio = check_content_similarity(h['content'], live_test.text)
			app.logger.info("\tfuzz_ratio : {}".format(content_fuzz_ratio)),



			

			final_domain_score 				= ( (fuzz_ratio + fuzz_parital_ratio + fuzz_token_sort_ratio + fuzz_token_set_ratio + levenshtein_distance) / 500 ) * 100
			final_content_similarity_score 	= content_fuzz_ratio
			app.logger.info("final_domain_score : {}".format(final_domain_score))
			app.logger.info("final_content_similarity_score : {}".format(final_content_similarity_score))

			suspicious_count = 0

			if content_fuzz_ratio >= CONTENT_THREASHOULD or final_domain_score >= DOMAIN_THREASHOULD:

				output = {
					"original_domain": is_domain_exists.domain,
					"fake_domain": fake_domain,
					"domain_similarity":{
						"fuzz_ratio":fuzz_ratio, 
						"fuzz_parital_ratio":fuzz_parital_ratio, 
						"fuzz_token_sort_ratio":fuzz_token_sort_ratio, 
						"fuzz_token_set_ratio":fuzz_token_set_ratio, 
						"levenshtein_distance":levenshtein_distance
					},
					"content_similarity":{
						"fuzz_ratio" : content_fuzz_ratio
					},
					"final_domain_score" : ( (fuzz_ratio + fuzz_parital_ratio + fuzz_token_sort_ratio + fuzz_token_set_ratio + levenshtein_distance) / 500 ) * 100,
					"final_content_similarity_score"  : content_fuzz_ratio
				}
				
				results.append(output)
				print("*"*30)				
				suspicious_count += 1
				_verdict = Verdict( 

					original_domain				= is_domain_exists.domain,
					fake_domain					= fake_domain,
					original_domain_hash		= is_domain_exists.hash,
					fake_domain_hash			= domain_hash,
					original_html_file_path		= h['file'],
					fake_html_file_path			= html_file_path if "_raw" in html_file_path else _clean_html_file_path,
					#original_img_file_path		= ,
					#fake_img_file_path			=,
					content_similarity_score	= final_content_similarity_score,
					domain_similarity_score		= final_domain_score,
					img_similarity_score		= 0,
					verdict						= "suspicious",
				)

				db.session.add(_verdict)
				db.session.commit()	

			# if not results:
			# 	_verdict = Verdict( 

			# 		original_domain				= is_domain_exists.domain,
			# 		fake_domain					= fake_domain,
			# 		original_domain_hash		= is_domain_exists.hash,
			# 		fake_domain_hash			= domain_hash,
			# 		original_html_file_path		= h['file'],
			# 		fake_html_file_path			= html_file_path if "_raw" in html_file_path else _clean_html_file_path,
			# 		#original_img_file_path		= ,
			# 		#fake_img_file_path			=,
			# 		content_similarity_score	= final_content_similarity_score,
			# 		domain_similarity_score		= final_domain_score,
			# 		img_similarity_score		= 0,
			# 		verdict						= "safe",
			# 	)

			# 	db.session.add(_verdict)
			# 	db.session.commit()	

	return jsonify({
		"status":"success",
		"message":"Domain is safe." if not results else "Domain looks suspicious.",
		"results":results
	})


if __name__ == '__main__':
	with app.app_context():
		db.create_all()
	app.run(debug=True, port=5000)