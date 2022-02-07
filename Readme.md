# Airflow on K8s (Kind) image using official Helm chart

This documentation is based on [offical documentation from airflow](https://airflow.apache.org/docs/helm-chart/stable/quick-start.html). At the time of writing Helm chart version was 1.4.0.

NOTE: This procecude is based on [Kind installation of K8s](Kind_k8s_Readme.md). If you do have the WSL image are prepared in that document some extra steps might be required based on our specific situation.

## Create a directory for airflow project

Create a directory for airflow project. This directory stores configuration files for Helm chart for airflow, any image files that it might need, test DAGs etc. This directory can be uploaded to github as needed.

```zsh
mkdir ~/projects/airflow
```

## Create a config.yaml file for kind cluster

Create a config.yaml file to creare a kind cluster. This cluster will be used to deploy Airflow using Helm chart.

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
kind create cluster --config=config.yaml                                              ─╯
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