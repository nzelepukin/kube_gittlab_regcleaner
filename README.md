# GITLAB REGISTRY CLEANER
### Decription
Have a couple Kubernetes clusters and GitLab registry full of unused images. Case is delete unused images from GitLab and keep images used by apps in Kubernetes.

### Local Run
 * `python3.9 start.py`
 
### Build
  * `docker build -t gitlab-regcleaner .`
 
### Environment variables
 * `GIT_TOKEN=asdasdasd` - GitLab token (api,read_repository, read_registry)
 * `KubeStageConfigPath=/app/stage.conf` - kubernetes config path (recomended permissions -  get, list, watch)
 * `KubeProdConfigPath=/app/prod.conf` - kubernetes config path. If you have more then 2 clusters or just 1 please edit string 85 start.py.
 * `MAX_CONNECTIONS=50` - parametr limits max simultaneous sessions for async framework.
 * `GITLAB_HOSTNAME=gitlab.my.ru` - hostname your gitlab.
 * `EXCLUDE_PROJECTS=project1,project2 ` - add projects that must be excluded from search or leave it blank.
 * `ONLY_THIS_GROUP=https://gitlab.my.ru/dev` - if you need to clean only one group or leave it blank.
 * `KUBE_HISTORY=5` - how much images from rollout history you want to keep.

