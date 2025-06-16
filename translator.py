import requests

def translate(text, source='auto', target='en'):
    url = 'https://libretranslate.com/translate'
    payload = {
        'q': text,
        'source': source,
        'target': target,
        'format': 'text'
    }
    response = requests.post(url, data=payload)
    return response.json()['translatedText']

print(translate('שלום עולם', target='en'))  # Output: Hello world