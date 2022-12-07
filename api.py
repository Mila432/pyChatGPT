import requests
import json
import uuid
import time
from flask import Flask,request
from threading import Thread
app = Flask(__name__)

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def loadcookies():
	with open('c.json','r') as f:
		return requests.utils.cookiejar_from_dict(json.load(f))

def savecookies(ck):
	with open('c.json','w') as f:
		json.dump(requests.utils.dict_from_cookiejar(ck), f)

class API(object):
	def __init__(self):
		self.s=requests.Session()
		self.s.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0','Accept':'text/event-stream','Accept-Language':'en-US,en;q=0.5','Accept-Encoding':'gzip, deflate, br','Referer':'https://chat.openai.com/chat','Content-Type':'application/json','X-OpenAI-Assistant-App-Id':'','Origin':'https://chat.openai.com','Sec-Fetch-Dest':'empty','Sec-Fetch-Mode':'cors','Sec-Fetch-Site':'same-origin'})
		self.s.verify=False
		self.noModeration=True

	def ask(self,question,isnext=True,isvariant=False):
		if not hasattr(self,'parent_message_id'):
			self.parent_message_id=str(uuid.uuid4())
		if not hasattr(self,'_id'):
			self._id=str(uuid.uuid4())
		self.getsession()
		self.moderations(question)
		return self.conversation(question,isnext,isvariant)

	def moderations(self,question):
		if self.noModeration:	return
		r=self.s.post('https://chat.openai.com/backend-api/moderations',json={"input":question,"model":"text-moderation-playground"},headers={'content-type':'application/json','authorization':'Bearer %s'%(self.accessToken)})
		return json.loads(r.content)['moderation_id']

	def conversation(self,question,isnext=True,isvariant=False):
		if isvariant and hasattr(self,'conversation_id'):
			jdata={"action":"variant","messages":[{"id":self._id,"role":"user","content":{"content_type":"text","parts":[question]}}],"conversation_id":self.conversation_id,"parent_message_id":self.parent_message_id,"model":"text-davinci-002-render"}
		elif isnext and hasattr(self,'conversation_id'):
			jdata={"action":"next","messages":[{"id":self._id,"role":"user","content":{"content_type":"text","parts":[question]}}],"conversation_id":self.conversation_id,"parent_message_id":self.parent_message_id,"model":"text-davinci-002-render"}
		else:
			jdata={"action":"next","messages":[{"id":self._id,"role":"user","content":{"content_type":"text","parts":[question]}}],"parent_message_id":self.parent_message_id,"model":"text-davinci-002-render"}
		r=self.s.post('https://chat.openai.com/backend-api/conversation',json=jdata,headers={'content-type':'application/json','authorization':'Bearer %s'%(self.accessToken)},stream=True)
		try:
			data= r.content.decode().split('\n\n')[-3]
		except:
			print(r.content)
			return None
		jdata=json.loads(data.split('data: ')[-1])
		return 'question:|%s|conversation_id:%s,%s,%s,%s||\n\n'%(question,jdata['conversation_id'],jdata["message"]["id"],self.parent_message_id,self._id)+jdata['message']['content']['parts'][0]

	def keepsession(self):
		while(1):
			self.getsession()
			time.sleep(60*4)

	def getsession(self):
		r=self.s.get('https://chat.openai.com/api/auth/session',cookies=loadcookies())
		self.accessToken=json.loads(r.content)['accessToken']
		savecookies(self.s.cookies)

@app.route('/ask',methods=['POST'])
def path_ask():
	a=API()
	question=request.form.get('question')
	_id=request.form.get('_id')
	conversation_id=request.form.get('conversation_id')
	parent_message_id=request.form.get('parent_message_id')
	if conversation_id:
		a.conversation_id=conversation_id
	if parent_message_id:
		a.parent_message_id=parent_message_id
	if bool(conversation_id and _id):
		if _id:
			a._id=_id
	isvariant=bool(conversation_id and _id)
	isnext=bool(True and not isvariant)
	return a.ask(question,isnext,isvariant)

if __name__ == "__main__":
	Thread(target = API().keepsession).start()
	app.jinja_env.auto_reload = True
	app.run(host='0.0.0.0',port=88,debug=True,threaded=True)
