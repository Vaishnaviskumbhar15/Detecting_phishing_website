
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class SafeDomain(db.Model):
	__tablename__ 	= "safe_domains"

	id 				= db.Column(db.Integer, primary_key=True)
	domain 			= db.Column(db.Text, nullable=False)

	hash 					= db.Column(db.Text, nullable=False)
	html_file_path 			= db.Column(db.Text, nullable=True)
	clean_html_file_path 	= db.Column(db.Text, nullable=True)
	img_file_path 			= db.Column(db.Text, nullable=True)
	

	def __repr__(self):
		return f"ID: {self.id}\nDomain: {self.domain}\nHash: {self.hash}"

class FakeDomain(db.Model):
	__tablename__ 	= "fake_domains"

	id 							= db.Column(db.Integer, primary_key=True)
	domain 						= db.Column(db.Text, nullable=False)
	
	hash 						= db.Column(db.Text, nullable=False)
	
	html_file_path 				= db.Column(db.Text, nullable=True)
	img_file_path 				= db.Column(db.Text, nullable=True)
	
	clean_html_file_path 	= db.Column(db.Text, nullable=True)	

	def __repr__(self):
		return f"ID: {self.id}\nOriginal Domain: {self.domain}\nHash: {self.hash}"		


class Verdict(db.Model):
	__tablename__ 	= "verdicts"

	id 							= db.Column(db.Integer, primary_key=True)
	original_domain 			= db.Column(db.Text, nullable=True)
	fake_domain 				= db.Column(db.Text, nullable=False)

	original_domain_hash 		= db.Column(db.Text, nullable=True)
	fake_domain_hash 			= db.Column(db.Text, nullable=False)
	
	original_html_file_path 	= db.Column(db.Text, nullable=True)
	fake_html_file_path 		= db.Column(db.Text, nullable=True)
	
	original_img_file_path 		= db.Column(db.Text, nullable=True)
	fake_img_file_path 			= db.Column(db.Text, nullable=True)
	
	content_similarity_score	= db.Column(db.Float, nullable=True)
	domain_similarity_score		= db.Column(db.Float, nullable=True)
	img_similarity_score		= db.Column(db.Float, nullable=True)
	
	verdict		= db.Column(db.Text, nullable=True,default="safe")
	

	def __repr__(self):
		return f"ID: {self.id}\nOriginal Domain: {self.original_domain}\nFake domain: {self.fake_domain}"				