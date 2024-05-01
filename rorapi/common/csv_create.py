import copy
from rorapi.common.record_utils import *
from rorapi.common.csv_utils import *
from rorapi.v2.record_constants import *
from rorapi.common.serializers import ErrorsSerializer
from rorapi.common.create_update import new_record_from_json


def new_record_from_csv(csv_data, version):
    v2_data = copy.deepcopy(V2_TEMPLATE)
    errors = []
    #domains
    if csv_data['domains']:
        v2_data['domains'] = [d.strip() for d in csv_data['domains'].strip(';').split(';')]

    #established
    if csv_data['established']:
        v2_data['established'] = int(csv_data['established'].strip())

    #external ids
    for k,v in V2_EXTERNAL_ID_TYPES.items():
        if csv_data['external_ids.type.' + v + '.all']:
            all_ids = [i.strip() for i in csv_data['external_ids.type.' + v + '.all'].strip(';').split(';')]
            ext_id_obj = {
                "type": v,
                "all": all_ids,
                "preferred": csv_data['external_ids.type.' + v + '.preferred'].strip() if csv_data['external_ids.type.' + v + '.preferred'] else all_ids[0]
            }
            v2_data['external_ids'].append(ext_id_obj)

    #links
    for k,v in V2_LINK_TYPES.items():
        if csv_data['links.type.' + v]:
            for l in csv_data['links.type.' + v].strip(';').split(';'):
                link_obj = {
                    "type": v,
                    "value": l.strip()
                }
                v2_data['links'].append(link_obj)

    #locations
    if csv_data['locations.geonames_id']:
        geonames_ids = [i.strip() for i in csv_data['locations.geonames_id'].strip(';').split(';')]
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
            for n in csv_data['names.types.' + v].strip(';').split(';'):
                if LANG_DELIMITER in n:
                    if n.count(LANG_DELIMITER) == 1:
                        name_val, lang  = n.split("*")
                        if lang:
                            lang_errors, lang_code = get_lang_code(lang.strip())
                            if lang_errors:
                                errors.append("Could not convert language value to ISO code: {}".format(lang))
                    else:
                        name_val = None
                        lang_code = None
                        errors.append("Could not parse name value {} in names.types.{} because it contains multiple {} lang delimiter chars.".format(n, v, LANG_DELIMITER))
                else:
                    name_val = n
                    lang_code = None
                if name_val:
                    name_obj = {
                        "types": [v],
                        "value": name_val.strip(),
                        "lang": lang_code
                    }
                    temp_names.append(name_obj)
    print("temp names 1:")
    print(temp_names)
    name_vals = [n['value'] for n in temp_names]
    dup_names = []
    for n in name_vals:
        if name_vals.count(n) > 1:
            if n not in dup_names:
                dup_names.append(n)
    for d in dup_names:
        dup_names_objs = [t for t in temp_names if t['value'] == d]
        lang_codes = [dno['lang'] for dno in dup_names_objs]
        for lang_code in lang_codes:
            if lang_codes.count(lang_code) > 1:
                name_lang_dups = [dno for dno in dup_names_objs if dno['lang'] == lang_code]
                types = []
                for n in name_lang_dups:
                    types.extend(n['types'])
                name_obj = {
                    "types": types,
                    "value": d,
                    "lang": lang_code
                }
                if name_obj not in temp_names:
                    temp_names = [t for t in temp_names if t not in name_lang_dups]
                    temp_names.append(name_obj)
    print("temp names 2:")
    print(temp_names)
    v2_data['names'] = temp_names

    #status
    if csv_data['status']:
        v2_data['status'] = csv_data['status'].strip().lower()

    #types
    if csv_data['types']:
        v2_data['types'] = [t.strip().lower() for t in csv_data['types'].strip(';').split(';')]

    validation_error, new_record = new_record_from_json(v2_data, version)
    if validation_error:
        errors.append(validation_error)
    return errors, new_record