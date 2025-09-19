import json
import re
from functools import wraps
from threading import local
import zipfile
import os
import glob
from os.path import exists
import pathlib
import shutil
from rorapi.settings import ES7, ES_VARS, DATA

from django.core.management.base import BaseCommand
from elasticsearch import TransportError

def get_nested_names_v1(org):
    yield org['name']
    for label in org['labels']:
        yield label['label']
    for alias in org['aliases']:
        yield alias
    for acronym in org['acronyms']:
        yield acronym

def get_nested_names_v2(org):
    for name in org['names']:
        yield name['value']

def get_nested_ids_v1(org):
    yield org['id']
    yield re.sub('https://', '', org['id'])
    yield re.sub('https://ror.org/', '', org['id'])
    for ext_name, ext_id in org['external_ids'].items():
        if ext_name == 'GRID':
            yield ext_id['all']
        else:
            for eid in ext_id['all']:
                yield eid

def get_nested_ids_v2(org):
    yield org['id']
    yield re.sub('https://', '', org['id'])
    yield re.sub('https://ror.org/', '', org['id'])
    for ext_id in org['external_ids']:
        for eid in ext_id['all']:
            yield eid

def get_single_search_names_v2(org):
    for name in org["names"]:
        if "acronym" not in name["types"]:
            yield name["value"]

def get_affiliation_match_doc(org):
    doc = { 
        'id': org['id'],
        'country': org["locations"][0]["geonames_details"]["country_code"],
        'status': org['status'],
        'primary': [n["value"] for n in org["names"] if "ror_display" in n["types"]][0],
        'names': [{"name": n} for n in get_single_search_names_v2(org)],
        'relationships': [{"type": r['type'], "id": r['id']} for r in org['relationships']]
    }
    return doc

def prepare_files(path, local_file):
    data = []
    err = {}
    try:
        if exists(local_file):
            with zipfile.ZipFile(local_file, 'r') as zip_ref:
                zip_ref.extractall(path)
    except Exception as e:
        err[prepare_files.__name__] = f"ERROR: {e}"

    json_files = os.path.join(path, "*.json")
    file_list = glob.glob(json_files)
    for file in file_list:
        try:
            with open(file) as f:
                data.append(json.load(f))
        except Exception as e:
            key = f"In {prepare_files.__name__}_{file}"
            err[key] =  f"ERROR: {e}"
    return data, err


def get_rc_data(dir, contents):
    err = {}
    path = f"{dir}/files.zip"
    branch_objects = [i for i in contents if path == i['Key']]
    local_file = None
    local_path = None
    if branch_objects:
        s3_file = branch_objects[0]['Key']
        local_path = os.path.join(DATA['DIR'], dir)
        os.makedirs(local_path)
        local_file = local_path + "/files.zip"
        try:
            DATA['CLIENT'].download_file(DATA['DATA_STORE'],s3_file, local_file)
        except Exception as e:
            key = f"In {get_rc_data.__name__}_downloading files"
            err[key] = f"ERROR: {e}"
    else:
       err[get_rc_data.__name__] = f"ERROR: {dir} not found in S3 bucket"
    return local_path, local_file, err

def get_data():
    err = {}
    # return contents or None
    contents = None
    try:
        objects = DATA['CLIENT'].list_objects_v2(Bucket = DATA['DATA_STORE'])
        contents = objects['Contents']
    except Exception as e:
        err[get_data.__name__] = f"ERROR: Could not get objects from {DATA['DATA_STORE']}: {e}"
    return contents, err


def process_files(dir, version):
    err = []
    if dir:
        path = os.path.join(DATA['WORKING_DIR'], dir)
        if os.path.isdir(path):
            p = pathlib.Path(path)
            shutil.rmtree(p)
        objects, e = get_data()
        err.append(e)
        if objects and not(e):
            # check if objects exist, otherwise error
            path, file, e = get_rc_data(dir, objects)
            err.append(e)
            if path and file and not(e):
                data, e = prepare_files(path, file)
                if not(e):
                    index_error = index(data, version)
                    err.append(index_error)
                else:
                    err.append(e)
        else:
            err.append({process_files.__name__: f"No objects found in {dir}"})
    else:
        err.append({process_files.__name__: "Need S3 directory argument"})
    err = [i for i in err if i]
    if err:
        msg = {"status": "ERROR", "msg": err}
    else:
        msg = {"status": "OK", "msg": f"{dir} indexed using version {version}"}

    return msg


def index(dataset, version):
    err = {}
    if version == 'v2':
        index = ES_VARS['INDEX_V2']
    else:
        index = ES_VARS['INDEX_V1']
    backup_index = '{}-tmp'.format(index)
    ES7.reindex(body={
        'source': {
            'index': index
        },
        'dest': {
            'index': backup_index
        }
    })

    try:
        for i in range(0, len(dataset), ES_VARS['BULK_SIZE']):
            body = []
            for org in dataset[i:i + ES_VARS['BULK_SIZE']]:
                body.append({
                    'index': {
                        '_index': index,
                        '_id': org['id']
                    }
                })
                if 'v2' in index:
                    org['names_ids'] = [{
                        'name': n
                    } for n in get_nested_names_v2(org)]
                    org['names_ids'] += [{
                        'id': n
                    } for n in get_nested_ids_v2(org)]
                    # experimental affiliations_match nested doc
                    org['affiliation_match'] = get_affiliation_match_doc(org)
                else:
                    org['names_ids'] = [{
                        'name': n
                    } for n in get_nested_names_v1(org)]
                    org['names_ids'] += [{
                        'id': n
                    } for n in get_nested_ids_v1(org)]
                body.append(org)
            print("example_1: ", body[0])
            print("example_1: ", body[1])
            print("example_2: ", body[8])
            print("example_2: ", body[9])
            ES7.bulk(body)
    except TransportError:
        err[index.__name__] = f"Indexing error, reverted index back to previous state"
        ES7.reindex(body={
            'source': {
                'index': backup_index
            },
            'dest': {
                'index': index
            }
        })
    if ES7.indices.exists(backup_index):
        ES7.indices.delete(backup_index)
    return err

class Command(BaseCommand):
    help = 'Indexes ROR dataset'

    def add_arguments(self, parser):
        parser.add_argument('dir', type=str, help='add directory name for S3 bucket to be processed')
        parser.add_argument('version', type=str, help='schema version of files to be processed')

    def handle(self,*args, **options):
        dir = options['dir']
        version = options['version']
        process_files(dir, version)


