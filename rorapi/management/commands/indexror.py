import json
from functools import wraps
from threading import local
import zipfile
import os
import glob
from os.path import exists
import pathlib
import shutil
from rorapi.settings import ES_VARS, DATA
from rorapi.common.index_helpers import bulk_index_with_backup

from django.core.management.base import BaseCommand


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
    if version != 'v2':
        err[index.__name__] = f"Only v2 schema version is supported. Received: {version}"
        return err
    index_name = ES_VARS['INDEX_V2']

    def on_transport_error(_exc):
        err[index.__name__] = f"Indexing error, reverted index back to previous state"

    bulk_index_with_backup(index_name, dataset, on_transport_error=on_transport_error)
    return err

class Command(BaseCommand):
    help = 'Indexes ROR dataset'

    def add_arguments(self, parser):
        parser.add_argument('dir', type=str, help='add directory name for S3 bucket to be processed')

    def handle(self,*args, **options):
        dir = options['dir']
        version = 'v2'
        process_files(dir, version)
