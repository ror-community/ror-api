import jsonschema
import requests
import copy
import csv
import json
import io
import os
import re
from datetime import datetime
from iso639 import Lang
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rorapi.common.models import Errors
import update_address as ua
from rorapi.settings import DATA
from rorapi.v2.serializers import (
    OrganizationSerializer as OrganizationSerializerV2
)
from rorapi.common.queries import get_ror_id, retrieve_organization
from rorapi.common.serializers import ErrorsSerializer

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

UPDATE_ACTIONS = {
    "ADD": "add",
    "DELETE": "delete",
    "REPLACE": "replace"
}

UPDATE_ACTIONS_MULTI = [UPDATE_ACTIONS["ADD"], UPDATE_ACTIONS["DELETE"], UPDATE_ACTIONS["REPLACE"]]

UPDATE_ACTIONS_SINGLE = [UPDATE_ACTIONS["DELETE"], UPDATE_ACTIONS["REPLACE"]]

NO_DELETE_FIELDS = ["id", "locations.geonames_id", "names.types.ror_display", "status", "types"]

CSV_REQUIRED_FIELDS_ACTIONS = {
    "id": None,
    "domains": UPDATE_ACTIONS_MULTI,
    "established": UPDATE_ACTIONS_SINGLE,
    "external_ids.type.fundref.all": UPDATE_ACTIONS_MULTI,
    "external_ids.type.fundref.preferred": UPDATE_ACTIONS_SINGLE,
    "external_ids.type.grid.all": UPDATE_ACTIONS_MULTI,
    "external_ids.type.grid.preferred": UPDATE_ACTIONS_SINGLE,
    "external_ids.type.isni.all": UPDATE_ACTIONS_MULTI,
    "external_ids.type.isni.preferred": UPDATE_ACTIONS_SINGLE,
    "external_ids.type.wikidata.all": UPDATE_ACTIONS_MULTI,
    "external_ids.type.wikidata.preferred": UPDATE_ACTIONS_SINGLE,
    "links.type.website": UPDATE_ACTIONS_MULTI,
    "links.type.wikipedia": UPDATE_ACTIONS_MULTI,
    "locations.geonames_id": UPDATE_ACTIONS_MULTI,
    "names.types.acronym": UPDATE_ACTIONS_MULTI,
    "names.types.alias": UPDATE_ACTIONS_MULTI,
    "names.types.label": UPDATE_ACTIONS_MULTI,
    "names.types.ror_display": [UPDATE_ACTIONS["REPLACE"]],
    "status": [UPDATE_ACTIONS["REPLACE"]],
    "types": UPDATE_ACTIONS_MULTI
}

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

LANG_DELIMITER = "*"

UPDATE_DELIMITER = "=="

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
            for field in CSV_REQUIRED_FIELDS_ACTIONS.keys():
                if field not in csv_fields:
                    missing_fields.append(field)
            print(missing_fields)
            if missing_fields:
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
    if location_errors:
        errors = Errors(location_errors)
    else:
        new_record['locations'] = updated_locations
        new_record = add_created_last_mod(new_record)
        new_ror_id = check_ror_id(version)
        print("new ror id: " + new_ror_id)
        new_record['id'] = new_ror_id
        errors, valid_data = validate_v2(new_record)
    return errors, valid_data


def update_record_from_json(new_json, existing_org):
    errors = None
    valid_data = None
    serializer = OrganizationSerializerV2(existing_org)
    existing_record = serializer.data
    updated_record = update_record(new_json, existing_record)
    location_errors, updated_locations = update_locations(updated_record['locations'])
    if location_errors:
        errors = Errors(location_errors)
    else:
        updated_record['locations'] = updated_locations
        errors, valid_data = validate_v2(updated_record)
    return errors, valid_data


def get_action_value(csv_field):
    action = None
    value = None
    if csv_field.lower() == "delete":
        action = "delete"
        value = None
    elif UPDATE_DELIMITER in csv_field:
        action = csv_field.split(UPDATE_DELIMITER)[0]
        value = csv_field.split(UPDATE_DELIMITER)[1]
    else:
        action = "replace"
        value = csv_field
    return action, value

def get_actions_values(csv_field):
    print("getting actions values:")
    actions_values = {}
    if csv_field.lower() == UPDATE_ACTIONS["DELETE"]:
        actions_values[UPDATE_ACTIONS["DELETE"]] = None
    elif UPDATE_DELIMITER in csv_field:
        for ua in list(UPDATE_ACTIONS.values()):
            print(ua)
            if ua + UPDATE_DELIMITER in csv_field:
                print("doing regex:")
                regex = r"(" + re.escape(
      ua + UPDATE_DELIMITER) + r")(.*?)(?=$|(add|delete|replace)==)"
                result = re.search(regex, csv_field)
                print(result[0])
                temp_val = result[0].replace(ua + UPDATE_DELIMITER, '')
                print("temp val:")
                print(temp_val)
                actions_values[ua] = [v.strip() for v in temp_val.split(';') if v]
                #csv_field.replace(result[0], '')

    else:
        actions_values[UPDATE_ACTIONS["REPLACE"]] = [v.strip() for v in csv_field.split(';') if v]
    print(actions_values)
    return actions_values

def validate_csv_row_update_syntax(csv_data):
    print("validating row")
    errors = []
    for k, v in csv_data.items():
        if UPDATE_DELIMITER in v:
            print("field:")
            print(k)
            print("value:")
            print(v)
            actions_values = get_actions_values(v)
            print("actions values:")
            print(actions_values)
            update_actions = list(actions_values.keys())
            if not update_actions:
                errors.append("Update delimiter '{}' found in '{}' field but no valid update action found in value {}".format(UPDATE_DELIMITER, k, v))
            if len(update_actions) > 2:
                errors.append("{} update actions '{}' found in '{}' field but only 2 are allowed".format(str(len(update_actions)), ", ".join(update_actions), k))
            if len(update_actions) == 2:
                if not (UPDATE_ACTIONS['ADD'] and UPDATE_ACTIONS['DELETE']) in update_actions:
                    errors.append("Invalid combination of update actions '{}' found in '{}' field.".format(", ".join(update_actions), k))
            disallowed_actions = [ua for ua in update_actions if ua not in CSV_REQUIRED_FIELDS_ACTIONS[k]]
            print("allowed actions:")
            print(CSV_REQUIRED_FIELDS_ACTIONS[k])
            print("disallowed actions:")
            print(disallowed_actions)
            if disallowed_actions:
                errors.append("Invalid update action(s) '{}' found in {} field. Allowed actions for this field are '{}'".format(", ".join(disallowed_actions), k, ", ".join(CSV_REQUIRED_FIELDS_ACTIONS[k])))
        if v.strip() == UPDATE_ACTIONS['DELETE'].lower() and k in NO_DELETE_FIELDS:
             errors.append("Invalid update action '{}' in {} field. Cannot remove all values from a required field.".format(UPDATE_ACTIONS['DELETE'], k))
    return errors

def update_record_from_csv(csv_data, version):
    errors = []
    updated_record = None
    print("updating record from csv")
    existing_org_errors, existing_org = retrieve_organization(csv_data['id'], version)
    print(existing_org)
    if existing_org is None:
        errors.append("No existing record found for ROR ID '{}'".format(csv_data['id']))
    else:
        row_validation_errors = validate_csv_row_update_syntax(csv_data)
        if row_validation_errors:
            errors.extend(row_validation_errors)
            print("row validation errors:")
            print(errors)
        else:
            serializer = OrganizationSerializerV2(existing_org)
            existing_record = serializer.data
            print(existing_record)
            update_data = {}

            #domains
            if csv_data['domains']:
                actions_values = get_actions_values(csv_data['domains'])
                temp_domains = copy.deepcopy(existing_record['domains'])
                print("initial temp domains:")
                print(temp_domains)
                if UPDATE_ACTIONS['DELETE'] in actions_values:
                    delete_values = actions_values[UPDATE_ACTIONS['DELETE']]
                    if delete_values is None:
                        temp_domains = []
                    else:
                        for d in delete_values:
                            if d not in temp_domains:
                                errors.append("Attempting to delete dommain(s) that don't exist: {}".format(d))
                        temp_domains = [d for d in temp_domains if d not in delete_values]
                    print("temp domains delete")
                    print(temp_domains)
                if UPDATE_ACTIONS['ADD'] in actions_values:
                    add_values = actions_values[UPDATE_ACTIONS['ADD']]
                    for a in add_values:
                        if a in temp_domains:
                            errors.append("Attempting to add dommain(s) that already exist: {}".format(a))
                    print(add_values)
                    temp_domains.extend(add_values)
                    print("temp domains add")
                    print(temp_domains)
                if UPDATE_ACTIONS['REPLACE'] in actions_values:
                    temp_domains = actions_values[UPDATE_ACTIONS['REPLACE']]
                    print("temp domains replace")
                    print(temp_domains)
                print("final temp domains:")
                print(temp_domains)
                update_data['domains'] = temp_domains

            #established
            if csv_data['established']:
                actions_values = get_actions_values(csv_data['established'])
                if UPDATE_ACTIONS['DELETE'] in actions_values:
                    update_data['established'] = None
                if UPDATE_ACTIONS['REPLACE'] in actions_values:
                    update_data['established'] = int(actions_values[UPDATE_ACTIONS['REPLACE']][0])

            #external ids
            updated_ext_id_types = []
            for k,v in V2_EXTERNAL_ID_TYPES.items():
                if csv_data['external_ids.type.' + v + '.all'] or csv_data['external_ids.type.' + v + '.preferred']:
                    updated_ext_id_types.append(v)
            if updated_ext_id_types:
                temp_ext_ids = copy.deepcopy(existing_record['external_ids'])
                for t in updated_ext_id_types:
                    temp_all = []
                    temp_preferred = None
                    existing_ext_id_obj = None
                    existing_ext_ids_type = [i for i in temp_ext_ids if i['type'] == t]
                    if len(existing_ext_ids_type) == 1:
                        existing_ext_id_obj = existing_ext_ids_type[0]
                        temp_all = existing_ext_id_obj['all']
                        temp_preferred = existing_ext_id_obj['preferred']
                    if len(existing_ext_ids_type) > 1:
                        errors.append("Something is wrong. Multiple external ID objects with type ".format(t))
                    # external_ids.all
                    if csv_data['external_ids.type.' + t + '.all']:
                        actions_values = get_actions_values(csv_data['external_ids.type.' + t + '.all'])
                        if UPDATE_ACTIONS['DELETE'] in actions_values:
                            delete_values = actions_values[UPDATE_ACTIONS['DELETE']]
                            if delete_values is None:
                                temp_all = []
                            else:
                                for d in delete_values:
                                    if d not in temp_all:
                                        errors.append("Attempting to delete external ID(s) from {}.all that don't exist: {}".format(t, d))
                                temp_all = [i for i in temp_all if i not in delete_values]
                        if UPDATE_ACTIONS['ADD'] in actions_values:
                            add_values = [a for a in actions_values[UPDATE_ACTIONS['ADD']]]
                            for a in add_values:
                                if a in temp_all:
                                    errors.append("Attempting to add external ID(s) to {}.all that already exist: {}".format(t, a))
                            temp_all.extend(add_values)
                        if UPDATE_ACTIONS['REPLACE'] in actions_values:
                            temp_all = actions_values[UPDATE_ACTIONS['REPLACE']]

                    # external_ids.preferred
                    if csv_data['external_ids.type.' + t + '.preferred']:
                        actions_values = get_actions_values(csv_data['external_ids.type.' + t + '.preferred'])
                        if UPDATE_ACTIONS['DELETE'] in actions_values:
                            temp_preferred = None
                        if UPDATE_ACTIONS['REPLACE'] in actions_values:
                            temp_preferred = actions_values[UPDATE_ACTIONS['REPLACE']][0]


                    if (not temp_all) and temp_preferred is None:
                        # remove all of type
                        if not existing_ext_id_obj:
                            errors.append("Attempting to delete external ID object with type {} that doesn't exist.".format(t))
                        temp_ext_ids = [i for i in temp_ext_ids if i['type'] != t]

                    else:
                        # remove all of type and replace with new obj
                        new_ext_id_obj = {
                                    "type": t,
                                    "all": temp_all,
                                    "preferred": temp_preferred
                                }
                        if existing_ext_id_obj:
                            temp_ext_ids = [i for i in temp_ext_ids if i['type'] != t]
                        temp_ext_ids.append(new_ext_id_obj)

                update_data['external_ids'] = temp_ext_ids

            #links
            updated_link_types = []
            for k,v in V2_LINK_TYPES.items():
                if csv_data['links.type.' + v]:
                    updated_link_types.append(v)
            if updated_link_types:
                temp_names = copy.deepcopy(existing_record['links'])
                for t in updated_link_types:
                    if csv_data['links.type.' + t]:
                        actions_values = get_actions_values(csv_data['links.type.' + t])
                        existing_links = [tl['value'] for tl in temp_links]
                        if UPDATE_ACTIONS['DELETE'] in actions_values:
                            delete_values = actions_values[UPDATE_ACTIONS['DELETE']]
                            if delete_values is None:
                                temp_links = [tl for tl in temp_links if tl['type'] != t]
                            else:
                                for d in delete_values:
                                    if d not in existing_links:
                                        errors.append("Attempting to delete link(s) that don't exist: {}".format(d))
                                temp_links = [tl for tl in temp_links if tl['value'] not in delete_values]
                        if UPDATE_ACTIONS['ADD'] in actions_values:
                            add_values = [a for a in actions_values[UPDATE_ACTIONS['ADD']]]
                            for a in add_values:
                                if a in existing_links:
                                    errors.append("Attempting to add link(s) that already exist: {}".format(a))
                            for a in add_values:
                                link_obj = {
                                    "type": t,
                                    "value": a
                                }
                                temp_links.append(link_obj)
                        if UPDATE_ACTIONS['REPLACE'] in actions_values:
                            temp_links = []
                            for r in actions_values[UPDATE_ACTIONS['REPLACE']]:
                                link_obj = {
                                    "type": t,
                                    "value": r
                                }
                                temp_links.append(link_obj)
                        print("final temp links:")
                        print(temp_links)
                        update_data['links'] = temp_links

            #locations
            if csv_data['locations.geonames_id']:
                actions_values = get_actions_values(csv_data['locations.geonames_id'])
                temp_locations = copy.deepcopy(existing_record['locations'])
                print("initial temp locations:")
                print(temp_locations)
                existing_geonames_ids = [tl['geonames_id'] for tl in temp_locations]
                print(existing_geonames_ids)
                if UPDATE_ACTIONS['DELETE'] in actions_values:
                    delete_values = [int(d) for d in actions_values[UPDATE_ACTIONS['DELETE']]]
                    for d in delete_values:
                        if d not in existing_geonames_ids:
                            errors.append("Attempting to delete locations(s) that don't exist: {}".format(d))
                    if len(existing_geonames_ids) == len(delete_values):
                        errors.append("Cannot remove all values from required field 'locations'")
                    temp_locations = [tl for tl in temp_locations if tl['geonames_id'] not in delete_values]
                if UPDATE_ACTIONS['ADD'] in actions_values:
                    add_values = [int(a) for a in actions_values[UPDATE_ACTIONS['ADD']]]
                    for a in add_values:
                        if int(a) in existing_geonames_ids:
                            errors.append("Attempting to add locations(s) that already exist: {}".format(a))
                    for a in add_values:
                        location_obj = {
                            "geonames_id": int(a),
                            "geonames_details": {}
                        }
                        temp_locations.append(location_obj)
                if UPDATE_ACTIONS['REPLACE'] in actions_values:
                    temp_locations = []
                    for r in actions_values[UPDATE_ACTIONS['REPLACE']]:
                        location_obj = {
                            "geonames_id": int(r),
                            "geonames_details": {}
                        }
                        temp_locations.append(location_obj)
                print("final temp locations:")
                print(temp_locations)
                update_data['locations'] = temp_locations

            #names
            updated_name_types = []
            for k,v in V2_NAME_TYPES.items():
                if csv_data['names.types.' + v]:
                    updated_name_types.append(v)
            print("updated name types")
            print(updated_name_types)
            if updated_name_types:
                temp_names = copy.deepcopy(existing_record['names'])
                for t in updated_name_types:
                    print("updating name type " + t)
                    if csv_data['names.types.' + t]:
                        actions_values = get_actions_values(csv_data['names.types.' + t])
                        for k, v in actions_values.items():
                            if v:
                                vals_obj_list = []
                                for val in v:
                                    print("val is")
                                    print(val)
                                    vals_obj = {
                                        "value": None,
                                        "lang": None
                                    }
                                    if LANG_DELIMITER in val:
                                        print("has lang delim")
                                        name_val, lang  = val.split("*")
                                        vals_obj["value"] = name_val.strip()
                                        if lang:
                                            lang_errors, lang_code = get_lang_code(lang.strip())
                                            if lang_errors:
                                                errors.append("Could not convert language value to ISO code: {}".format(lang))
                                            else:
                                                vals_obj["lang"] = lang_code
                                    else:
                                        vals_obj["value"] = val.strip()
                                    vals_obj_list.append(vals_obj)
                                actions_values[k] = vals_obj_list
                        print("updated actions values")
                        print(actions_values)
                        if UPDATE_ACTIONS['DELETE'] in actions_values:
                            print("delete in actions")
                            delete_values = actions_values[UPDATE_ACTIONS['DELETE']]
                            print(delete_values)
                            if delete_values is None:
                                temp_names = [tn for tn in temp_names if t not in tn['types']]
                            else:
                                for d in delete_values:
                                    temp_names_match = [tn for tn in temp_names if (t in tn['types'] and tn['value'] == d['value'] and tn['lang'] == d['lang'])]
                                    if not temp_names_match:
                                        errors.append("Attempting to delete name(s) that don't exist: {}".format(d))
                                    else:
                                        for tnm in temp_names_match:
                                            temp_names.remove(tnm)
                                            #if name has multiple types, delete type only
                                            if len(tnm['types']) > 1:
                                                temp_types = [tnm_type for tnm_type in tnm['types'] if tnm_type != t]
                                                tnm['types'] = temp_types
                                                temp_names.append(tnm)

                        if UPDATE_ACTIONS['ADD'] in actions_values:
                            add_values = actions_values[UPDATE_ACTIONS['ADD']]
                            for a in add_values:
                                temp_names_match = [tn for tn in temp_names if (t in tn['types'] and tn['value'] == a['value'] and tn['lang'] == a['lang'])]
                                # check if value, lang and type already exist
                                if temp_names_match:
                                    errors.append("Attempting to add names(s) that already exist: {}".format(a))
                                else:
                                    name_vals_match = [tn for tn in temp_names if (tn['value'] == a['value'] and tn['lang'] == a['lang'])]
                                    if name_vals_match:
                                        print("name vals match")
                                        print(name_vals_match)
                                        for nvm in name_vals_match:
                                            # if value and lang exist but not type, add type only
                                            if len(nvm['types']) > 0:
                                                temp_names.remove(nvm)
                                                nvm['types'].append(t)
                                                temp_names.append(nvm)
                                    else:
                                        # if value and lang don't exist add new name obj
                                        name_obj = {
                                            "types": [t],
                                            "value": a['value'],
                                            "lang": a['lang']
                                        }
                                        temp_names.append(name_obj)
                        if UPDATE_ACTIONS['REPLACE'] in actions_values:
                            temp_names_match = [tn for tn in temp_names if t in tn['types']]
                            # remove all names of current type from temp names using same rules as delete
                            if temp_names_match:
                                for tnm in temp_names_match:
                                    temp_names.remove(tnm)
                                    #if name has multiple types, delete type only
                                    if len(tnm['types']) > 1:
                                        temp_types = [tnm_type for tnm_type in tnm['types'] if tnm_type != t]
                                        tnm['types'] = temp_types
                                        temp_names.append(tnm)
                            replace_values = actions_values[UPDATE_ACTIONS['REPLACE']]
                            for r in replace_values:
                                name_vals_match = [tn for tn in temp_names if (tn['value'] == r['value'] and tn['lang'] == r['lang'])]
                                # add new names of current type to temp names using same rules as add
                                if name_vals_match:
                                    for nvm in name_vals_match:
                                        # if value and lang exist but not type, add type only
                                        if len(nvm['types']) > 0:
                                            temp_names.remove(nvm)
                                            nvm['types'].append(t)
                                            temp_names.append(nvm)
                                else:
                                    # if value and lang don't exist add new name obj
                                    name_obj = {
                                        "types": [t],
                                        "value": r['value'],
                                        "lang": r['lang']
                                    }
                                    temp_names.append(name_obj)

                print("final temp names:")
                print(temp_names)
                update_data['names'] = temp_names

            #status
            if csv_data['status']:
                actions_values = get_actions_values(csv_data['status'])
                if UPDATE_ACTIONS['DELETE'] in actions_values:
                    errors.append("Cannot delete required field 'status'")
                if UPDATE_ACTIONS['REPLACE'] in actions_values:
                    update_data['status'] = actions_values[UPDATE_ACTIONS['REPLACE']][0]

            #types
            if csv_data['types']:
                actions_values = get_actions_values(csv_data['types'])
                temp_types = copy.deepcopy(existing_record['types'])
                print("initial temp types:")
                print(temp_types)
                if UPDATE_ACTIONS['DELETE'] in actions_values:
                    delete_values = actions_values[UPDATE_ACTIONS['DELETE']]
                    for d in delete_values:
                        if d not in temp_types:
                            errors.append("Attempting to delete type(s) that don't exist: {}".format(d))
                    if len(temp_types) == len(delete_values):
                        errors.append("Cannot remove all values from required field 'types'")
                    temp_types = [t for t in temp_types if t not in delete_values]
                if UPDATE_ACTIONS['ADD'] in actions_values:
                    add_values = actions_values[UPDATE_ACTIONS['ADD']]
                    for a in add_values:
                        if a in temp_types:
                            errors.append("Attempting to add type(s) that already exist: {}".format(a))
                    temp_types.extend(add_values)
                if UPDATE_ACTIONS['REPLACE'] in actions_values:
                    temp_types = actions_values[UPDATE_ACTIONS['REPLACE']]
                print("final temp types:")
                print(temp_types)
                update_data['types'] = temp_types

            if not errors:
                validation_errors, updated_record = update_record_from_json(update_data, existing_record)
                if validation_errors:
                    errors = ErrorsSerializer(validation_errors).data
    return errors, updated_record


def new_record_from_csv(csv_data, version):
    v2_data = copy.deepcopy(V2_TEMPLATE)

    #domains
    if csv_data['domains']:
        v2_data['domains'] = [d.strip() for d in csv_data['domains'].split(';')]

    #established
    if csv_data['established']:
        v2_data['established'] = int(csv_data['established'].strip())

    #external ids
    for k,v in V2_EXTERNAL_ID_TYPES.items():
        if csv_data['external_ids.type.' + v + '.all']:
            all_ids = [i.strip() for i in csv_data['external_ids.type.' + v + '.all'].split(';')]
            ext_id_obj = {
                "type": v,
                "all": all_ids,
                "preferred": csv_data['external_ids.type.' + v + '.preferred'].strip() if csv_data['external_ids.type.' + v + '.preferred'] else all_ids[0]
            }
            v2_data['external_ids'].append(ext_id_obj)

    #links
    for k,v in V2_LINK_TYPES.items():
        if csv_data['links.type.' + v]:
            for l in csv_data['links.type.' + v].split(';'):
                link_obj = {
                    "type": v,
                    "value": l.strip()
                }
                v2_data['links'].append(link_obj)

    #locations
    if csv_data['locations.geonames_id']:
        geonames_ids = [i.strip() for i in csv_data['locations.geonames_id'].split(';')]
        for geonames_id in geonames_ids:
            location_obj = {
                "geonames_id": geonames_id,
                "geonames_details": {}
            }
            v2_data['locations'].append(location_obj)

    #names
    temp_names = []
    for k,v in V2_NAME_TYPES.items():
        if csv_data['names.types.' + v]:
            for n in csv_data['names.types.' + v].split(';'):
                if LANG_DELIMITER in n:
                    name_val, lang_code  = n.split("*")
                    if lang:
                        lang_errors, lang_code = get_lang_code(lang.strip())
                        if lang_errors:
                            errors.append("Could not convert language value to ISO code: {}".format(lang))
                else:
                    name_val = n
                    lang_code = None

                name_obj = {
                    "types": [v],
                    "value": name_val.strip(),
                    "lang": lang_code
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
                types.extend(t['types'])
        name_obj = {
            "types": types,
            "value": d,
            "lang": None
        }
        dup_names_types.append(name_obj)
    temp_names = [t for t in temp_names if t['value'] not in dup_names]
    temp_names.append(name_obj)
    print("temp names 2:")
    print(temp_names)
    v2_data['names'] = temp_names

    #status
    if csv_data['status']:
        v2_data['status'] = csv_data['status'].strip()

    #types
    if csv_data['types']:
        v2_data['types'] = [t.strip() for t in csv_data['types'].split(';')]

    validation_errors, new_record = new_record_from_json(v2_data, version)
    if validation_errors:
        errors = ErrorsSerializer(validation_errors).data
    return errors, new_record

def process_csv(csv_file, version):
    print("Processing CSV")
    errors = None
    report = []
    report_fields = ['row', 'ror_id', 'action', 'errors']
    skipped_count = 0
    updated_count = 0
    new_count = 0
    read_file = csv_file.read().decode('utf-8')
    print(read_file)
    reader = csv.DictReader(io.StringIO(read_file))
    row_num = 2
    for row in reader:
        ror_id = None
        print("Row data")
        print(row)
        if row['id']:
            action = 'updated'
            ror_id = row['id']
            errors, v2_record = update_record_from_csv(row, version)
        else:
            action = 'updated'
            errors, v2_record = new_record_from_csv(row, version)
        if errors is None:
            ror_id = v2_record['id']
            serializer = OrganizationSerializerV2(v2_record)
            json_obj = json.loads(JSONRenderer().render(serializer.data))
            print(json_obj)
        else:
            action = 'skipped'
            print(errors)

        report.append({"row": row_num, "ror_id": ror_id if ror_id else '', "action": action, "errors": errors})
        row_num += 1
        print(report)

        '''

        full_path = os.path.join(DATA['DIR'], ror_id.split('https://ror.org/')[1] + '.json')
        serializer = OrganizationSerializerV2(v2_record)
        json_obj = json.loads(JSONRenderer().render(serializer.data))
        with open(full_path, "w") as outfile:
            json.dump(json_obj, outfile, ensure_ascii=False, indent=2)
         '''
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