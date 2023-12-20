import jsonschema
import requests
import copy
from datetime import datetime
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rorapi.common.models import Errors

NOW = datetime.now()

ADMIN = {
    "created": {
        "date": NOW.strftime("%Y-%m-%d"),
        "schema_version": "2.0"
    },
    "last_modified": {
        "date": NOW.strftime("%Y-%m-%d"),
        "schema_version": "2.0"
    }
}

LAST_MOD = {
    "date": NOW.strftime("%Y-%m-%d"),
    "schema_version": "2.0"
}

OPTIONAL_FIELD_DEFAULTS = {
    "domains": [],
    "established": None,
    "external_ids": [],
    "links": [],
    "relationships": []
}

def update_record(json_input, existing_record):
    record = copy.deepcopy(existing_record)
    for k, v in json_input.items():
        record[k] = copy.deepcopy(v)
    return record

def update_last_mod(record):
    record['admin']['last_modified'] = copy.deepcopy(LAST_MOD)
    return record

def check_optional_fields(record):
    for k in OPTIONAL_FIELD_DEFAULTS:
        if k not in record:
            return True
    return False

def add_missing_optional_fields(record):
    for k, v in OPTIONAL_FIELD_DEFAULTS.items():
        if k not in record:
            record[k] = v
    return record

def add_created_last_mod(record):
    record['admin'] = copy.deepcopy(ADMIN)
    return record

def get_file_from_url(url):
    rsp = requests.get(url)
    rsp.raise_for_status()
    return rsp.json()

def validate_v2(data):
    errors = []
    schema = get_file_from_url("https://raw.githubusercontent.com/ror-community/ror-schema/schema-v2/ror_schema_v2_0.json")
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as error:
        errors.append(error)
        return Errors(errors), None
    else:
        return None, data