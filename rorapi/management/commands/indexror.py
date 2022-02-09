import json
import re
from functools import wraps
from threading import local
import zipfile
import os
import glob
from os.path import exists
from rorapi.settings import ES, ES_VARS, DATA

from django.core.management.base import BaseCommand
from elasticsearch import TransportError


# figure out how to return errors. Have an errors hash that is then returned as a response?
ERR_MSG = {}
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
    try:
        if exists(local_file):
            with zipfile.ZipFile(local_file, 'r') as zip_ref:
                zip_ref.extractall(path) 
    except Exception as e:
        ERR_MSG[prepare_files.__name__] = f"ERROR: {e}"

    json_files = os.path.join(path, "*.json")
    file_list = glob.glob(json_files)
    for file in file_list:
        try:
            with open(file) as f:
                data.append(json.load(f))
        except Exception as e:
            ERR_MSG[file] =  f"ERROR: {e}"
    # clean this up so that it fails if there is any error with any file, maybe do a raise 
    return data
   

def get_rc_data(dir, contents):
    # clarify this function to report errors on creating files, download files, and if the branch is not found in the S3 bucket
    find_branch = re.compile(rf'^wip\/\b{dir}\b\/.*?.zip')
    branch_objects = [i for i in contents if find_branch.search(i['Key'])]
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
            ERR_MSG["downloading_files"] = f"ERROR: {e}"
    else:
       ERR_MSG[get_rc_data.__name__] = f"ERROR: {dir} not found in S3 bucket"
    return local_path, local_file

def get_data():
    # return contents or None
    contents = None
    try:
        objects = DATA['CLIENT'].list_objects_v2(Bucket = DATA['DATA_STORE'])
        contents = objects['Contents']
    except Exception as e:
        ERR_MSG[get_data.__name__] = f"ERROR: Could not get objects from {DATA['DATA_STORE']}: {e}"
    return contents

def msg(dir):
    return dir
    
def process_files(dir):
    # delete existing files in dir, if exists before starting over ?
    if dir:
        objects = get_data()
        if objects:
            # check if objects exist, otherwise error
            path, file = get_rc_data(dir, objects)
            if path and file: 
                data = prepare_files(path, file)
                index(data)
        else:
            ERR_MSG[process_files.__name__] = f"No objects found in {dir}"
    else:
        ERR_MSG[process_files.__name__] = "Need S3 directory argument"
    if ERR_MSG:
        print(ERR_MSG)
    

def index(dataset):
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
        print(TransportError)
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

class Command(BaseCommand):
    help = 'Indexes ROR dataset'

    def add_arguments(self, parser):
        parser.add_argument('dir', type=str, help='add directory name for S3 bucket to be processed')

    def handle(self,*args, **options):
        dir = options['dir']
        process_files(dir)

  
