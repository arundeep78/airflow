# Airflow on Kubernetes(minikube) using official helm chart

NOTE: This procedure is based on [minikube installation of K8s](https://github.com/arundeep78/wsl_debian_dev/blob/master/minikube_k8s_Readme.md). If you do have the WSL image are prepared in that document some extra steps might be required based on our specific situation.

## Create a directory structure for airflow project

Create a directories for airflow project. These directories store configuration files for Helm chart for airflow, any image files that it might need, test DAGs etc. These files can be uploaded to github as needed.

You will follow your own project organization methods. This one I just throught might work for me. We shall see  :)

```zsh
# for main airflow project
mkdir ~/projects/airflow 
# to keep minikube k8s cluster related config files
mkdir ~/projects/airflow/minikube
# to keep airflow helm chart deplyment/installation related files
mkdir ~/projects/airflow/helmcharts 

# Enter in the main project directory and start code for documentations.
# You would use any other tool that you might like for coding/documentation
cd ~/projects/airflow
code .
```

