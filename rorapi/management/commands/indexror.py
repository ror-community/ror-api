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
from rorapi.settings import ES, ES_VARS, DATA

from django.core.management.base import BaseCommand
from elasticsearch import TransportError


def get_nested_names(org):
    yield org['name']
    for label in org['labels']:
        yield label['label']
    for alias in org['aliases']:
        yield alias
    for acronym in org['acronyms']:
        yield acronym


def get_nested_ids(org):
    yield org['id']
    yield re.sub('https://', '', org['id'])
    yield re.sub('https://ror.org/', '', org['id'])
    for ext_name, ext_id in org['external_ids'].items():
        if ext_name == 'GRID':
            yield ext_id['all']
        else:
            for eid in ext_id['all']:
                yield eid

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
        os.mkdir(local_path)
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

    
def process_files(dir):
    err = []
    if dir:
        path = os.path.join("rorapi/data", dir)
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
                    index_error = index(data)
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
        msg = {"status": "OK", "msg": f"{dir} indexed"}
    
    return msg
    

def index(dataset):
    err = {}
    index = ES_VARS['INDEX']
    backup_index = '{}-tmp'.format(index)
    ES.reindex(body={
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
                        '_type': 'org',
                        '_id': org['id']
                    }
                })
                org['names_ids'] = [{
                    'name': n
                } for n in get_nested_names(org)]
                org['names_ids'] += [{
                    'id': n
                } for n in get_nested_ids(org)]
                body.append(org)
            ES.bulk(body)
    except TransportError:
        err[index.__name__] = f"Indexing error, reverted index back to previous state"
        ES.reindex(body={
            'source': {
                'index': backup_index
            },
            'dest': {
                'index': index
            }
        })

    if ES.indices.exists(backup_index):
        ES.indices.delete(backup_index)
    return err

class Command(BaseCommand):
    help = 'Indexes ROR dataset'

    def add_arguments(self, parser):
        parser.add_argument('dir', type=str, help='add directory name for S3 bucket to be processed')

    def handle(self,*args, **options):
        dir = options['dir']
        process_files(dir)

  
