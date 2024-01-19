import jsonschema
import requests
import copy
import csv
import json
import io
from datetime import datetime
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rorapi.common.models import Errors
import update_address as ua

from rorapi.management.commands.generaterorid import check_ror_id

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

CSV_REQUIRED_FIELDS = (
    "id",
    "domains",
    "established",
    "external_ids.type.fundref.all",
    "external_ids.type.fundref.preferred",
    "external_ids.type.grid.all",
    "external_ids.type.grid.preferred",
    "external_ids.type.isni.all",
    "external_ids.type.isni.preferred",
    "external_ids.type.wikidata.all",
    "external_ids.type.wikidata.preferred",
    "links.type.website",
    "links.type.wikipedia",
    "locations.geonames_id",
    "names.types.acronym",
    "names.types.alias",
    "names.types.label",
    "names.types.ror_display",
    "status",
    "types"
)

V2_TEMPLATE = {
    "locations": [],
    "established": None,
    "external_ids": [],
    "id": "",
    "domains": [],
    "links": [],
    "names": [],
    "relationships": [],
    "status": "",
    "types": [],
    "admin": {}
}

V2_EXTERNAL_ID_TYPES = {
                        "FUNDREF" : "fundref",
                        "GRID" : "grid",
                        "ISNI" : "isni",
                        "WIKIDATA" : "wikidata"
                    }

V2_LINK_TYPES = {
                "WEBSITE" : "website",
                "WIKIPEDIA" : "wikipedia"
            }

V2_NAME_TYPES = {
                "ACRONYM" : "acronym",
                "ALIAS" : "alias",
                "LABEL" : "label",
                "ROR_DISPLAY" : "ror_display"
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

def update_locations(locations):
    errors = []
    updated_locations = []
    for location in locations:
        if 'geonames_id' in location:
            try:
                print(location['geonames_id'])
                updated_location = ua.new_geonames_v2(str(location['geonames_id']))
                updated_locations.append(updated_location['location'])
            except:
                errors.append("Error retrieving Geonames data for ID {}. Please check that this is a valid Geonames ID".format(location['geonames_id']))
    return errors, updated_locations

def get_file_from_url(url):
    rsp = requests.get(url)
    rsp.raise_for_status()
    return rsp.json()

def validate_v2(data):
    errors = []
    schema = get_file_from_url("https://raw.githubusercontent.com/ror-community/ror-schema/schema-v2/ror_schema_v2_0.json")
    try:
        print("validating data:")
        print(data)
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as error:
        errors.append(error)
        print(errors)
        return Errors(errors), None
    else:
        return None, data

def validate_csv(csv_file):
    errors = []
    try:
        read_file = csv_file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(read_file))
        rowcount = 0
        for row in reader:
            rowcount += 1
        if rowcount > 0:
            csv_fields = reader.fieldnames
            missing_fields = []
            for field in CSV_REQUIRED_FIELDS:
                if field not in csv_fields:
                    missing_fields.append(field)
            print(missing_fields)
            if len(missing_fields) > 0:
                errors.append(f'CSV file is missing columns: {", ".join(missing_fields)}')
        else:
            errors.append("CSV file contains no data rows")
    except IOError as e:
        errors.append(f"Error parsing CSV file: {e}")
    print(errors)
    return errors

def new_record_from_json(json_input, version):
    errors = None
    valid_data = None
    new_record = copy.deepcopy(json_input)
    if check_optional_fields(new_record):
        new_record = add_missing_optional_fields(new_record)
    location_errors, updated_locations = update_locations(new_record['locations'])
    if len(location_errors) > 0:
        errors = Errors(location_errors)
    else:
        new_record['locations'] = updated_locations
        new_record = add_created_last_mod(new_record)
        new_ror_id = check_ror_id(version)
        new_record['id'] = new_ror_id
        # handle admin
        errors, valid_data = validate_v2(new_record)
    return errors, valid_data


def new_record_from_csv(csv_data, version):
    v2_data = copy.deepcopy(V2_TEMPLATE)
    if csv_data['domains']:
        v2_data['domains'] = [d.strip() for d in csv_data['domains'].split(';')]

    if csv_data['established']:
        v2_data['established'] = int(csv_data['established'].strip())

    for k,v in V2_EXTERNAL_ID_TYPES.items():
        if csv_data['external_ids.type.' + v + '.all']:
            ext_id_obj = {
                "type": v,
                "all": [i.strip() for i in csv_data['external_ids.type.' + v + '.all'].split(';')],
                "preferred": csv_data['external_ids.type.' + v + '.preferred'].strip() if csv_data['external_ids.type.' + v + '.preferred'] else None
            }
            v2_data['external_ids'].append(ext_id_obj)

    for k,v in V2_LINK_TYPES.items():
        if csv_data['links.type.' + v]:
            link_obj = {
                "type": v,
                "value": csv_data['links.type.' + v].strip()
            }
            v2_data['links'].append(link_obj)

    if csv_data['locations.geonames_id']:
        geonames_ids = [i.strip() for i in csv_data['locations.geonames_id'].split(';')]
        for geonames_id in geonames_ids:
            location_obj = {
                "geonames_id": geonames_id,
                "geonames_details": {}
            }
            v2_data['locations'].append(location_obj)

    temp_names = []
    for k,v in V2_NAME_TYPES.items():
        if csv_data['names.types.' + v]:
            name_obj = {
                "types": v,
                "value": csv_data['names.types.' + v].strip()
            }
            temp_names.append(name_obj)
    print("temp names 1:")
    print(temp_names)
    name_values = [n['value'] for n in temp_names]
    dup_names = []
    for n in name_values:
        if name_values.count(n) > 1:
            dup_names.append(n)
    dup_names_types = []
    for d in dup_names:
        types = []
        for t in temp_names:
            if t['value'] == d:
                types.append(t['types'])
        name_obj = {
            "types": types,
            "value": d
        }
        dup_names_types.append(name_obj)
    temp_names = [t for t in temp_names if t['value'] not in dup_names]
    temp_names.append(name_obj)
    print("temp names 2:")
    print(temp_names)
    v2_data['names'] = temp_names
    if csv_data['status']:
        v2_data['status'] = csv_data['status'].strip()

    if csv_data['types']:
        v2_data['types'] = [t.strip() for t in csv_data['types'].split(';')]
    errors, new_record = new_record_from_json(v2_data, version)
    return errors, new_record

def process_csv(csv_file, version):
    print("Processing CSV")
    errors = None
    row_errors = {}
    skipped_count = 0
    updated_count = 0
    new_count = 0
    read_file = csv_file.read().decode('utf-8')
    print(read_file)
    reader = csv.DictReader(io.StringIO(read_file))
    row_num = 1
    for row in reader:
        print("Row data")
        print(row)
        errors, v2_record = new_record_from_csv(row, version)
        print(errors)
        print(v2_record)
    '''
        if row['ror_id']:
            row_error, updated_record = update_from_csv(row)
            if row_error:
                row_errors[row_num] = ror_error
                skipped_count += 1
            else:
                updated_count += 1
        else:
            row_error, new_record = new_record_from_csv(row)
            if row_error:
                row_errors[row_num] = ror_error
                skipped_count += 1
            else:
                new_count +=1
        row_num += 1
    if len(ror_errors):
        #create row errors csv
    if updated_count > 0 or updated_count > 0 or skipped_count > 0:
        # created zip
    '''