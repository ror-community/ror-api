import jsonschema
import requests
import copy
import csv
import json
import io
import os
import re
from datetime import datetime
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
    if len(location_errors) > 0:
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
                result = re.search(r"{0}(.*?)(?=$|(add|delete|replace)==)".format(ua + UPDATE_DELIMITER), csv_field)
                print(result[0])
                #add==foo;bar;delete==fizz;buzz;
                #^(add|delete|replace)==(.*?)($|(?=add|delete|replace==))
                temp_val = result[0].replace(ua + UPDATE_DELIMITER, '')
                print("temp val:")
                print(temp_val)
                actions_values[ua] = temp_val
                csv_field.replace(result[0], '')
    else:
        actions_values[UPDATE_ACTIONS["REPLACE"]] = csv_field
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
            if len(update_actions) > 2:
                errors.append("{} update actions '{}' found in '{}' field but only 2 are allowed".format(str(len(update_actions)), ", ".join(update_actions), k))
            if len(update_actions) == 2:
                if not (UPDATE_ACTIONS['ADD'] and UPDATE_ACTIONS['delete']) in update_actions:
                    errors.append("Invalid combination of update actions '{}' found in '{}' field.".format(", ".join(update_actions), k))
            disallowed_actions = [ua for ua in update_actions if ua not in CSV_REQUIRED_FIELDS_ACTIONS[k]]
            print("allowed actions:")
            print(CSV_REQUIRED_FIELDS_ACTIONS[k])
            print("disallowed actions:")
            print(disallowed_actions)
            if len(disallowed_actions) > 0:
                errors.append("Invalid update action(s) '{}' found in {} field. Allowed actions for this field are '{}'".format(", ".join(disallowed_actions), k, ", ".join(CSV_REQUIRED_FIELDS_ACTIONS[k])))
        if v.strip() == UPDATE_ACTIONS['DELETE'].lower() and k in NO_DELETE_FIELDS:
             errors.append("Invalid update action '{}' in {} field. Cannot remove all values from a required field.".format(UPDATE_ACTIONS['DELETE'], k))
    return errors

def update_record_from_csv(csv_data, version):
    errors = None
    updated_record = None
    print("updating record from csvs")
    errors, existing_record = retrieve_organization(csv_data['id'], version)
    print(existing_record)
    if existing_record is None:
        errors = Errors(["No existing record found for ROR ID '{}'".format(csv_data['id'])])
    else:
        row_validation_errors = validate_csv_row_update_syntax(csv_data)
        if len(row_validation_errors) > 0:
            errors = row_validation_errors
            print("row validation errors:")
            print(errors)

        else:
            update_data = {}
            '''
            #domains
            if csv_data['domains']:
                actions_values = get_actions_values(csv_data['domains'])
                temp_domains = copy.deepcopy(existing_record['domains'])
                if UPDATE_ACTIONS['DELETE'] in actions_values:
                    delete_values = actions_values[UPDATE_ACTIONS['DELETE']]
                    if delete_values is None:
                        temp_domains = []
                    else:
                        #should we check if values to delete exist?
                        temp_domains = [d for d in temp_domains if d not in delete_values.split(';')]
                if UPDATE_ACTIONS['ADD'] in actions_values:
                    add_values = actions_values[UPDATE_ACTIONS['ADD']]
                    temp_domains = temp_domains.append([a.strip() for a in add_values.split(';')])
                if UPDATE_ACTIONS['REPLACE'] in actions_values:
                    replace_values = actions_values[UPDATE_ACTIONS['REPLACE']]
                    temp_domains = [r.strip() for r in replace_values.split(';')]
                update_data['domains'] = temp_domains

            #established
            if csv_data['established']:
                actions_values = get_actions_values(csv_data['established'])
                if UPDATE_ACTIONS['DELETE'] in actions_values:
                    update_data['established'] = None
                if UPDATE_ACTIONS['REPLACE'] in actions_values:
                    update_data['established'] = int(actions_values[UPDATE_ACTIONS['REPLACE']].strip())

            #external ids
            updated_ext_id_types = []
            for k,v in V2_EXTERNAL_ID_TYPES.items():
                if csv_data['external_ids.type.' + v + '.all'] or csv_data['external_ids.type.' + v + '.preferred']:
                    updated_ext_id_types.append(v)
            if len(updated_ext_id_types) > 0:
                existing_ext_ids = copy.deepcopy(existing_record['external_ids'])
                for t in updated_ext_id_types:
                    new_ext_id_obj = {}
                    if csv_data['external_ids.type.' + t + '.all']:
                        action, csv_field_value = get_action_value(csv_data['external_ids.type.' + t + '.all'])
                        existing_ext_id_obj = [i for i in existing_ext_ids if i['type'] == t]
                        # all
                        if action == "add":
                            new_ext_id_obj = {
                                "type": t,
                                "all": existing_ext_id_obj[0]['all'].append([c.strip() for c in csv_field_value.split(';')]),
                                "preferred": existing_ext_id_obj[0]['preferred']
                            }
                        elif action == "delete":
                            new_ext_id_obj = {
                                "type": t,
                                "all": [e for e in existing_ext_id_obj[0]['all'] if e not in csv_field_value.split(';')],
                                "preferred": existing_ext_id_obj[0]['preferred']
                            }
                        elif action == "replace":
                            new_ext_id_obj = {
                                "type": t,
                                "all": [c.strip() for c in csv_field_value.split(';')],
                                "preferred": existing_ext_id_obj[0]['preferred']
                            }
                    # preferred
                    if csv_data['external_ids.type.' + t + '.preferred']:
                        if action == "add":
                            new_ext_id_obj = {
                                "type": t,
                                "all": existing_ext_id_obj[0]['all'].append([c.strip() for c in csv_field_value.split(';')]),
                                "preferred": existing_ext_id_obj[0]['preferred']
                            }
                        elif action == "delete":
                            new_ext_id_obj = {
                                "type": t,
                                "all": [e for e in existing_ext_id_obj[0]['all'] if e not in csv_field_value.split(';')],
                                "preferred": existing_ext_id_obj[0]['preferred']
                            }
                        elif action == "replace":
                            new_ext_id_obj = {
                                "type": t,
                                "all": [c.strip() for c in csv_field_value.split(';')],
                                "preferred": existing_ext_id_obj[0]['preferred']
                            }




                        all_ids = [i.strip() for i in csv_data['external_ids.type.' + v + '.all'].split(';')]
                        ext_id_obj = {
                            "type": v,
                            "all": [i.strip() for i in csv_data['external_ids.type.' + v + '.all'].split(';')],
                            "preferred": csv_data['external_ids.type.' + v + '.preferred'].strip() if csv_data['external_ids.type.' + v + '.preferred'] else all_ids[0]
                        }
                        v2_data['external_ids'].append(ext_id_obj)

            #links
            updated_link_types = []
            for k,v in V2_LINK_TYPES.items():
                if csv_data['links.type.' + v]:
                    updated_link_types.append(v)
            if len(updated_link_types) > 0:
                temp_links = copy.deepcopy(existing_record['links'])
                for t in updated_link_types
                    if csv_data['links.type.' + t]:
                        action, csv_field_value = get_action_value(csv_data['links.type.' + t])
                        if action == "add":
                            new_links = [c.strip() for c in csv_field_value.split(';')]
                            for link in new_links:
                                link_obj = {
                                    "type": t,
                                    "value": link
                                }
                                temp_links.append(link_obj)
                        elif action == "delete":
                            # remove all links of current type
                            if csv_field_value is None:
                                temp_links = [tl for tl in temp_links if tl['type'] != t]
                            else:
                                deleted_links = [c.strip() for c in csv_field_value.split(';')]
                                temp_links = [tl for tl in temp_links if tl['value'] not in deleted_links]
                        elif action == "replace":
                            temp_links = []
                            new_links = [c.strip() for c in csv_field_value.split(';')]
                            for link in new_links:
                                link_obj = {
                                    "type": t,
                                    "value": csv_data['links.type.' + t].strip()
                                }
                            temp_links.append(link_obj)
                        update_data['links'] = temp_links

            #locations
            if csv_data['locations.geonames_id']:
                temp_locations = copy.deepcopy(existing_record['locations'])
                action, csv_field_value = get_action_value(csv_data['locations.geonames_id'])
                if action == "add":
                    new_locations = [c.strip() for c in csv_field_value.split(';')]
                    for nl in new_locations:
                        location_obj = {
                            "geonames_id": nl,
                            "geonames_details": {}
                        }
                        temp_locations.append(location_obj)
                elif action == "delete":
                    deleted_locations = [c.strip() for c in csv_field_value.split(';')]
                    temp_locations = [tl for tl in temp_locations if tl['geonames_id'] not in deleted_locations]
                elif action == "replace":
                    temp_locations = []
                    new_locations = [c.strip() for c in csv_field_value.split(';')]
                    for nl in new_locations:
                        location_obj = {
                            "geonames_id": nl,
                            "geonames_details": {}
                        }
                        temp_locations.append(location_obj)

                update_data['locations'] = temp_locations

            #names

            #status
            if csv_data['status']:
                action, csv_field_value = get_action_value(csv_data['established'])
                update_data['status'] = csv_field_value.strip()

            #types
            if csv_data['types']:
                action, csv_field_value = get_action_value(csv_data['types'])
                if action == "add":
                    update_data['types'] = existing_record['types'].append([c.strip() for c in csv_field_value.split(';')])
                elif action == "delete":
                    update_data['types'] = [t for t in existing_record['types'] if t not in csv_field_value.split(';')]
                elif action == "replace":
                    update_data['types'] = [c.strip() for c in csv_field_value.split(';')]

            '''
            errors, updated_record = update_record_from_json(update_data, existing_record)

    return errors, updated_record

    #return None, None

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
            link_obj = {
                "type": v,
                "value": csv_data['links.type.' + v].strip()
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
            name_lang = csv_data['names.types.' + v].split(LANG_DELIMITER)
            name_obj = {
                "types": v,
                "value": name_lang[0].strip(),
                "lang": name_lang[1].strip() if name_lang[1] else None
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
        if row['id']:
            errors, v2_record = update_record_from_csv(row, version)
        else:
            errors, v2_record = new_record_from_csv(row, version)
        if errors is None:
            serializer = OrganizationSerializerV2(v2_record)
            json_obj = json.loads(JSONRenderer().render(serializer.data))
            print(json_obj)
        else:
            print(errors)

        '''
        ror_id = v2_record['id']
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