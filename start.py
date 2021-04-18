import json, os, time, logging
from src.async_gitlab import get_registry, del_registry_tags
from src.kube import get_images_from_cluster

def parse_gitlab_tags(hostname: str, token: str, headers: dict, max_connections: int, exclude_projects: list, only_this_group: str)->dict:
    '''
    Get info from GitLab and transform to usable structure.
    '''
    raw_data=get_registry(hostname, token, headers, max_connections, only_this_group=only_this_group,exclude_projects=exclude_projects)
    raw_data = {image['location']:image['del_url'] for image in raw_data}
    return raw_data


def parse_kube(filename: str, hisory_leghth: int, group: str)->list:
    '''
    Get info from Kubernetes and transform to usable structure.
    '''
    raw_data=get_images_from_cluster(filename)
    image_base=list()
    for app in raw_data:
        image_buffer=list()
        raw_data[app] = {int(i['revision']):i['containers'] for i in raw_data[app] if i['containers'][0].startswith(group)}
        for revision in sorted(raw_data[app].keys())[::-1]:
            if len(image_buffer)<hisory_leghth:
                if raw_data[app][revision] not in image_buffer: image_buffer.append(raw_data[app][revision])
            else: 
                break
        for image in image_buffer:
            image_base+=image
    return image_base

def show_stat(kube_image_base: set,gitlab_image_base: set, kube_history: int)->None:
    '''
    Image sorting statistics.
    '''
    text= f'''
    GitLab registry images - {len(gitlab_image_base)}
    Images from kubernetes replicaset rollout history({kube_history} last images) - {len(kube_image_base)}
    Images from kubernetes, found in GitLab - {len(kube_image_base.intersection(gitlab_image_base))}
    Images from kubernetes, not found in GitLab - {len(kube_image_base.difference(gitlab_image_base))}
    Removal candidates - {len(gitlab_image_base.difference(kube_image_base))}
    '''
    logging.info(text)

def show_del_stat(del_image_base: list)->None:
    '''
    Minimal deletion statistics
    '''
    output={'stage':[],'prod':[],'other':[], 'forbidden':[]}
    for each in del_image_base:
        if '--=Cant delete=--' in each: output['forbidden'].append(each)
        elif 'prod' in each: output['prod'].append(each)
        elif 'stage' in each: output['stage'].append(each)
        else: output['other'].append(each)
    text= f'''
    Prod tags deleted - {len(output['prod'])}
    Stage tags deleted - {len(output['stage'])}
    Other tegs deleted - {len(output['other'])}
    Cant delete - {len(output['forbidden'])}
    '''
    logging.info(text)


class Timer():
    def __init__(self):
        self.start=time.time()
    def stop(self):
        logging.info(f' ---- Runtime {int(time.time()-self.start)} sec ---- ')


timer=Timer()

### Environment variables
GIT_TOKEN=os.environ['GIT_TOKEN'] 
gitlab_hostname=os.environ['GITLAB_HOSTNAME']
max_connections=int(os.environ['MAX_CONNECTIONS'])
exclude_projects=[each.strip().lower() for each in os.environ['EXCLUDE_PROJECTS'].split(',')]
only_this_group=os.environ['ONLY_THIS_GROUP']
kube_history=int(os.environ['KUBE_HISTORY'])
remove_unused_tags=os.getenv("REMOVE_UNUSED_TAGS", 'False').lower() in ('true', '1', 't')
###
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
headers= {"PRIVATE-TOKEN":GIT_TOKEN}
clusters=[os.environ['KubeStageConfigPath'],os.environ['KubeProdConfigPath']]            
kube_image_base=list()
logging.info(f'Working with {gitlab_hostname}')
gitlab_image_base=parse_gitlab_tags(gitlab_hostname,GIT_TOKEN,headers,max_connections,exclude_projects,only_this_group )
gitlab_registry_url = [each for each in gitlab_image_base.keys()][0]
only_this_group=gitlab_registry_url[:gitlab_registry_url.find('/')]+'/'+'/'.join(only_this_group.split('/')[3:])
logging.info(f'Successfully finish with {gitlab_hostname}')
for cluster in clusters:
    kube_image_base+=parse_kube(cluster,kube_history,group=only_this_group)
kube_image_base=set(kube_image_base)
show_stat(kube_image_base,set(gitlab_image_base.keys()),kube_history)
del_candidates=list()
for tag in set(gitlab_image_base.keys()).difference(kube_image_base):
    del_candidates.append(gitlab_image_base[tag])
logging.info(f'Got {len(del_candidates)} candidates to delete')
if remove_unused_tags:
    del_output=del_registry_tags(del_candidates,headers,max_connections)
    show_del_stat(del_output)
timer.stop()
