import re
import random
import string
import hmac
import hashlib

SECRET = 'DhTEEtdSUQqMOQfE'

def check_uname(username):
    pattern = re.compile(r"^[a-zA-Z0-9-_]{3,20}$")
    return pattern.match(username)

def check_pw(pw):
    pattern = re.compile(r"^.{3,20}$")
    return pattern.match(pw)

def check_email(email):
    pattern = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
    return pattern.match(email)

def make_salt():
    salt = ''.join(random.choice(string.ascii_letters) for i in range(0,16))
    return salt
    

def hash_pw(username, pw, salt=''):
    if not salt:
        salt = make_salt()
    p = hmac.new(salt, pw+username, hashlib.sha256).hexdigest()
    return '%s|%s'%(salt,p)

def uhash_pw(username, pw, h):
    salt = h.split('|')[0]
    if h == hash_pw(username, pw, salt):
        return True

def hash_user(username):
    value = hmac.new(SECRET, username, hashlib.sha256).hexdigest()
    return "%s|%s" %(username, value)

def uhash_user(h):
    username = h.split('|')[0]
    if hash_user(username)==h:
        return username
    

h = "ABkSDThyoIfXZwOh|294427026c2219bd7233b69cefbe4bcab1e6bb032cb3b0728255e397871b3f2e"

print uhash_pw('djin', '', h)

