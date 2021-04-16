import logging
from kubernetes import client, config, watch

def get_images_from_namespace(namespace: str,output: dict)->dict:
    deploy_api = client.AppsV1Api()
    repl=deploy_api.list_namespaced_replica_set(namespace=namespace)
    for replica_set in repl.items:
        namespace=replica_set.metadata.namespace
        if not 'app' in replica_set.metadata.labels:
            app_name=f'{replica_set.spec.template.spec.service_account}-{namespace}'
        else: app_name=f'{replica_set.metadata.labels["app"]}-{namespace}'
        if app_name not in output: output[app_name]=[]
        app_record=dict()
        if 'deployment.kubernetes.io/revision' in replica_set.metadata.annotations:
            app_record['revision']=replica_set.metadata.annotations['deployment.kubernetes.io/revision']
        if 'kubernetes.io/change-cause' in replica_set.metadata.annotations:
            app_record['commit']=replica_set.metadata.annotations['kubernetes.io/change-cause']
        app_record['containers']=list()
        for container in replica_set.spec.template.spec.containers:
            app_record['containers'].append(container.image)
        output[app_name].append(app_record)
    return output

def get_namespaces()->list:
    core_api = client.CoreV1Api()
    namespaces = [ns.metadata.name  for ns in core_api.list_namespace().items]
    return namespaces

def get_images_from_cluster(filename:str)->dict:
    config.load_kube_config(config_file=filename)
    logging.info('Successfully connected to cluster')
    namespaces=get_namespaces()
    logging.info('Successfully got namespaces')
    output=dict()
    for ns in namespaces:
        logging.info(f'Trying to get images of namespace {ns}')
        output=get_images_from_namespace(ns, output)
    return output
