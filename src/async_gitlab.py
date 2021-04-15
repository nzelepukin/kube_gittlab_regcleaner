import requests, json, os, logging
import aiohttp,asyncio,tqdm

###  Начало блока для асинхронного сбора инфы GET'ом 

async def browsing_get(sem, url: str, headers: str, session: aiohttp.ClientSession)->str:
    ''' Get info '''
    async with sem:
        async with session.get(url,headers=headers,ssl=False) as request:
            if request.status==200:
                return await request.read()
            else: return b'[]'

async def browsing_join(url_base: list, headers: str, max_sessions: int)->list:
    ''' Control asinc getting pages '''
    tasks=[]
    sem=asyncio.Semaphore(max_sessions)
    async with aiohttp.ClientSession() as session: 
        for url in url_base:
            task = asyncio.ensure_future(browsing_get(sem,url,headers,session))
            tasks.append(task)
        for future in tqdm.tqdm(tasks, total=len(url_base)):
            await future
    return await asyncio.gather(*tasks)

### Конец блока для асинхронного сбора инфы GET'ом


### Начало блока для сбора X-Total из заголовка ответа и добавление результата в словарь

async def browsing_get_header(sem, record: dict, headers: str, session: aiohttp.ClientSession)->str:
    ''' Get X-Total from header and add to dict '''
    async with sem:
        async with session.get(record['url'],headers=headers,ssl=False) as request:
            if request.status==200:
                record['total'] = int(request.headers['X-Total'])
                return record
            else: return record

async def browsing_header(base: list, headers: str, max_sessions: int)->list:
    ''' Control asinc getting pages '''
    tasks=[]
    sem=asyncio.Semaphore(max_sessions)
    async with aiohttp.ClientSession() as session: 
        for each in base:
            task = asyncio.ensure_future(browsing_get_header(sem,each,headers,session))
            tasks.append(task)
        for future in tqdm.tqdm(tasks, total=len(base)):
            await future
    return await asyncio.gather(*tasks)

### Конец блока для сбора X-Total из заголовка ответа и добавление результата в словарь


###  Начало блока для асинхронного сбора инфы GET'ом, сделал отдельно чтобы склеивать вывод с URL
#       эта связка нужна для создания URL для удаления 

async def browsing_get_tags(sem, url: str, headers: str, session: aiohttp.ClientSession)->str:
    ''' Get info '''
    async with sem:
        async with session.get(url,headers=headers,ssl=False) as request:
            if request.status==200:
                data = await request.read()
                return {'url': url,'data': json.loads(data)}
            else: logging.error(f'No tag {url}')

async def browsing_join_tags(url_base: list, headers: str, max_sessions: int)->list:
    ''' Control asinc getting pages '''
    tasks=[]
    sem=asyncio.Semaphore(max_sessions)
    async with aiohttp.ClientSession() as session: 
        for url in url_base:
            task = asyncio.ensure_future(browsing_get_tags(sem,url,headers,session))
            tasks.append(task)
        for future in tqdm.tqdm(tasks, total=len(url_base)):
            await future
    return await asyncio.gather(*tasks)
###  Конец блока для асинхронного сбора инфы GET'ом, сделал отдельно чтобы склеивать вывод с URL


### Начало блока для асинхронного удаления тегов, по итогу возвращает строку об удачном или не удачном удалении

async def browsing_del_tags(sem, url: str, headers: str, session: aiohttp.ClientSession)->str:
    ''' Deleting tags '''
    async with sem:
        async with session.delete(url,headers=headers,ssl=False) as request:
            if request.status==200:
                return url
            else: 
                logging.error(f'Cant delete tag {url}')
                return f'--=Cant delete=--{url}'

async def browsing_join_del_tags(url_base: list, headers: str, max_sessions: int)->list:
    ''' Control asinc deleting '''
    tasks=[]
    sem=asyncio.Semaphore(max_sessions)
    async with aiohttp.ClientSession() as session: 
        for url in url_base:
            task = asyncio.ensure_future(browsing_del_tags(sem,url,headers,session))
            tasks.append(task)
        for future in tqdm.tqdm(tasks, total=len(url_base)):
            await future
    return await asyncio.gather(*tasks)
### Конец блока асинхронного удаления


def get_gitlab_projects(hostname: str, token: str, headers: dict)->list:
    '''
    Функция собирает информацию о всех проектах находящихся на GitLab сервере
    Для работы нужен API токен c правами на api и read_repository
    '''
    projects=list()
    params={"per_page": 20}
    url=f"http://{hostname}/api/v4/projects"
    response = requests.get(url, headers=headers, params=params)
    try:
        total_items=int(response.headers['X-Total'])
    except:
        logging.error('Please check your GitLab token.')
        exit()
    logging.info(f"Found {total_items} projects in GitLab")
    if total_items % 100 > 0: total_pages=total_items // 100 + 1
    else: total_pages=total_items // 100
    urls = [url+'?per_page=100&page='+str(page) for page in range(1,total_pages+1)]
    response = asyncio.run(browsing_join(urls, headers, 10))
    for each in response:
        projects+=json.loads(each)
    return projects


def get_registry(hostname: str, token:str, headers:dict, max_connections: int, exclude_projects=[''], only_this_group='')->list:
    '''
    Функция собирает теги в репозиториях registry и возвращает список тегов(dict) 
    в том виде в каком отдает gitlab с парой кастомным полем - URL для удаления
    '''
    projects = get_gitlab_projects(hostname,token, headers) # Берем список проектов
    if only_this_group!='': 
        projects = [project for project in projects if only_this_group in project['web_url'].lower()]
    if exclude_projects!=['']: 
        projects = [project for project in projects if project['name'].lower() not in exclude_projects]  
    registry=list()
    registry_urls=list()
    repos=list()
    repo_urls = [f"https://{hostname}/api/v4/projects/{project['id']}/registry/repositories" for project in projects] 
    response = asyncio.run(browsing_join(repo_urls, headers, max_connections))
    for each in response:
        tmp = json.loads(each)
        if tmp != []:
            repos += tmp
    for repo in repos:
        repo['url']= f"https://{hostname}/api/v4/projects/{repo['project_id']}/registry/repositories/{repo['id']}/tags"
    repos= asyncio.run(browsing_header(repos, headers, max_connections))
    for repo in repos:
        if repo['total'] % 100 > 0: total_pages=repo['total'] // 100 + 1
        else: total_pages=repo['total'] // 100
        registry_urls+=[repo['url']+'?per_page=100&page='+str(page) for page in range(1,total_pages+1)]
    response = asyncio.run(browsing_join_tags(registry_urls, headers, max_connections))
    for each in response:
        for tag in each['data']:
            tag['del_url']=each['url'][:each['url'].find('?')]+'/'+tag['name']
        each['data']=[tag for tag in each['data'] if tag['name'] != 'latest']
        registry+=each['data']
    return registry

def del_registry_tags(url_base: list, headers: str, max_sessions: int)->list:
    output=asyncio.run(browsing_join_del_tags(url_base,headers,5))
    return output