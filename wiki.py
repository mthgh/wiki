import webapp2
import jinja2
import os
import func

from google.appengine.ext import db
from google.appengine.api import memcache

temp_dir=os.path.join(os.path.dirname(__file__),'template')
jinja_env=jinja2.Environment(loader = jinja2.FileSystemLoader(temp_dir),
                             autoescape = True)

def user_key(parent='default'):
    return db.Key.from_path('UserInfo', parent)

class UserInfo(db.Model):
    username = db.StringProperty(required=True)
    pw = db.StringProperty(required=True)
    email = db.EmailProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)

    @classmethod
    def by_name(cls, username):
        return UserInfo.all().filter('username =', username).get()

    @classmethod
    def regist(cls,username, pw, email):
        u = UserInfo(username=username,
                     pw=func.hash_pw(username, pw),
                     email=db.Email(email),
                     parent=user_key())
        u.put()

def wiki_key(parent='default'):
    return db.Key.from_path('WikiInfo', parent)

class WikiInfo(db.Model):
    path = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    username = db.StringProperty(required=True)

    @classmethod
    def by_path(cls, path):
        return WikiInfo.all().filter('path =', path).order("-created")

    @classmethod
    def regist(cls, path, content, username):
        w = WikiInfo(path=path,
                     content=content,
                     username=username,
                     parent=wiki_key())
        w.put()

class Cache():
    @classmethod
    def name_uinfo(cls, username, update=False):
        key = "uinfo"+username
        if not memcache.get(key) or update:
            value = UserInfo.by_name(username)
            if value:
                memcache.set(key, value)
        return memcache.get(key)

    @classmethod
    def path_wiki(cls, path, update=False):
        key = 'wiki'+path
        if not memcache.get(key) or update:
            value = WikiInfo.by_path(path)
            if value:
                memcache.set(key, value)
        return memcache.get(key)

class BasicHandler(webapp2.RequestHandler):
    def render_str(self, template, **params):
        temp = jinja_env.get_template(template)
        return temp.render(params)

    def render(self, template, **params):
        return self.response.write(self.render_str(template, **params))

    def write(self, *a, **kw):
        return self.response.write(*a, **kw)

    def set_cookie(self, username):
        return self.response.set_cookie('user', func.hash_user(username), overwrite=True)

    def del_cookie(self):
        return self.response.delete_cookie('user')

    def get_cookie(self):
        return self.request.cookies.get('user')

    def get_user(self):
        h = self.get_cookie()
        if h:
            return func.uhash_user(h)

    def if_user(self, page):
        username = self.get_user()
        if username:
            self.redirect('/')
        else:
            self.render(page)

    def version(self, path, v):
        #q = WikiInfo.all().filter('path = ', path).order("-created")
        q  = Cache.path_wiki(path)
        if not q:
            q=''
        else:
            if not v or int(v)==0:
                q = q.get()
            else:
                try:
                    q = q.fetch(limit=int(v)+1)[int(v)]
                except:
                    "IndexError"
                    q = 'error'
        return q

class MainPage(BasicHandler):
    def get(self, error=''):
        username = self.get_user()
        self.render('mainpage.html', username=username)


class EditPage(BasicHandler):
    def get(self, path):
        username = self.get_user()
        if username:
            v = self.request.get('v')
            q = self.version(path, v)
            if not q:
                content=''
            elif q=='error':
                return self.error(404)
            else:
                content=q.content
            self.render('editpage.html', content=content,
                                         username=username,
                                         path=path)
        else:
            self.redirect('/')
            
    def post(self, path):
        content = self.request.get('content')
        username = self.get_user()
        if content:
            WikiInfo.regist(path, content, username)
            Cache.path_wiki(path, update=True)
            self.redirect(path)
        else:
            error = "Please input content"
            self.render('editpage.html', username=username,
                                             error=error)

class WikiPage(BasicHandler):
    def get(self, path):
        v = self.request.get('v')
        q = self.version(path, v)
        if not q:
            self.redirect('/_edit%s' %(path))
        elif q == 'error':
            return self.error(404)
        else:
            username = self.get_user()
            self.render('wikipage.html', q=q,
                                         path = path,
                                         username = username)
    
class PageHistory(BasicHandler):
    def get(self, path):
        username = self.get_user()
        q  = Cache.path_wiki(path).fetch(limit=100)
        self.render('history.html', q=q,
                                   username=username,
                                   path=path)

class Signup(BasicHandler):
    def get(self):
        self.if_user('signup.html')

    def post(self, error1='', error2='', error3='', error4=''):
        username = self.request.get('username')
        pw = self.request.get('pw')
        verify = self.request.get('verify')
        email = self.request.get('email')

        c_username = func.check_uname(username)
        c_pw = func.check_pw(pw)
        c_email = func.check_email(email)

        user_exist = Cache.name_uinfo(username)

        if user_exist:
            error1='This username has already been used'
            self.render('signup.html', error1=error1,
                                       username=username,
                                       email=email)
        else:   
        
            if c_username and c_pw and c_email and pw == verify:
                UserInfo.regist(username, pw, email)
                self.set_cookie(username)
                self.redirect('/')
                
            else:
                if not c_username:
                    error1 = 'Please input a valid username'
                if not c_pw:
                    error2 = 'Please input a valid password'
                if not c_email:
                    error4 = 'Please input a valid email'
                elif pw!=verify:
                    error3 = "Password doesn't match"
                self.render('signup.html', error1=error1,
                                           error2=error2,
                                           error3=error3,
                                           error4=error4,
                                           username=username,
                                           email=email)

class Login(BasicHandler):
    def get(self):
        self.if_user('login.html')
    def post(self):
        username = self.request.get('username')
        pw = self.request.get('pw')
        q = Cache.name_uinfo(username)
        if q and func.uhash_pw(username, pw, str(q.pw)):
            self.set_cookie(username)
            self.redirect('/')
        else:
            self.render('login.html', error="Wrong username or password",
                                      username=username)

class Logout(BasicHandler):
    def get(self):
        self.del_cookie()
        self.redirect('/')
            

PAGE_RE = r'(/(?:[a-zA-Z0-9-_]+/?)*)'
app = webapp2.WSGIApplication([('/', MainPage),
                               ('/signup', Signup),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/_edit'+PAGE_RE, EditPage),
                               ('/_history' + PAGE_RE, PageHistory),
                               (PAGE_RE, WikiPage),
                               ],
                              debug=True)
