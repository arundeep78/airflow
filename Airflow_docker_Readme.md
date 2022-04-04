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
mkdir -p mkdir -p ../dags ./logs ./plugins ./pgdata
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

### Create custom image with Docker file

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
