# import logging
import random
import hashlib
import string

from google.appengine.ext import db
from google.appengine.api import memcache


# Used in memcache
USERNAME_PREFIX = 'aw_wiki_user-'
WIKI_PREFIX = 'aw_wiki_page-'



# class User(db.Model)
# Defines the "User" object for the wiki.

# All users will have a username, password, salt (for checking their hashed password),
# and date created.  Email address is optional.

class User(db.Model):
    username = db.StringProperty(required=True)
    salt = db.StringProperty(required=True)
    password = db.StringProperty()
    email = db.EmailProperty()
    created = db.DateTimeProperty(auto_now_add=True)


    @classmethod
    def get_user(cls, username):
        user = memcache.get(USERNAME_PREFIX + username)
        if not user:
            # logging.error('--------------->MC MISS -- USER: %s' % username)
            # logging.error('--------------->DB SRCH -- USER: %s' % username)
            query = User.all()
            query.filter("username =", username)
            user = query.get()
            if user:
                memcache.set(USERNAME_PREFIX + user.username, user)
                # logging.error('--------------->MC ADD -- USER: %s' % user.username)

        return user


    @classmethod
    def hash_pass(cls, password, salt):
        return hashlib.md5(salt + password).hexdigest()


    @classmethod
    def make_salt(cls):
        return "".join(random.choice(string.letters) for x in xrange(5))


    @classmethod
    def insert(cls, user):
        user.put()
        memcache.set(USERNAME_PREFIX + user.username, user)
        # logging.error('--------------->DB PUT -- USER: %s' % user.username)
        # logging.error('--------------->MC ADD -- USER: %s' % user.username)


    @classmethod
    def create(cls, user_form):
        user = User(username=user_form.get('username'), salt=cls.make_salt())
        user.password = cls.hash_pass(user_form.get('password'), user.salt)
        if user_form.get('email'):
            user.email = user_form.get('email')

        cls.insert(user)

        return user


    @classmethod
    def check_pass(cls, user, password):
        if user and password:
            return user.password == cls.hash_pass(password, user.salt)
        else:
            return False


class Wiki(db.Model):
    path = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    author = db.StringProperty(required=True)
    version = db.IntegerProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)


    @classmethod
    def create(cls, wiki_inputs):
        if wiki_inputs:
            path = wiki_inputs.get('path')
            content = wiki_inputs.get('content')
            author = wiki_inputs.get('author')
            version = cls.num_versions(path) + 1

            wiki = Wiki(path=path, content=content, author=author, version=version)
            wiki.put()
            # logging.error('--------------->DB PUT -- WIKI: %s' % wiki.path)
            cls.update_cache(path, wiki)
            return wiki

        else:
            return None


    @classmethod
    def wiki_history(cls, path):
        history = memcache.get(WIKI_PREFIX + '_history' + path)

        if not history:
            q = Wiki.all()
            q.filter("path =", path)
            # logging.error('--------------->MC MISS -- WIKI: %s' % path)
            # logging.error('--------------->DB SRCH -- WIKI: %s' % path)

            if q:
                history = []
                for wiki in q:
                    history.append(wiki)
                memcache.set(WIKI_PREFIX + '_history' + path, history)
                # logging.error('--------------->MC ADD-- WIKI: %s' % path)

        if history:
            history = sorted(history, key=lambda wiki: wiki.version)

        return history


    @classmethod
    def update_cache(cls, path, wiki):
        history = cls.wiki_history(path)

        if history:
            history.append(wiki)
        else:
            history = [wiki]

        memcache.set(WIKI_PREFIX + '_history' + path, history) # update cache (path history -> list of wikis)
        # logging.error('--------------->MC ADD-- WIKI: %s' % path)


    @classmethod
    def get_wiki(cls, path, version):
        wiki = None
        history = cls.wiki_history(path)

        if history:
            num_versions = cls.num_versions(path)

            if not version or int(version) > num_versions:
                wiki = history[num_versions - 1]
            else:
                wiki = history[int(version) - 1]

        return wiki


    @classmethod
    def num_versions(cls, path):
        history = cls.wiki_history(path)

        if history:
            num_versions = len(history)
        else:
            num_versions = 0

        return num_versions

