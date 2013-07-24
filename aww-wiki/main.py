import webapp2
import os
import jinja2
import utilities
import models

from google.appengine.api import memcache

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), extensions=['jinja2.ext.autoescape'])


class Handler(webapp2.RequestHandler):
    logged_in_user = None

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

        if user_cookie:
            username, uid = self.parse_cookie(user_cookie)
            user = models.User.get_user(username)
            if user:
                if int(uid) == user.key().id():
                    return user
        else:
            return None

    def make_secure_cookie(self, user):
        username = str(user.username)
        uid = str(user.key().id())
        self.response.headers.add_header('Set-Cookie', 'user_id=%s|%s; Path=/' % (username, uid))

    def get_user_inputs(self, case=''):
        if case == 'signup' or case == 'login':
            user_inputs = {'username': self.fetch('username'), 'password':
                self.fetch('password')}
            if case == 'signup':
                user_inputs['verify'] = self.fetch('verify')
                user_inputs['email'] = self.fetch('email')

        elif case == 'edit':
            user_inputs = {'content': self.fetch('content')}

        else:
            return None

        return user_inputs

    def get_input_errors(self, inputs, case=''):
        errors_exist = False
        errors = inputs

        if case == 'signup':
            username = inputs.get('username')
            password = inputs.get('password')
            verify = inputs.get('verify')
            email = inputs.get('email')

            re_check = utilities.regexChecking()

            if not re_check.username(username):
                errors['username_error'] = 'Invalid username.'
                errors_exist = True
            elif models.User.get_user(username):
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
            user = models.User.get_user(username)

            if not user or not user.check_pass(user, password):
                errors['login_error'] = 'Invalid credentials. Please try again.'
                errors_exist = True

        elif case == 'edit':
            content = inputs.get('content')

            if not content:
                errors['post_error'] = "Please enter content (html or plain text)."
                errors_exist = True

        return errors if errors_exist else None

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        global logged_in_user
        logged_in_user = self.check_secure_cookie()
        # if logged_in_user:
        #     logging.error('Logged in!')
        # else:
        #     logging.error('Not logged in!')


class Signup(Handler):
    def get(self):
        self.render('wiki_signup.html')

    def post(self):
        inputs = self.get_user_inputs('signup')
        errors = self.get_input_errors(inputs, 'signup')

        if not errors:
            new_user = models.User.create(inputs)
            self.make_secure_cookie(new_user)
            self.redirect('/')
        else:
            self.render('wiki_signup.html', **errors)


class Login(Handler):
    def get(self):
        self.render('wiki_login.html')

    def post(self):
        inputs = self.get_user_inputs('login')
        errors = self.get_input_errors(inputs, 'login')

        if not errors:
            user = models.User.get_user(inputs.get('username'))
            self.make_secure_cookie(user)
            self.redirect('/')
        else:
            self.render('wiki_login.html', **errors)


class Logout(Handler):
    def get(self, path):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')
        self.redirect(path)


class EditPage(Handler):
    def get(self, path):
        global logged_in_user
        v = self.fetch('v')

        wiki = models.Wiki.get_wiki(path, v)

        if logged_in_user:
            if wiki:
                self.render('wiki_edit.html', username=logged_in_user.username, path=path,
                            content=wiki.content, version=wiki.version)
            else:
                self.render('wiki_edit.html', username=logged_in_user.username, path=path, version="1")
        else:
            self.redirect('/logout/')

    def post(self, path):
        global logged_in_user

        if not logged_in_user:
            self.redirect('/login/')
        else:
            inputs = self.get_user_inputs('edit')
            errors = self.get_input_errors(inputs, 'edit')

            if errors:
                self.render('wiki_edit.html', username=logged_in_user.username,
                            path=path, post_error=errors.get('post_error'))
            else:
                inputs['path'] = path
                inputs['author'] = logged_in_user.username

                new_wiki = models.Wiki.create(inputs)
                self.redirect(new_wiki.path)


class History(Handler):
    def get(self, path):
        global logged_in_user
        wiki_history = models.Wiki.wiki_history(path)
        wiki_history.reverse()
        self.render('wiki_history.html', user=logged_in_user, path=path, history=wiki_history)


class WikiPage(Handler):
    def get(self, path):
        global logged_in_user
        v = self.fetch('v')

        wiki = models.Wiki.get_wiki(path, v)

        if wiki:
            self.render('wiki_home.html', user=logged_in_user, path=path, content=str(wiki.content))
        elif logged_in_user:
            self.redirect('/_edit' + path)
        else:
            self.redirect('/login/')


class Flush(Handler):
    def get(self):
        memcache.flush_all()
        self.redirect('/')


PAGE_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)'
app = webapp2.WSGIApplication([('/signup/?', Signup),
                               ('/login/?', Login),
                               ('/logout' + PAGE_RE, Logout),
                               ('/_edit' + PAGE_RE, EditPage),
                               ('/_history' + PAGE_RE, History),
                               ('/flush/?', Flush),
                               (PAGE_RE, WikiPage)
                              ],
                              debug=True)
