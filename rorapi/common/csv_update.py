import copy
from rorapi.common.record_utils import *
from rorapi.v2.record_constants import *
from rorapi.common.csv_utils import *
from rorapi.v2.serializers import (
    OrganizationSerializer as OrganizationSerializerV2
)
from rorapi.common.queries import retrieve_organization
from rorapi.common.serializers import ErrorsSerializer
from rorapi.common.create_update import update_record_from_json

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
                                errors.append("Attempting to delete domain(s) that don't exist: {}".format(d))

                        temp_domains = [d for d in temp_domains if d not in delete_values]
                    print("temp domains delete")
                    print(temp_domains)
                if UPDATE_ACTIONS['ADD'] in actions_values:
                    add_values = actions_values[UPDATE_ACTIONS['ADD']]
                    for a in add_values:
                        if a in temp_domains:
                            errors.append("Attempting to add domain(s) that already exist: {}".format(a))
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
                        if temp_preferred is not None and temp_preferred not in temp_all:
                            errors.append("Changes to external ID object with type {} result in preferred value '{}' not in all values '{}'".format(t, temp_preferred, ", ".join(temp_all)))
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
                temp_links = copy.deepcopy(existing_record['links'])
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
                            temp_links = [l for l in temp_links if l['type'] != t]
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
                                        if val.count(LANG_DELIMITER) == 1:
                                            name_val, lang  = val.split("*")
                                            vals_obj["value"] = name_val.strip()
                                            if lang:
                                                lang_errors, lang_code = get_lang_code(lang.strip())
                                                if lang_errors:
                                                    errors.append("Could not convert language value to ISO code: {}".format(lang))
                                                else:
                                                    vals_obj["lang"] = lang_code
                                        else:
                                            errors.append("Could not parse name value {} in names.types.{} because it contains multiple {} lang delimiter chars.".format(val, t, LANG_DELIMITER))
                                    else:
                                        vals_obj["value"] = val.strip()
                                    if vals_obj["value"]:
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
                                temp_names_null_lang_match = [tn for tn in temp_names if (tn['value'] == a['value'] and (tn['lang'] is None and a['lang'] is not None))]
                                # check if value, lang and type already exist
                                if temp_names_match or temp_names_null_lang_match:
                                    if temp_names_match:
                                        errors.append("Attempting to add name that already exists: {}".format(a))
                                    if temp_names_null_lang_match:
                                        errors.append("Attempting to add name with lang code that already exists with no lang code: {}".format(a))
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
                    update_data['status'] = actions_values[UPDATE_ACTIONS['REPLACE']][0].lower()

            #types
            if csv_data['types']:
                actions_values = get_actions_values(csv_data['types'])
                temp_types = copy.deepcopy(existing_record['types'])
                print("initial temp types:")
                print(temp_types)
                if UPDATE_ACTIONS['DELETE'] in actions_values:
                    delete_values = [av.lower() for av in actions_values[UPDATE_ACTIONS['DELETE']]]
                    for d in delete_values:
                        if d not in temp_types:
                            errors.append("Attempting to delete type(s) that don't exist: {}".format(d))
                    if len(temp_types) == len(delete_values):
                        errors.append("Cannot remove all values from required field 'types'")
                    temp_types = [t for t in temp_types if t not in delete_values]
                if UPDATE_ACTIONS['ADD'] in actions_values:
                    add_values = [av.lower() for av in actions_values[UPDATE_ACTIONS['ADD']]]
                    for a in add_values:
                        if a in temp_types:
                            errors.append("Attempting to add type(s) that already exist: {}".format(a))
                    temp_types.extend(add_values)
                if UPDATE_ACTIONS['REPLACE'] in actions_values:
                    temp_types = [av.lower() for av in actions_values[UPDATE_ACTIONS['REPLACE']]]
                print("final temp types:")
                print(temp_types)
                update_data['types'] = temp_types

            if not errors:
                validation_error, updated_record = update_record_from_json(update_data, existing_record)
                if validation_error:
                    errors.append(validation_error)
    return errors, updated_record