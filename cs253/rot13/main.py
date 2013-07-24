#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import cgi

form = """
    <div style="font-family: Courier; font-size: 20pt;">Rot13 Encrypter</div>
    <p>
        <div style="font-family: Courier; font-size: 12pt;">Enter some text to begin:</div>
        <form method="post">
            <textarea name="text" rows="10" cols="100">%(prev_text)s</textarea>
            <br>
            <input type="submit">
        <form>
    </p>
    
    """

def cgi_escape(i):
    return cgi.escape(i)

def convert_rot13(i):
    result = ""
    
    for ch in i:
        index = ord(ch)
        
        # if (ch is a character between 'A' -> 'Z')
        if (index >= 65 and index <= 90):
            index += 13
            if index > 90:
                index -= 26
        # elif (ch is a character between 'a' -> 'z')
        elif (index >= 97 and index <= 122):
            index += 13
            if index > 122:
                index -= 26
    
        result += chr(index)
    
    return cgi.escape(result)


class MainHandler(webapp2.RequestHandler):
    def show_form(self, text=""):
        self.response.out.write(form % {
                                "prev_text": text
                                })
    def get(self):
        self.show_form()

    def post(self):
        i = self.request.get("text")
        result = convert_rot13(i)

        self.show_form(result)

        #self.response.headers['Content-Type'] = 'text/plain'
        #self.response.out.write(strip(i))



app = webapp2.WSGIApplication([
    ('/', MainHandler),
], debug=True)





#self.response.headers['Content-Type'] = 'text/plain'