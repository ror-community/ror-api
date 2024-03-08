import csv
import io
import re

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

LANG_DELIMITER = "*"

UPDATE_DELIMITER = "=="


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

    else:
        actions_values[UPDATE_ACTIONS["REPLACE"]] = [v.strip() for v in csv_field.split(';') if v]
    print(actions_values)
    return actions_values

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