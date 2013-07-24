import re


# class regexChecking()
# Used for checking if various user inputs (received from an HTTP Post)
# are valid per the following globally defined regular expressions.
#
# If the user input for a function matches, return an instance of MatchObject
# If the user input DOESN'T match, return None.

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASS_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

class regexChecking():
	def username(self, username):
		if username is None:
			return False
		return USER_RE.match(username)
	
	def password(self, password):
		if password is None:
			return False
		return PASS_RE.match(password)
	
	def email(self, email):
		if email is None:
			return False
		return EMAIL_RE.match(email)


