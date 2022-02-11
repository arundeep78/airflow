# Airflow on K8s (Kind) image using official Helm chart

This documentation is based on [offical documentation from airflow](https://airflow.apache.org/docs/helm-chart/stable/quick-start.html). At the time of writing Helm chart version was 1.4.0.

NOTE: This procecude is based on [Kind installation of K8s](https://github.com/arundeep78/wsl_debian_dev/blob/master/Kind_k8s_Readme.md). If you do have the WSL image are prepared in that document some extra steps might be required based on our specific situation.

## Create a directory structure for airflow project

Create a directories for airflow project. These directories store configuration files for Helm chart for airflow, any image files that it might need, test DAGs etc. These files can be uploaded to github as needed.

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

Interestingly, in these issues once can find reference to articles with headlines " **Airflow in Kubernetes in 10 mins**". This IMO is one of the cause of such issues. People are led to beleive that all is just so simple.

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
