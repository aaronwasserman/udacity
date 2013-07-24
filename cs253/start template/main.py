import webapp2
import os
import jinja2
import re
import hashlib
import string
import random
import json
import time

from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import timedelta

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)
                               
class Handler(webapp2.RequestHandler):
	def write(self, *a, **lw):
		self.response.out.write(*a, **lw)


	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)


	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))
			

class MainPage(Handler):
    def get(self):
    	self.write('HelloWorld!')
			
				
app = webapp2.WSGIApplication([
    ('/?', MainPage)
], debug=True)