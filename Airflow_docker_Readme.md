# Airflow installation using Docker compose

I came to try this after I had successfully managed to configure Airflow helm chart on [Kind Kubernetes cluster](Airflow_kind_readme.md). But I happend to find 2 things of concern there.

1. Github sync method is based on username and password for private repos. Github does not support that method any more now. I assume it would need to modify the Airflow image somehow.
2. I was not sure how to do DAG development using this K8s development installation. I know there is someway to connect to K8s clusters, but do not know yet.

## Motivation

Search on google/youtube led me to docker compose way of installing Airflow. I think, I kind of know how to connect VS code on Windows to a Docker container on WSL2 Debian image. So, thought this may work. We shall see now.

Idea is to use Docker compose version to develop DAGs, which are on local FS. This FS is connected to github repo. This repo can then sync with Kind/K8s installtion of Airflow. This way it will help to test the overall setup as well.

## Installation

I used [offical documentation](https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html) for Docker compose installation.

### Download docker-compose file

```zsh
curl -LfO 'https://airflow.apache.org/docs/apache-airflow/2.2.5/docker-compose.yaml'
```

### Setup local user

```zsh
mkdir -p ../dags ./logs ./plugins ./pgdata
echo -e "AIRFLOW_UID=$(id -u)" > .env
```

### Initialize DB

```zsh
docker-compose up airflow-init
```

### Run Airflow

```zsh
docker-compose up
```

### Cleanup

This test installation and run worked fine. Time to clean up the basic configuration and adapt it for specific use.

## Configuration

### Different dag folder and no default examples

I decided to have a separate dag folder in my github repo outside of docker folder. Idea was simply to try a new path and have it as common path for dags from different airflow configurations.

Also, I decided not to load default examples. Reason is probably that I will follow a tutorial which is not based on @task operator of Airflow, but works without it. For some reason it felt easier. We shall see.

Also exposed DB port to connect from local DB client.

Mounted local volume for postgres data to have persistent storage.

In `docker-compose.yaml` change below settings

```yaml
x-airflow-common:
  environment:
    AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
  volumes:
    - ../dags:/opt/airflow/dags
services:
  postgres:
    ports:
      - 5432:5432
    volumes:
    #- postgres-db-volume:/var/lib/postgresql/data
    - ./pgdata:/var/lib/postgresql/data
   
```

**Challenge:**: This caused a problem between host and docker IDs. Data persists in this hostpath even after cleanup. But, the postgres image has different user configuring this path. This caused future `docker-compose build` commands to fail due to permissions issue. To solve this, I have to execute below command everytime before calling `build`

```zsh
chown -R {hostuser} ./docker_airflow/pgdata
```

### Create custom image with Docker file using exta pip packages

This I used to add new packages to the image. Other option is to use `_PIP_ADDITIONAL_REQUIREMENTS` parameter in .evn file and set additiona packages. But, I think this way once image is build it will be directly loaded locally rather then installing packages everytime.

After these changes one must execure `docker-compose build` in the directory where `docker-compose` and `Dockerfile` files are.

`Dockerfile`

```Dockerfile
FROM apache/airflow:2.2.5
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir \
  && netCDF4=1.5.8 \
  && ecmwf-opendata=0.1.1 \
  && ecmwf-api-client=1.6.3 \
  && minio=7.1.5
```

Changes in `docker-compose.yaml`. Comment `image` and uncomment `build`.

```yaml
x-airflow-common:
  &airflow-common
  # In order to add custom dependencies or upgrade provider packages you can use your extended image.
  # Comment the image line, place your Dockerfile in the directory where you placed the docker-compose.yaml
  # and uncomment the "build" line below, Then run `docker-compose build` to build the images.
  #image: ${AIRFLOW_IMAGE_NAME:-apache/airflow:2.2.5}
  build: .
```

### Development container configuration with VSCode

Now I have airflow

* configured in Docker
* it has persistent DB on host
* it has dags and logs folder on host that can synced to github repo from host.

Now, how to connect to this development environment

* where dags can be developed,
* have all python linting and help available and
* DAG python file can be tested to check if it works with its configuration

For this I needed help from

* [Create development container using Docker compose](https://code.visualstudio.com/docs/remote/create-dev-container#_use-docker-compose)
* [Add non-root user to a container](https://code.visualstudio.com/remote/advancedcontainers/add-nonroot-user)

with the help of these documentation and trial and error, I configured below entries for `.devcontainer/devcontainer.json`

```json
  // For format details, see https://aka.ms/devcontainer.json. For config options, see the README at:
  // https://github.com/microsoft/vscode-dev-containers/tree/v0.231.3/containers/docker-from-docker-compose
  {
    "name": "Airflow DAG in docker",
    "dockerComposeFile": "../docker_airflow/docker-compose.yaml",
    "service": "airflow-scheduler",
    "workspaceFolder": "/opt/airflow/dags",
 
    // Set *default* container specific settings.json values on container create.
    "settings": {
      "terminal.integrated.profiles.linux": {
        "bash": {
          "path": "/bin/bash"
        }
      }
    },

    // Add the IDs of extensions you want installed when the container is created.
    "extensions": [
      "ms-azuretools.vscode-docker",
      "ms-python.python",
      "ms-python.vscode-pylance"
    ],
    // Comment out to connect as root instead. More info: https://aka.ms/vscode-remote/containers/non-root.
    "remoteUser": "airflow",

  // This was important as otherwise, everytime I closed/disconnected from container, it would shutdown the complete airflow environment
    "shutdownAction": "none"
  }
```

This configruation now

1. Connects to a running docker container started from `docker-compose.yaml`. Container is referenced with `service name` defined in the file.
2. It opens up the `DAGS` folder in the container to start the development.
3. It loads VScode python extensions to have linting and other capabilities.
4. Allow to write and test code in airflow environment

**Challenge** was `remoteUser`. As per [airflow documentation](https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html) and standard `docker-compose.yaml` file I should set `AIRFLOW_UID` in `.env`. I did that, but it caused problems when trying to connect to container using VScode remote containers.

It turns out that if I specify remoteUser as `airflow`, it could not access certain paths. It would fail with error below

```zsh
/bin/sh: 15: cannot create /home/airflow/.vscode-server/data/Machine/.connection-token-e18005f0f1b33c29e81d732535d8c0e47cafb0b5-74f0c71b-a295-4c6d-9d1a-0f8842781a49: Permission denied
```

If I used `default` user then VSCode could not access terminal.
Reason was that airflow image creates a `default` user with id = `AIRFLOW_UID` which does not have any default shell assigned to it.

This led me to add below changes to `Dockerfile` for airflow image.
This meant that `airflow` user has the same UID as my default user on host. Thus files created by these users are accessible on host as well as container. Also `airflow` user has a shell defined, so it worked with Vscode terminal as well.

```Dockerfile
FROM apache/airflow:2.2.5

# This was key to solve that development problem. 
USER root

ARG USERNAME=airflow
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && usermod --uid $USER_UID --gid $USER_GID $USERNAME \
    && chown -R $USER_UID:$USER_GID /home/$USERNAME

USER ${USERNAME} 
   
RUN python -m pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

```

Now it is possible to use this configuration to execute `Remote Containers: |Reopen in Container`

![Open in remote container](images/airflow/airflow_vscode_devcontainer_docker.drawio.svg)

Once opened in container, development can start in the dag folder.

![Vscode in airflow container](images/airflow/airflow_vscode_devcontainer_terminal.drawio.svg)