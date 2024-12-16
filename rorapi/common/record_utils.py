import jsonschema
import requests
from iso639 import Lang


def get_lang_code(lang_string):
    lang_code = None
    error = None
    if len(lang_string) == 2:
        lang_string = lang_string.lower()
    else:
        lang_string = lang_string.title()
    try:
        lg = Lang(lang_string)
        lang_code = lg.pt1
    except Exception as e:
        error = e.msg
    return error, lang_code

def get_file_from_url(url):
    rsp = requests.get(url)
    rsp.raise_for_status()
    return rsp.json()

def validate_record(data, schema):
    try:
        print("validating data:")
        print(data)
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        return "Validation error: " + e.message, None
    else:
        return None, data

