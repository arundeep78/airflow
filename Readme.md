# Airflow on K8s image using official Helm chart

This documentation is based on [offical documentation from airflow](https://airflow.apache.org/docs/helm-chart/stable/quick-start.html). At the time of writing Helm chart version was 1.4.0.

Official Airflow documentation recommends Kind for local Kubernetes cluster. In this project I try to use different Kubernetes deployments to install airflow.
In the process, I hope to also learn a little bit of configurations on each of Kubernetes implementations.

* ## [PostgreSQL in Kubernetes](Postgres_Readme.md)
* ## [Airflow in Kind Kubernetes](Airflow_kind_readme.md)
* ## [Airflow in minikube Kubernetes](Airflow_minikube_readme.md)

