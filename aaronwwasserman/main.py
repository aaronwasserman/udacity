import logging
import webapp2
import os
import jinja2
import blogutils
import blogmodels

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

	def fetch(self, url_parameter):
		return self.request.get(url_parameter)

	def parse_cookie(self, user_cookie):
		username = user_cookie.split('|')[0]
		uid = user_cookie.split('|')[1]
		return username, uid

	def check_secure_cookie(self):
		user_cookie = self.request.cookies.get('user_id')
		cookie_secure = True
		
		if user_cookie:
			username, uid = self.parse_cookie(user_cookie)
			user = blogmodels.User.get_user(username)
			if not user:
				cookie_secure = False
			elif not int(uid) == user.key().id():
				cookie_secure = False

		return cookie_secure					
		
	def make_secure_cookie(self, user):
		username = str(user.username)
		uid = str(user.key().id())
		self.response.headers.add_header('Set-Cookie', 'user_id=%s|%s; Path=/' % (username, uid))

	def get_user_inputs(self, case = ''):
		if case == 'signup' or case == 'login':
			user_inputs = {'username' : self.fetch('username'), 'password' : 
							self.fetch('password')}
			if case == 'signup':
				user_inputs['verify'] = self.fetch('verify')
				user_inputs['email'] = self.fetch('email')
		
		elif case == 'newpost':
			user_inputs = {'subject' : self.fetch('subject'), 
							'content' : self.fetch('content')}
		
		else:
			return None

		return user_inputs

	def get_input_errors(self, inputs, case = ''):
		errors_exist = False
		errors = inputs
		
		if case == 'signup':
			username = inputs.get('username')
			password = inputs.get('password')
			verify = inputs.get('verify')
			email = inputs.get('email')
			
			re_check = blogutils.regexChecking()
						
			if not re_check.username(username):
				errors['username_error'] = 'Invalid username.'
				errors_exist = True
			elif blogmodels.User.get_user(username):
				errors['username_error'] = 'Username already exists.'
				errors_exist = True
			if not re_check.password(password):
				errors['password_error'] = 'Invalid password.'
				errors_exist = True
			elif password != verify:
				errors['verify_error'] = "Passwords don't match."
				errors_exist = True
			if email and not re_check.email(email):
				errors['email_error'] = "Invalid email address."
				errors_exist = True
		
		elif case == 'login':
			username = inputs.get('username')
			password = inputs.get('password')
			user = blogmodels.User.get_user(username)
			
			if not user or not user.check_pass(user, password):
				errors['login_error'] = 'Invalid credentials. Please try again.'
				errors_exist = True
		
		elif case == 'newpost':
			subject = inputs.get('subject')
			content = inputs.get('content')
			
			if not subject or not content:
				errors['newpost_error'] = 'Please provide both subject and content.'
				errors_exist = True

		return errors if errors_exist else None	

	def initialize(self, *a, **kw):
		webapp2.RequestHandler.initialize(self, *a, **kw)
		if self.check_secure_cookie():
			logging.error('Logged in!')
		else:
			logging.error('Not logged in!')
			self.redirect('/logout')




class MainPage(Handler):
	def get(self, blog_id = None, json = False):
		if blog_id:
			blog = blogmodels.Blog.get_blog(blog_id)

			if blog: # Blog passed in URL was valid
				if json:
					self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
					blog_json = blogutils.renderJSON([blog])
					self.write(blog_json)
				else:
					self.render('blog_home.html', front_page = [blog], cache_age = blog.cache_age)
			
			else: # Blog passed in URL was not valid (or no longer found within the db)
				self.redirect('/')

		else:
			front_page, cache_age = blogmodels.Blog.most_recents()
			if json:
				self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
				front_json = blogutils.renderJSON(front_page)
				self.write(front_json)
			else:
				self.render('blog_home.html', front_page = front_page, cache_age = cache_age)




class Signup(Handler):
	def get(self):
		self.render('blog_signup.html')

	def post(self):
		inputs = self.get_user_inputs('signup')
		errors = self.get_input_errors(inputs, 'signup')

		if not errors:
			new_user = blogmodels.User.create(inputs)
			self.make_secure_cookie(new_user)
			self.redirect('/welcome/')
		else:
			self.render('blog_signup.html', **errors)




class Login(Handler):
	def get(self):
		self.render('blog_login.html')

	def post(self):
		inputs = self.get_user_inputs('login')
		errors = self.get_input_errors(inputs, 'login')

		if not errors:
			user = blogmodels.User.get_user(inputs.get('username'))
			self.make_secure_cookie(user)
			self.redirect('/welcome/')
		else:
			self.render('blog_login.html', **errors)




class Logout(Handler):
	def get(self):
		self.response.headers.add_header('Set-Cookie','user_id=; Path=/')
		self.redirect('/login')




class Welcome(Handler):
	def get(self):
		self.render('blog_welcome.html')




class NewPost(Handler):
    def get(self):
    	self.render('blog_newpost.html')
    	
    
    def post(self):
        inputs = self.get_user_inputs('newpost')
        errors = self.get_input_errors(inputs, 'newpost')
        
        if not errors:
            new_blog_id = blogmodels.Blog.create(inputs)
            self.redirect('/%s' % new_blog_id)
        else:
            self.render('blog_newpost.html', **errors)
            
            				


class Flush(Handler):
	def get(self, blog_id = None):
		if blog_id:
			blogmodels.Blog.flush_blog(blog_id)
			self.redirect('/%s' % blog_id)
		else:
			memcache.flush_all()
			self.redirect('/')


		


app = webapp2.WSGIApplication([
    ('/(\d+)?(/?json)?/?', MainPage),
    ('/signup/?', Signup),
    ('/login/?', Login),
    ('/logout/?', Logout),
	('/welcome/?', Welcome),    
    ('/newpost/?', NewPost),
    ('/?(\d+)?(?:/flush)/?', Flush)
], debug=True)
