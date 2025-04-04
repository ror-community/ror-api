import copy
from datetime import datetime
from rorapi.common.record_utils import *
import update_address as ua
from rorapi.v2.record_constants import *
from rorapi.v2.serializers import (
    OrganizationSerializer as OrganizationSerializerV2
)
from rorapi.management.commands.generaterorid import check_ror_id

V2_SCHEMA = get_file_from_url("https://raw.githubusercontent.com/ror-community/ror-schema/refs/heads/master/ror_schema_v2_1.json")


def update_record(json_input, existing_record):
    record = copy.deepcopy(existing_record)
    for k, v in json_input.items():
        record[k] = copy.deepcopy(v)
    return update_last_mod(record)

def update_last_mod(record):
    record['admin']['last_modified'] = copy.deepcopy(V2_LAST_MOD)
    record['admin']['last_modified']['date'] = datetime.now().strftime("%Y-%m-%d")
    return record

def check_optional_fields(record):
    for k in V2_OPTIONAL_FIELD_DEFAULTS:
        if k not in record:
            return True
    return False

def add_missing_optional_fields(record):
    for k, v in V2_OPTIONAL_FIELD_DEFAULTS.items():
        if k not in record:
            record[k] = v
    return record

def add_created_last_mod(record):
    today = datetime.now().strftime("%Y-%m-%d")
    record['admin'] = copy.deepcopy(V2_ADMIN)
    record['admin']['created']['date'] = today
    record['admin']['last_modified']['date'] = today
    return record

def update_locations(locations):
    error = None
    updated_locations = []
    for location in locations:
        if 'geonames_id' in location:
            try:
                print(location['geonames_id'])
                updated_location = ua.new_geonames_v2(str(location['geonames_id']))
                updated_locations.append(updated_location['location'])
            except:
                error = "Error retrieving Geonames data for ID {}. Please check that this is a valid Geonames ID".format(location['geonames_id'])
    return error, updated_locations

def sort_list_fields(v2_record):
    for field in v2_record:
        if field in V2_SORT_KEYS:
            if V2_SORT_KEYS[field] is not None:
                sort_key = V2_SORT_KEYS[field]
                sorted_vals = sorted(v2_record[field], key=lambda x: x[sort_key])
            else:
                sorted_vals = sorted(v2_record[field])
            v2_record[field] = sorted_vals
    return v2_record


def new_record_from_json(json_input, version):
    error = None
    valid_data = None
    new_record = copy.deepcopy(json_input)
    if check_optional_fields(new_record):
        new_record = add_missing_optional_fields(new_record)
    error, updated_locations = update_locations(new_record['locations'])
    if not error:
        new_record['locations'] = updated_locations
        new_record = add_created_last_mod(new_record)
        new_ror_id = check_ror_id(version)
        print("new ror id: " + new_ror_id)
        new_record['id'] = new_ror_id
        error, valid_data = validate_record(sort_list_fields(new_record), V2_SCHEMA)
    return error, valid_data


def update_record_from_json(new_json, existing_org):
    error = None
    valid_data = None
    serializer = OrganizationSerializerV2(existing_org)
    existing_record = serializer.data
    updated_record = update_record(new_json, existing_record)
    error, updated_locations = update_locations(updated_record['locations'])
    if not error:
        updated_record['locations'] = updated_locations
        error, valid_data = validate_record(sort_list_fields(updated_record), V2_SCHEMA)
    return error, valid_data
