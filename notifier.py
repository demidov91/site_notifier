from lxml import html
from requests import Session
import os
import urllib
import json
import defines
from defines import TARGET_URL, EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL,\
    SEND_TO, LOGOUT_URL
import smtplib
from email.mime.text import MIMEText
from lockfile import FileLock

MAX_BAD_ATTEMPTS = 3

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

class NewItemsFetcher:
    DB_FILE = 'used_posts.json'
    target_url = TARGET_URL
    send_to = SEND_TO

    already_read_items = []
    new_items = None
    session = Session()

    lock = None

    def _get_db_lock_name(self):
        return self.get_db_filename() + '.lock'

    def get_db_filename(self):
        return os.path.join(CURRENT_DIR, self.DB_FILE)

    def __init__(self, **kwargs):
        if not os.path.exists(self.get_db_filename()):
            with open(self.get_db_filename(), 'w') as f:
                json.dump([], f)
        self.lock = FileLock(self._get_db_lock_name())
        self.lock.acquire()
        with open(self.get_db_filename(), 'r') as f:
            self.already_read_items = json.loads(f.read())
        self.session.post(defines.LOGIN_URL, data={
            'email': defines.SITE_USER,
            'password': defines.SITE_PASSWORD,
        })
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def fetch_new_items(self):
        response = self.session.get(self.target_url)
        if response.status_code >= 400:
            return False
        doc = html.fromstring(response.text)
        new_news = []
        for post in doc.cssselect('#contentIns .item'):
            id = post.get('id')
            print(u'Processing post {0}'.format(id))
            if id in self.already_read_items:
                continue
            else:
                self.already_read_items.append(id)
            price = post.cssselect('.nprice20, .nprice30')[0].text_content().strip()
            place = post.cssselect('.it_title>address>a')[0].text_content().strip()
            time = post.cssselect('.it_date')[0].text_content().strip()
            phone = post.cssselect('ul.contact-data .icon-phone strong')[0].text_content().strip()
            text = post.cssselect('.it_message>h2')[0].tail.strip()
            link = post.cssselect('.it_title>address>a')[0].get('href')
            new_news.append({
                'price': price,
                'place': place,
                'time': time,
                'text': text,
                'phone': phone,
                'link': link,
            })
        print('{0} new items is fetched.'.format(len(new_news)))
        self.new_items = new_news

    def _record_to_post(self, record):
        return u'{price} {place}\n{text}\n{phone}\n{link}\n{time}'.format(**record)

    def send_new_items(self):
        if not len(self.new_items):
            print('There is nothing to send.')
            return
        message = u'{0} new posts:\n{1}'.format(
            len(self.new_items),
            u'\n---------------\n'.join(self._record_to_post(x) for x in self.new_items)
        )
        print(u'Trying to send: {0}'.format(message))
        email = MIMEText(message, _charset='utf-8')
        email['Subject'] = 'New posts on neagent.'
        email['From'] = DEFAULT_FROM_EMAIL
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server_response = server.sendmail(DEFAULT_FROM_EMAIL, self.send_to, email.as_string())
        print('Email is sent. Response is {0}'.format(server_response))
        with open(self.get_db_filename(), 'w') as f:
            json.dump(self.already_read_items, f)
        print('DB is updated.')
        self.session.post(LOGOUT_URL, data={'act': 'logout'})

    def __del__(self):
        self.lock.release()


def send_new_posts():
    fetcher = NewItemsFetcher()
    fetcher.fetch_new_items()
    fetcher.send_new_items()


if __name__ == '__main__':
    send_new_posts()
