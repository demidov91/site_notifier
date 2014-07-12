import json
from lxml import html
from notifier import NewItemsFetcher

class PlayMarketNotifier(NewItemsFetcher):
    DB_FILE = 'comments_sent.json'

    POST_URL = 'https://play.google.com/store/getreviews'

    post_data = {
        'pageNum': 0,
        'reviewSortOrder': 0,
        'reviewType': 0,
        'xhr': 1,
        'hl': 'ru',
    }

    application_id = None

    def __init__(self, **kwargs):
        super(PlayMarketNotifier, self).__init__(**kwargs)
        self.post_data['id'] = self.application_id

    def doc_to_posts(self, document):
        return document.cssselect('.single-review')

    def get_post_id(self, post):
        return post.cssselect('.review-header')[0].get('data-reviewid')

    def get_post_data(self, post):
        date = post.cssselect('.review-header .review-date')[0].text_content().strip()
        name = post.cssselect('.review-header .author-name')[0].text_content().strip()
        title = post.cssselect('.review-body .review-title')[0].text_content().strip()
        comment_text = post.cssselect('.review-body .review-title')[0].tail
        rate = post.cssselect('.review-info-star-rating .star-rating-non-editable-container')[0].get('aria-label')
        return {
            'date': date,
            'name': name,
            'title': title,
            'text': comment_text,
            'rate': rate,
        }

    def fetch_new_items(self):
        response = self.session.post(self.POST_URL, data=self.post_data)
        if response.status_code >= 400:
            print(response.text)
            return False
        json_source = response.text[response.text.find('['):]
        response_as_json = json.loads(json_source)
        response_as_html = response_as_json[0][2]
        doc = html.fromstring(response_as_html)
        self.new_items = self.fetch_news_from_doc(doc)

    def _record_to_post(self, record):
        return u'{name} {date} {rate}\n{title}\n{text}'.format(**record)