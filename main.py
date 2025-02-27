import requests
import json
import subprocess

# Replace with your Snyk API token
API_TOKEN = '<your_api_token>'
GROUP_ID = '<your_group_id>'
BASE_URL_V1 = 'https://api.snyk.io/v1'
BASE_URL_REST = 'https://api.snyk.io'
REST_VERSION = "2024-10-15"

headers = {
    'Authorization': f'token {API_TOKEN}',
    'Content-Type': 'application/json'
}

def get_organizations():
    all_orgs={'data':[]}
    uri=f'/rest/groups/{GROUP_ID}/orgs?version={REST_VERSION}'
    
    while True:

        response = requests.get(f'{BASE_URL_REST}{uri}', headers=headers)
        response.raise_for_status()
        all_orgs['data'] += response.json()['data']
        if 'next' in response.json()['links']:
            uri = response.json()['links']['next'] # get the next page
        else:
            return all_orgs

def get_targets(org_id):
    all_targets={'data':[]}
    uri=f'/rest/orgs/{org_id}/targets?version={REST_VERSION}'

    while True:
       
        response = requests.get(f'{BASE_URL_REST}{uri}', headers=headers)
        response.raise_for_status()
        all_targets['data'] += response.json()['data']
        if 'next' in response.json()['links']:
            uri = response.json()['links']['next'] # get the next page
        else:
            return all_targets


def get_target_references(org_id, target_id):
    target_references = set()
    response = requests.get(f'{BASE_URL_REST}/rest/orgs/{org_id}/projects', params={'version':REST_VERSION, 'target_id': target_id}, headers=headers)
    
    response.raise_for_status()
    
    for project in response.json()['data']:
            target_references.add(project['attributes']['target_reference']) 

    return target_references

def reimport_target(org_id, target, target_reference):
    integration_id = target['relationships']['integration']['data']['id']
    
    url = f'{BASE_URL_V1}/org/{org_id}/integrations/{integration_id}/import'

    print(f'Reimporting target {target["id"]}')
    
    if len(target['attributes']['display_name'].split('/')) > 1 and target['relationships']['integration']['data']['attributes']['integration_type'] != 'cli':

        data = {
            'target': {
                "owner":target['attributes']['display_name'].split('/')[0],
                "name":target['attributes']['display_name'].split('/')[1],
                "branch":target_reference, # Replace with the branch you want to import - 
                                # we can't currently retrieve which branch is being monitored
            }
        }
        response = requests.post(url, data=json.dumps(data), headers=headers)
        response.raise_for_status()
        
        if response.status_code == 201:
            print(f'Target {target["id"]} reimported successfully')
        else:    
            print(f'Target {target["id"]} could not be reimported')
            print(response.json())
        
        return response.json()
    else:
        print(f'Target {target["id"]} does not have a valid owner/name format')

def main():

    # install the cli tool here for updating orgs to activate snyk code. 
    # just leveraging this...no point in re-inventing the wheel
    # https://github.com/jordanmilessnyk/snyk-rest-cli
    subprocess.run(['npm', 'install', '-g', 'snyk-rest-cli'])
    subprocess.run([
        'snyk-rest-cli', 
        f'--snyk_token={API_TOKEN}',
        f'--api_version={REST_VERSION}',
        f'--group_id={GROUP_ID}',
        '--update_snyk_code_orgs',
        '--sast_enabled=true'])
        
    organizations = get_organizations()
    
    for org in organizations['data']:

        print(f'Importing targets for org {org["id"]}')
        
        org_id = org['id']    
        targets = get_targets(org_id)

        for target in targets['data']:
            for target_reference in get_target_references(org_id, target['id']):
                reimport_target(org_id, target, target_reference)

if __name__ == '__main__':
    main()