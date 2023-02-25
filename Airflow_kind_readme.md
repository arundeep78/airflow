# Airflow on Kubernetes(Kind) using official helm chart

NOTE: This procedure is based on [Kind installation of K8s](https://github.com/arundeep78/wsl_debian_dev/blob/master/Kind_k8s_Readme.md). If you do have the WSL image are prepared in that document some extra steps might be required based on our specific situation.

## Create a directory structure for airflow project

Create directries for airflow project. These directories store configuration files for Helm chart for airflow, any image files that it might need, test DAGs etc. These files can be uploaded to github as needed.

You will follow your own project organization methods. This one I just throught might work for me. We shall see  :)

```zsh
# for main airflow project
mkdir ~/projects/airflow 
# to keep kind k8s cluster related config files
mkdir ~/projects/airflow/kind 
# to keep airflow helm chart deplyment/installation related files
mkdir ~/projects/airflow/helmcharts 

# Enter in the main project directory and start code for documentations.
# You would use any other tool that you might like for coding/documentation
cd ~/projects/airflow
code .
```

## Create a config.yaml file for kind cluster

Create a config.yaml file to creare a kind cluster. This cluster will be used to deploy Airflow using Helm chart.

`./kind/config.yaml`

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: kind-airflow
nodes:
- role: control-plane
  image: kindest/node:v1.20.7@sha256:cbeaf907fc78ac97ce7b625e4bf0de16e3ea725daf6b04f930bd14c
67c671ff9
- role: worker
  image: kindest/node:v1.20.7@sha256:cbeaf907fc78ac97ce7b625e4bf0de16e3ea725daf6b04f930bd14c
67c671ff9
```

**NOTE**: I used 1.20 image specifically as in my case 1.21 image was failing for some reason.

## Create kind cluster using this config.yaml

```zsh
kind create cluster --config=./kind/config.yaml                                              ─╯
Creating cluster "kind-airflow" ...
 ✓ Ensuring node image (kindest/node:v1.20.7) 🖼
 ✓ Preparing nodes 📦 📦
 ✓ Writing configuration 📜
 ✓ Starting control-plane 🕹️
 ✓ Installing CNI 🔌
 ✓ Installing StorageClass 💾
 ✓ Joining worker nodes 🚜
Set kubectl context to "kind-kind-airflow"
You can now use your cluster with:

kubectl cluster-info --context kind-kind-airflow
```

A simple check as proposed above in the output shows

```zsh
kubectl cluster-info --context kind-kind-airflow                                      ─╯
Kubernetes control plane is running at https://127.0.0.1:46493
KubeDNS is running at https://127.0.0.1:46493/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

## Create a namespace in the cluster for airflow installation

```zsh
export NS=ns-airflow
kubectl create namespace $NS
```

OR create a [namespace file](kind/namespace.yaml) and execute

```zsh
kubectl apply -f ./kind/namespace.yaml
```

## Add apache airflow helm repository

```zsh
helm repo add apache-airflow https://airflow.apache.org
helm repo update
```

NOTE: apache-airflow is just local name given to the long URL of the repository.

If you want to see all the config files in the airflow Helm chart then execute below command

```zsh
cd ./helmcharts
helm pull apache-airflow/airflow --untar
```

The above command pulls a specific Chart from the given repository; in this case airflow.

## Install the chart with default configuration

use the local copy of the chart

```zsh
export RELEASE_NAME=rn-airflow
helm install $RELEASE_NAME . --namespace $NS
```

OR

use directly from the repository url

```zsh
export RELEASE_NAME=rn-airflow
helm install $RELEASE_NAME apache-airflow/airflow --namespace $NS
```

**FAIL**: failed post-install: timed out waiting for the condition

Well, I do not remember when I last executed some statements following an article that just executed as mentioned. Not to say the instructions are wrong, but to highlight the variation of environments is so large for any instructions or softwares to capture all.

Apparently, lots of people have been [facing this issue](https://github.com/apache/airflow/issues/16176).

For some deleting the namespace and executing steps again worked. Windows restart solving issues! ?

I am in those for whom that trick did not work.

Interestingly, in these issues one can find reference to articles with headlines " **Airflow in Kubernetes in 10 mins**". This IMO is one of the cause of such issues. People are led to beleive that all is just so simple.

## Attempt 2 leading to same issue

<details>
  <summary> Click to expand</summary>

Cleanup

```zsh
kind delete cluster --namespace $NS
```

start again

1. create kind cluster
2. create namespace in cluster
3. set default namespace for kubectl commands

   ```zsh
   kcn $NS # This short works if you have Oh My ZSH installed
   ```

4. Helm install with debug option

  ```zsh
  helm install $RELEASE_NAME apache-airflow/airflow --namespace $NS --debug
  ```

</details>

## Same issue again. let the Sherlock lose on investigation

<details>

<summary>click to expand</summary>

1. Check pods. All are in `ImagePullBackOff` status

   ```zsh
   kgp
   ```

2. get logs of one of the failed pods

   ```zsh
   kdp rn-airflow-redis-0 # you may have a different pod name
   ```

3. Error seems to be getting image downloaded from Docker.io into the node

   ```zsh
   Failed to pull image "redis:6-buster": rpc error: code = Unknown desc = failed to pull and unpack image "docker.io/library/redis:6-buster": failed to resolve reference "docker.io/library/redis:6-buster": failed to do request: Head "https://registry-1.docker.io/v2/library/redis/manifests/6-buster": dial tcp: lookup registry-1.docker.io on 172.19.0.1:53: no such host
   ```

4. Try reaching out the host `registry-1.docker.io` on the host machine. it seems get the IP address, just that ping is blocked(probably) at server level

   ```zsh
    $ping registry-1.docker.io
    PING registry-1.docker.io (54.198.211.201) 56(84) bytes of data.
    $ping registry.docker.io
    PING registry-1.docker.io (54.198.211.201) 56(84) bytes of data.
    $ping docker.io
    PING docker.io (34.237.197.36) 56(84) bytes of data.
   ```

5. That means host WSL Debian can reach docker. Some network issue in cluster node images. Let's see if node has access to internet. Which nodes exists in kind cluster?

    ```zsh
    $kind get nodes --name kind-airflow
    kind-airflow-worker
    kind-airflow-control-plane
    ```

6. As these nodes are actually docker images running in the host, we can open an interactive session with the worker node.

   ```zsh
   docker exec -it kind-airflow-worker bash
   root@kind-airflow-worker:/#
   ```

7. As this is a restricted image need to install basic tools first

    ```zsh
    apt update
    apt install iputils-ping traceroute
    ```

8. Lets try reaching out the docker.io and registry-1.docker.io from this node

    ```zsh
    $root@kind-airflow-worker:/# ping docker.io
    PING docker.io (34.237.197.36) 56(84) bytes of data.
    $root@kind-airflow-worker:/# ping registry-1.docker.io
    ping: registry-1.docker.io: No address associated with hostname
    $root@kind-airflow-worker:/# ping registry.docker.io
    ping: registry.docker.io: Name or service not known
    ```

9. For some reason this node can reach to docker.io with same IP address as host, but cannot find IP address of registry-1.docker.io. Why? can it reach other common hosts? Lets try some of the common ones

    ```zsh
    $root@kind-airflow-worker:/# ping google.com
    PING google.com (216.239.32.10) 56(84) bytes of data.
    64 bytes from ns1.google.com (216.239.32.10): icmp_seq=1 ttl=105 time=41.0 ms
    $root@kind-airflow-worker:/# ping yahoo.com
    PING YAHoo.com (98.137.11.163) 56(84) bytes of data.
    64 bytes from media-router-fp74.prod.media.vip.gq1.yahoo.com (98.137.11.163): icmp_seq=1 ttl=42 time=186 ms
    $root@kind-airflow-worker:/# ping amazon.com
    PING aMAzon.com (176.32.103.205) 56(84) bytes of data.
    64 bytes from 176.32.103.205 (176.32.103.205): icmp_seq=1 ttl=233 time=131 ms
    ```

10. The node has internet connection, great!. But for some reason it just cannot resolve that particular host related to docker registry!! This means general internet routing is working. In this specific case.

    `From Kubernetes KIND cluster node(which is a docker container) > to WSL2 Debian host (running docker engine) > Windows 11 (with WSL2) > to router and further.`

11. How are the network settings in different computing units
    1. In Kind worker node, which is infact a docker container

        ```zsh
        $root@kind-airflow-worker:/ hostname -I
        10.244.1.1 10.244.1.1 10.244.1.1 10.244.1.1 10.244.1.1 10.244.1.1 172.19.0.2 10.244.1.1 10.244.1.1 10.244.1.1 fc00:f853:ccd:e793::2
        $root@kind-airflow-worker:/ cat /etc/resolv.conf
        nameserver 172.19.0.1
        options ndots:0
        ```

    2. In WSL2 machine that hosts the docker environment and kind deployment

        ```zsh
        $hostname -I
        172.17.121.109 172.17.0.1 172.19.0.1 172.18.0.1 fc00:f853:ccd:e793::1
        $cat /etc/resolv.conf
        # This file was automatically generated by WSL. To stop automatic generation of this file, add the following entry to /etc/wsl.conf:
        # [network]
        # generateResolvConf = false
        nameserver 172.17.112.1
        ```

    3. In windows machine running WSL 2 image

        ```powershell
        ipconfig
        Wireless LAN adapter Wi-Fi:

          Connection-specific DNS Suffix  . : TL-WA860RE
          Link-local IPv6 Address . . . . . : fe80::8cde:69ec:2173:cd80%15
          IPv4 Address. . . . . . . . . . . : 192.168.1.102
          Subnet Mask . . . . . . . . . . . : 255.255.255.0
          Default Gateway . . . . . . . . . : 192.168.1.1

       Ethernet adapter vEthernet (WSL):

          Connection-specific DNS Suffix  . :
          Link-local IPv6 Address . . . . . : fe80::b1b4:4306:8fd8:368e%43
          IPv4 Address. . . . . . . . . . . : 172.17.112.1
          Subnet Mask . . . . . . . . . . . : 255.255.240.0
          Default Gateway . . . . . . . . . :
        ```

12. This seems OK! atleast to me. Kind node with IP address 172.19.0.2 points to 172.19.0.1 as nameserver, which is IP of the host machine running Kind cluster in docker. This hostmachine points to 172.17.112.1 as nameserver, which is IP address of the WSL interface. And that some connects to local adapter on Windows and out it goes to the internet world. This is how it can connect to google and yahoo and likes. Not sure what is the block for registry.docker.io. I need some network expert!!!
13. How about `traceroute`?. It seems for some reason DNS tables are not reaching the Kind node. Not sure, as to why only registry-1.docker.com is not working
    1. On Debian host WSL2 image

        ```zsh
        $traceroute docker.io
        traceroute to docker.io (35.171.64.121), 30 hops max, 60 byte packets
        1  arunpc.mshome.net (172.17.112.1)  0.338 ms  0.223 ms  0.214 ms
        2  speedport.ip (192.168.1.1)  3.671 ms  3.621 ms  6.535 ms
        $traceroute registry-1.docker.io
        traceroute to registry-1.docker.io (54.198.211.201), 30 hops max, 60 byte packets
        1  arunpc.mshome.net (172.17.112.1)  0.251 ms  0.172 ms  0.166 ms
        2  speedport.ip (192.168.1.1)  2.993 ms  3.070 ms  5.096 ms
        ```

    2. On kind node

        ```zsh
        $root@kind-airflow-worker:/ traceroute registry-1.docker.io
        registry-1.docker.io: No address associated with hostname
        Cannot handle "host" cmdline arg 'registry-1.docker.io' on position 1 (argc 1)
        $root@kind-airflow-worker:/ traceroute docker.io
        traceroute to docker.io (54.84.243.136), 30 hops max, 60 byte packets
        1  172.19.0.1 (172.19.0.1)  0.246 ms  0.010 ms  0.006 ms
        2  arunpc.mshome.net (172.17.112.1)  0.193 ms  0.145 ms  0.208 ms
        3  speedport.ip (192.168.1.1)  2.803 ms  2.778 ms  2.733 ms

        ```

        however traceroute to IP address as given by WSL host is working.

        ```zsh
        $root@kind-airflow-worker:/ traceroute 54.198.211.201
        traceroute to 54.198.211.201 (54.198.211.201), 30 hops max, 60 byte packets
        1  172.19.0.1 (172.19.0.1)  0.226 ms  0.011 ms  0.005 ms
        2  arunpc.mshome.net (172.17.112.1)  0.272 ms  0.253 ms  0.262 ms
        3  speedport.ip (192.168.1.1)  2.693 ms  2.704 ms  3.169 ms
        ```

14. It seems trouble is only with the specific name resolution. Maybe it has something to do with the host with hyphen '-' in the name. But that should also mean that it is something specific to the Node image's linux version/configuration etc. As same host is working through Debian on WSL and Windows. Well, it does not seem to be a generic issue. I searched for some websites with hyphen in names and it works!!. What is wrong with registry-1.docker.io and where??

    ```zsh
    $root@kind-airflow-worker:/ ping street-map.co.uk
    PING street-map.co.uk (199.59.243.200) 56(84) bytes of data.
    64 bytes from 199.59.243.200 (199.59.243.200): icmp_seq=1 ttl=118 time=17.1 ms
    $root@kind-airflow-worker:/ ping merriam-webster.com
    PING merriam-webster.com (65.9.20.55) 56(84) bytes of data.
    64 bytes from server-65-9-20-55.zag50.r.cloudfront.net (65.9.20.55): icmp_seq=1 ttl=243 time=18.2 ms
    $root@kind-airflow-worker:/ ping ghcr.io
    PING ghcr.io (140.82.121.33) 56(84) bytes of data.
    ```

15. There are some articles that talks about hyphens and underscores in hostnames. But none that could specify why just a specific host won't work. As my knowledge of networks is limited, so I have not clue what could I do. So, i tried to setup `/etc/resolve.conf` in Kind node image same as it is for the WSL Debian host where docker/kind is running and give it a try. It works!!!.

    ```zsh
    $root@kind-airflow-worker:/ nano /etc/resolv.conf

    #nameserver 172.19.0.1
    nameserver 172.17.112.1
    options ndots:0

    $root@kind-airflow-worker:/ traceroute registry-1.docker.io
    traceroute to registry-1.docker.io (52.200.37.142), 30 hops max, 60 byte packets
    1  172.19.0.1 (172.19.0.1)  0.075 ms  0.015 ms  0.010 ms
    2  arunpc.mshome.net (172.17.112.1)  0.193 ms  0.170 ms  0.162 ms
    ```

16. But why? Where is the block for registry-1.docker.io in the original/default setup when everything else is working? This may be a search later, but for now need to see what can I need to change so that this change remains in the node image even when I delete the kind cluster and restart it. Is it a docker change or something need to be added to the kind cluster's config.yaml? as I change in docker then it will be for every docker/kind instance. Maybe better to find image/cluster specific solution.


</details>

## Alternate way: Change the node image version. once again!

<details>

<summary>
click to expland
</summary>

As I am new to kubernetes, kind, docker and not much of an expert of networking too, so it takes long time to investigate issues. While I was thinking and searching for solution, it occured to me, that may be I can change the node image again. The original kind cluster was based on node image 1.20, [because 1.21 had issues.](https://github.com/arundeep78/wsl_debian_dev/blob/master/Kind_k8s_Readme.md#test-kind)

* ### Kind cluster with Node image version 1.23

Looking at the [Kind releases](https://github.com/kubernetes-sigs/kind/releases), I noticed that even 1.23 is supported and I used it.

Cluster creation works!
![kind cluster with node image 1.23](kind/images/kind_cluster_1.23.drawio.svg)

* ### Test network in worker node

Need to install `iputils-ping` and `traceroute` package to test it

1. google.com works

    ```zsh
    root@kind-airflow-worker:/ ping google.com
    PING google.com (142.251.39.46) 56(84) bytes of data.
    64 bytes from bud02s38-in-f14.1e100.net (142.251.39.46): icmp_seq=1 ttl=116 time=24.8 ms
    ```

2. How about registry-1.docker.io. It works too!!

    ```zsh
    root@kind-airflow-worker:/# traceroute registry-1.docker.io
    traceroute to registry-1.docker.io (174.129.220.74), 30 hops max, 60 byte packets
    1  172.19.0.1 (172.19.0.1)  0.182 ms  0.010 ms  0.006 ms
    2  172.17.112.1 (172.17.112.1)  0.172 ms  0.408 ms  0.385 ms
    3  192.168.1.1 (192.168.1.1)  2.623 ms  5.489 ms  2.559 ms
    ```

* ### Time to install airflow helm chart now

```zsh
$helm install $RELEASE_NAME apache-airflow/airflow --namespace $NS --debug
install.go:178: [debug] Original chart version: ""
....

You can get Fernet Key value by running the following:

    echo Fernet Key: $(kubectl get secret --namespace ns-airflow rn-airflow-fernet-key -o jsonpath="{.data.fernet-key}" | base64 --decode)

###########################################################
#  WARNING: You should set a static webserver secret key  #
###########################################################

You are using a dynamically generated webserver secret key, which can lead to
unnecessary restarts of your Airflow components.

Information on how to set a static webserver secret key can be found here:
https://airflow.apache.org/docs/helm-chart/stable/production-guide.html#webserver-secret-key
```

**It works!**: Still don't know why the other one does not work

**Lesson**: This is seems to be the way with new style of infrastructure. People just replace the version/number of some file/image and test if it works. If works then fine, if not then try another version/file/chart/yaml or whatever.

It would appear that another layer of administrators/developers have been created who actually find root causes and solutions to when one these images do not work. While the "front facing admnistrators" just try to find which image works and do some little of tweaking by searching while lines in those yaml files to change. Maybe it is OK in the new environment. However, coming from the old setup, I would like to know why my application could not work in a given setup. And maybe that means I need to go to the another level of administrators?

### Additional notes

As I continued to work on it. I found there is some randomness somewhere which caused this network issues. I had issues with version 1.23 as well as 1.20.
I had issues with Docker DNS configured to 8.8.8.8 as well as default entry as well.

However, even when network was working Airflow installation using helm will fail at times. To be specific helm command would fail, but if you check nodes, they were still working and after sometime all will be in running status. Trouble was that I could not log on to Airflow web frontend with standard user credentials.

Reason was that default helm command waits for 5minutes for a job to complete. In my case download of images was taking long time. So helm command would fail and stop after 5 min and would not trigger the user creation job. So I changed the standard airflow installtion command to

```zsh
$helm install $RELEASE_NAME apache-airflow/airflow --namespace $NS --debug --timeout 10m
```

In this case helm would wait for job to complete and trigger the user creation job.

</details>

## Access airflow frontend

Follwing instructions provided by the helm chart installation output or as per instructions on [Airflow Quick Start documentaion](https://airflow.apache.org/docs/helm-chart/stable/quick-start.html), once can login to the Airflow webserver frontend

1. Forward port from kubectl

   ```zsh
   kpf svc/$RELEASE_NAME-webserver 8080:8080 --namespace $NS
   ```

2. Open airflow webserver URL in webbrowser (In Windows) `localhost:8080`
   ![airflow webserver in windows](images/airflow/airflow_webserver.drawio.svg)

## Access Flower dashboard

Follwing instructions provided by the helm chart installation output, one can login to the Airflow webserver frontend

1. Forward port from kubectl

   ```zsh
   kpf svc/$RELEASE_NAME-flower 5555:5555 --namespace $NS
   ```

2. Open Flower dashboard URL in web browser (In Windows) `localhost:5555`
   ![airflow flower dashboard in windows](images/airflow/airflow_flower.drawio.svg)

## Access PostgreSQL DB

1. Forward port from kubectl

   ```zsh
   kpf svc/$RELEASE_NAME-postgresql 5432:5432 --namespace $NS
   ```

2. Connect using preferred DB manager tool. I used DBeaver
   ![Airflow DB connection](images/airflow/airflow_pgsql.drawio.svg)

## Export the WSL image

Export this kind based Airflow image as a reference working image

```powershell
wsl --export deb11kindaf ./wsl_backups/deb11kindaf.tar | tar -czf ./wsl_backups/deb11kindaf.tar.gz ./wsl_backups/deb11kindaf.tar
```

## Airflow with external PostgreSQL DB

This section is based on the [PostgreSQL setup](Postgres_Readme.md). Kind cluster in that configuration setup worker node with node and pod Affinity parameters for Database.

To allow Airflow helm chart to connect with external database in this case the PostgreSQL configured above, I used below files in my `values_custom.yaml` file for Airflow helm chart.

```yaml
# Configuration for postgresql subchart
# Not recommended for production. Disable
postgresql:
  enabled: false

# Airflow database & redis config
data:

  # Otherwise pass connection values in
  metadataConnection:
    user: postgres  # directly entered
    pass: postgres # this is coming from environment variable based on secret
    protocol: postgresql
    host: rn-postgres-postgresql #.default.svc.cluster.local # as configured by postgres helm chart. RN however is not templated now.
    port: 5432
    db: arcticrisk # as configured in postgres helm chart
```

This section provides connection details about the external DB. I know that I have password in plain text in this file. But this was the quickest way. I tried to pass the an evironment variable based on postgres helm chart secret. But realized that Airflow uses a secret which has a connection url based on the above information. As this URL is created at level of helm chart generation, in my awarness, it can use value from another secret inside Kubernetes.

TODO:
It seems if I want to pass a password field based on an existing secret, I would have to change the pod template definition first, so that connection string is build inside kubernetes rather than at helm level. This is what I think. Let's see what I find as I move further.

## Github as DAG repository

So as to save my DAG definitions on github and allow collaboration, I now need to configure Airflow helm chart to synch DAG filepath with github repository.

I updated the below section in the `values_custom.yaml` file for dags to configure github repo.

**NOTE:** At the time of writing (Apr 2022) this helm chart configuration supports out-of-box username and password based configuration for github repo. But github does not support it anymore since Aug 2021. So, unless someone can and wants to configure the base images, I think one needs to use a public repo for this helm chart.

```yaml
dags:
  gitSync:
    enabled: true
    repo: https://github.com/arundeep78/airflow.git
    branch: master
    rev: HEAD
    depth: 1
    # the number of consecutive failures allowed before aborting
    maxFailures: 1
    # subpath within the repo where dags are located
    # should be "" if dags are at repo root
    subPath: "dags"
```

