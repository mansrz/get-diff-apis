import os
import requests
import yaml
from random import random
import json
from deepdiff import DeepDiff
import argparse
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import Terminal256Formatter
from pygments.token import Token
from pprint import pformat
from pygments.style import Style


CONFIG_NAME = 'config.yml'
URL_SWAGGER = 'https://api.swaggerhub.com/apis'

class FormatStyle(Style):
    styles = { Token.String: 'ansibrightgreen bg:ansibrightblack', }

def pprint(obj):
    print(highlight(pformat(obj), PythonLexer(), Terminal256Formatter(style=FormatStyle)))

def read_config():
    config_file = read_file(CONFIG_NAME)
    if config_file:
        return yaml.load(config_file, yaml.FullLoader)
    return None

def read_vars(config):
    config_vars = []
    if config.get('config'):
        if config.get('config').get('swaggerkey'):
            config_vars.append(config.get('config').get('swaggerkey'))
    return tuple(config_vars)


def run_command(command, args):
    result = os.system(f'{command} >/dev/null 2>&1')
    return not result

def read_file(name):
    try:
        with open(name, 'r') as file:
            content = file.read()
            return content
    except Exception as e:
        print(e)
        return None

def write_file(name, data, format='json'):
    name = f'{name}{int(random()*10)}.{format}'
    with open(name, 'w') as file:
        file.write(data)
    return name

def read_swaggerhub(complete, owner, model, version, key):
    if  complete:
        url = f'{URL_SWAGGER}/{complete}'
    else:
        url = f'{URL_SWAGGER}/{owner}/{model}/{version}'
    response = requests.get(url=url, headers={"Authorization": key})
    if response.content:
        return yaml.load(response.content, yaml.FullLoader)
    return None

def read_aws(id, stage="prod", region="us-east-1", name_file="tmpfile"):
    name_file = f'{name_file}{int(random()*10)}'
    command = f'aws apigateway get-export --parameters extensions=\'apigateway\' --rest-api-id {id} --region {region} --stage-name "{stage}" --export-type swagger /tmp/{name_file}.json'
    result = run_command(command, "")
    if result:
        data = read_file(f'/tmp/{name_file}.json')
        if data:
            return yaml.load(data, yaml.FullLoader)
    return None

def main(swagger_info=None, awsid=None):

    # SwaggerHub Data
    owner = "" #can be in config file
    model = ""
    version = ""

    if not (swagger_info or awsid):
        pprint("Error")
        return {}

    config = read_config()
    if config:
        (swagger_key,) = read_vars(config)
        f_swagger = read_swaggerhub(swagger_info, owner, model, version, swagger_key)
        pprint("+ reading swigger configurations")
        write_file('swagger', json.dumps(f_swagger.get('paths')), 'json')
        f_aws = read_aws(awsid)
        pprint("+ reading aws configurations")
        write_file('aws', json.dumps(f_aws.get('paths')), 'json')
        f_diff = DeepDiff(f_swagger.get('paths'), f_aws.get('paths'), ignore_order=True)
        name = write_file('result', json.dumps(json.loads(f_diff.to_json()), indent=4))
        pprint(f"+ output in {name}")
    else:
        pprint("You need fill config file")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get diff from swagger & AWS API Gatewayo \n Use: python get_diffs.py --awsid idresource --swaggerinfo company/model/1.0.0')
    parser.add_argument('--awsid', type=str, nargs='+', help='resource rest api id')
    parser.add_argument('--swaggerinfo', type=str, nargs='+', help='Swagger {owner}/{model}/{version}')
    args = parser.parse_args()
    if args.awsid and args.swaggerinfo:
        awsinfo = args.awsid[0]
        swaggerinfo = args.swaggerinfo[0]
        main(swaggerinfo, awsinfo)
