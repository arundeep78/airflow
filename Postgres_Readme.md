# PostgreSQL in Kind with persisted volumes on host

This documentation is to configure PostgresSQL with persistent volumes on the host where Kind cluster is running. This will help to keep the persistent data survive cluster, WSL2 and Windows restart.

Once this PostgreSQL is working, it can then be added into Airflow helm chart

* as an external Database configuration OR
* as a template inside customized helm chart.

## Create Kind Cluster with path mounted from host

This is based on [Kind extraMounts option](https://kind.sigs.k8s.io/docs/user/configuration/#extra-mounts).

In this case the default example provided with `HostToContainer` propogation did not work. Kind cluster would fail with below error.

```zsh
$kind create cluster --config=./kind/config23_pvnode.yaml
Creating cluster "kind-airflow" ...
 ✓ Ensuring node image (kindest/node:v1.23.0) 🖼
 ✗ Preparing nodes 📦 📦
ERROR: failed to create cluster: docker run error: command "docker run --hostname kind-airflow-worker --name kind-airflow-worker --label io.x-k8s.kind.role=worker --privileged --security-opt seccomp=unconfined --security-opt apparmor=unconfined --tmpfs /tmp --tmpfs /run --volume /var --volume /lib/modules:/lib/modules:ro --detach --tty --label io.x-k8s.kind.cluster=kind-airflow --net kind --restart=on-failure:1 --init=false --volume=/home/arundeep/projects/airflow/pv_data:/data:ro,rslave kindest/node:v1.23.0@sha256:49824ab1727c04e56a21a5d8372a402fcd32ea51ac96a2706a12af38934f81ac" failed with error: exit status 125
Command Output: 7c6963bbce1291dbc1b121194a164a4817943b818b12ae99ab338219688389a6
docker: Error response from daemon: path /home/arundeep/projects/airflow/pv_data is mounted on / but it is not a shared or slave mount.
```

### MountFlags in Docker service

As per the [documentation from kubernetes on MountPropagation](https://kubernetes.io/docs/concepts/storage/volumes/#mount-propagation), some operating systems would need to cofigure `MountFlags` parameter for Docker service. There were 2 issues with that.

1. Debian in WSL2 is not based on `systemd` and thus could not use that technique. Did not find how else it is possible.
2. Docker as of 18.09 version does not recommend/support MountFlags parameter as learned from this [github issue](https://github.com/coreos/bugs/issues/2579#issuecomment-486744151) and found in [Docker documentation.](https://docs.docker.com/engine/release-notes/18.09/#18091)

### solution

After reading various threads and articles on internet, though to remove `propagation` parameter from the config.yaml for kind cluster.

It works!!

### Add labels to nodes

In addition to adding hostPath, I also used the [Kubeadm configPatches options](https://kind.sigs.k8s.io/docs/user/configuration/#kubeadm-config-patches) from Kind to add node labels. This should help me later to decide which node to allocate pods to based on nodeAffinity feature of kubernetes objects.In my case I added

```yaml
kubeadmConfigPatches:
    - | 
      kind: JoinConfiguration
      nodeRegistration:
        kubeletExtraArgs:
          node-labels: "postgres=true"
```

## Prepare Storage objects for PostgreSQL

There are probably different ways to install PostgreSQL in kubernetes. I selected to use bitnami's [PostgreSQL helm chart](https://bitnami.com/stack/postgresql/helm) for this example. Mainly as that might help to learn helm as well along the way.

The default documentation makes it seems quite an easy task. But, if you are new to all these components and want to have persistence then it needs some extra effort. This [article helped](https://phoenixnap.com/kb/postgresql-kubernetes) me in that and I modified it a little bit for persistence related files for kubernetes.

Official documentation from Kubernetes helped me to learn below components and create respective yaml files.

I must say, it was a hard way to figure out between hostpath, local, storage class, dynamic vs static allocation etc. One of the challenge is that there are many ways to create same resources and every article or documentation one finds, has it's own way.

### StorageClass

Created a storage class for [local volume types](https://kubernetes.io/docs/concepts/storage/storage-classes/#local).

I Created this so as later if I use another type of storage then I would be required only to change this definition. [Yaml file available](kind/k8s/storage_class.yaml).

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: data-postgres-sc
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
```

### Pesistent volume

For a [local storage class Persistent volumes CANNOT be automatically created](https://kubernetes.io/docs/concepts/storage/volumes/#local). I used this official documentaion as base to define my Persistent Volume definition. [YAML file is available](kind/k8s/pv.yaml)

The configuration file also has a nodeSelectorTerms to check if the node is configured for `postgres`. In this case it means that this node has been passed a file path from Kind cluster host to persist DB files beyong Kind cluster lifecycle.

```yaml

## Persistent volumne for PostgreSQL
apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-postgres-pv
  labels:
    app: airflow
spec:
  capacity:
    storage: 2Gi
  volumeMode: Filesystem
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  storageClassName: data-postgres-sc
  local:
    path: /data
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: postgres
          operator: Exists
#          operator: In
#          values:
#          - "true" 
```

Now we have StorageClass defined and a persistent Volume is created which is based on this Storage Class, but points to the mount path which was passed on to a given Node from the host that is running Kind cluster!

Just writing this sentence makes you think of so many layers!!!

### Persistent Volume Claim

Now to create a [Persistent Volume Claim](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) that will make a claim to this above Persistent Volume. [Yaml file is available](kind/k8s/pvc.yaml)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-postgres-pvc
spec:
  storageClassName: data-postgres-sc 
#  volumeName: data-postgres-pv
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

### Create these objects in Kind cluster

Same as all of other objects, there are multiple ways to create these objects in Kubernetes. I tried 2 methods.

1. Using individual yaml files.
   This help to see individually as the objects are being created and how the relate to each other. I have to create separate files for each objects. Each file is the applied using `kubectl apply -f`
2. Using kustomization.yaml.
   As I undrstood it a bit more, I thought to merge these files in single `storage.yaml` using `---` seprator notation. Then I somehow came across `kubectl apply -k` method. I decided to use it to learn that tool as well. It meant that I had to create one additional file named `kustomization.yaml` and add other .yaml files into kustomization.yaml files to apply them all at once. There are many more advanced features of `kustomize` option, but that is for later.

   Files are added into `kustomization.yaml` with `resources` tag.

   ```yaml
     resources:
      - pv.yaml
      - pvc.yaml
      - storage_class.yaml
   ```

  This file is then applied to cluster using

  ```zsh
  $kubectl apply -k kind/k8s/
  storageclass.storage.k8s.io/data-postgres-sc created
  persistentvolume/data-postgres-pv created
  persistentvolumeclaim/data-postgres-pvc created
  ```

Now we are ready with persistent storage from cluster host mounted on k8s nodes for Postgres pods.

## Configure PostgreSQL Helm chart for persistence

Now that persistence storage sorted out for postgres, I can now configure the [Bitnami's PostgreSQL helm chart](https://bitnami.com/stack/postgresql/helm) to use it. [This article](https://phoenixnap.com/kb/postgresql-kubernetes) helped me to figure out key parts for the value.yaml for this helm chart, that I need to change.

Overall helm chart is quite complex and there are lots of variable in values.yaml. Well this statement is valid for me. Others may find it a simple configuration.

### Configure and update Helm repo

```zsh
helm repo add bitnami https://charts.bitnami.com/bitnami   
helm repo update
```

I used below command to have a look at complete chart and it's templates.

```zsh
helm pull bitnami/postgresql --untar   
```

There is a default `values.yaml` with various parameters that can be configured for this chart.

### Configure values.yaml

Based on the above mentioned article and my own configuration for storage, I updated below sections in the `values_custom.yaml` (which is a copy of original `values.yaml`) as below.

```yaml
auth:
  ## @param auth.enablePostgresUser Assign a password to the "postgres" admin user. Otherwise, remote access will be blocked for this user
  ##
  enablePostgresUser: true
  ## @param auth.postgresPassword Password for the "postgres" admin user
  ##
  postgresPassword: "postgres"
  ## @param auth.database Name for a custom database to create
  ##
  database: "arcticrisk"
## @section PostgreSQL Primary parameters
##
primary:
## @param primary.nodeSelector Node labels for PostgreSQL primary pods assignment
  ## ref: https://kubernetes.io/docs/user-guide/node-selection/
  ##
  nodeSelector: 
    postgres: "true" # This matches with extra label set in kind cluster worker node config.yaml
  ## PostgreSQL Primary persistence configuration
  ##
  persistence:
    ## @param primary.persistence.enabled Enable PostgreSQL Primary data persistence using PVC
    ##
    enabled: true
    ## @param primary.persistence.existingClaim Name of an existing PVC to use
    ##
    existingClaim: data-postgres-pvc # matches with PVC created above
    ## @param primary.persistence.storageClass PVC Storage Class for PostgreSQL Primary data volume
    ## If defined, storageClassName: <storageClass>
    ## If set to "-", storageClassName: "", which disables dynamic provisioning
    ## If undefined (the default) or set to null, no storageClassName spec is
    ##   set, choosing the default provisioner.  (gp2 on AWS, standard on
    ##   GKE, AWS & OpenStack)
    ##
    storageClass: "data-postgres-sc" # matches storage class defined earlier
    ##
    ## @param primary.persistence.size PVC Storage Request for PostgreSQL volume
    ##
    size: 1Gi # This however is not used in this case, as PV is created with given size. This probably is useful when dynamic provisioning is done based on respective StorageClass
```

**NOTE:** Once again there are different ways to configure these parameters e.g. password can be a preexisting secret. I chose to set it as default string as it helped me to configure my local DB client with standard password and do not have to confgure a new password everytime, if e.g. I decide to create random passwords based on defined secrets. In production environment however this approach should not be used.

## Install PostgreSQL helm chart

Install PostgreSQL helm chart with custom `values_custom.yaml`.

```zsh
$helm install $RN bitnami/postgresql --values helmcharts/postgresql/values_custom.yaml
NAME: rn-postgres
LAST DEPLOYED: Thu Mar 31 09:53:55 2022
NAMESPACE: default
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
CHART NAME: postgresql
CHART VERSION: 11.1.9
APP VERSION: 14.2.0

** Please be patient while the chart is being deployed **

PostgreSQL can be accessed via port 5432 on the following DNS names from within your cluster:

    rn-postgres-postgresql.default.svc.cluster.local - Read/Write connection

To get the password for "postgres" run:

    export POSTGRES_PASSWORD=$(kubectl get secret --namespace default rn-postgres-postgresql -o jsonpath="{.data.postgres-password}" | base64 --decode)

To connect to your database run the following command:

    kubectl run rn-postgres-postgresql-client --rm --tty -i --restart='Never' --namespace default --image docker.io/bitnami/postgresql:14.2.0-debian-10-r35 --env="PGPASSWORD=$POSTGRES_PASSWORD" \
      --command -- psql --host rn-postgres-postgresql -U postgres -d arcticrisk -p 5432

    > NOTE: If you access the container using bash, make sure that you execute "/opt/bitnami/scripts/entrypoint.sh /bin/bash" in order to avoid the error "psql: local user with ID 1001} does not exist"

To connect to your database from outside the cluster execute the following commands:

    kubectl port-forward --namespace default svc/rn-postgres-postgresql 5432:5432 &
    PGPASSWORD="$POSTGRES_PASSWORD" psql --host 127.0.0.1 -U postgres -d arcticrisk -p 5432
```

## Test DB connection

Use command above to forward the port to local host to connect to DB.

**NOTE:** Although in this case host is a Debian Linux. but this inside WSL2 on a Windows 11 machine. When we do this port forward, PostgreSQL is also available on Windows 11 host with same parameters.

```zsh
$kubectl port-forward --namespace default svc/rn-postgres-postgresql 5432:5432
```

Connect DB client on Windows to PostgreSQL. In this case it is [DBeaver](https://dbeaver.io/).

![DB client configuration for PostgreSQL](images/postgreSQL/db_connection.drawio.svg)

Persisted table across pod and kind cluster restarts.
