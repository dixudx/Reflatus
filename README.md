# reflatus

**re**al-time jenkins **fl**ow st**atus** (Standalone Service)

This tool is used to track the `real-time status` of the Jenkins Build Flow. Admittedly, there is already a plugin named [Build Graph View Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Build+Graph+View+Plugin), which computes a graph of related builds starting from the current one, and renders it as a graph.

However, that plugin is full-fledged with no standalone daemon, which is hard to customized and integrated into your own dashboard. Also that plugin cannot fully display the whole flow graph until all the subjobs/pipelines finish. So it is quite hard for developers, testers and operations engineers to maintain/monitor the overall process of the flow.


## What it can NOT do

This tool only has a ***static parser***, which can **NOT** parse the dedicated DSL defined by [build flow](https://wiki.jenkins-ci.org/display/JENKINS/Build+Flow+Plugin). For the reasons, please refer to FAQ.

Then an extra yaml file is needed to ***explicitly*** define the build workflows (aka build pipelines). More info can be seen in the `Configuration` section.


## How to Use it ?

Firstly, you have to install the prerequisite packages.

```shell
$ pip install -r requirements.txt
```

### Configuration

In folder `reflatus/config`, there are two sample configuration files, you need
to copy them and modify accordingly.

```shell
$ cd config
$ cp config.conf.example config.conf
$ cp flows.yaml.example flows.yaml
```

* `config.conf`: an overall configuration file in ***ini*** file format

    In this file, three sections have to be specified.

    * `jenkins`

        The Jenkins **url**, **username** and **password** have to be configured so that the tool can connect to *Jenkins server* to retrieve some detailed information.

    * `zmq`

        You have to firstly install [zmq-event-publisher](https://github.com/openstack-infra/zmq-event-publisher) through `Plugin Manager`.

        This section specifies the [zeromq](http://zeromq.org/) **server name** and **address**.

    * `flows`

        This section specify the build flows configuration **file path**.

* `flows.yaml`: defines build flows' structure in ***yaml*** file format

    Of course, this filename can be renamed. But You have to modify it accordingly in `section flows` of `config.conf`.

    For a group of jobs that you may reuse in other build flows, you can ***label*** them as a new fake build flow, like `Destroy VMs` in the sample `flows.yaml`.

    **Important Notice**: For a job/pipeline that will be triggered several times with some `triggered parameters`, you have to explicitly add an **identifier** to distinguish them, such as `Build_Zenith_VMs`.


### Start the service

To start your service, run the following command:

```shell
$ python service.py
```


## FAQ

* Why not adding/using a parser to handle the dedicated DSL defined by [build flow](https://wiki.jenkins-ci.org/display/JENKINS/Build+Flow+Plugin) ?

    If so, there is no need to manually add an extra yaml file. Actually it will become quite complex to implement this feature. Regardless of the complicated build flow combinations, the name of a build job/pipeline can be dynamically acquired by `triggered parameters`, `environment variables` or an `explicit name`. This also applies to build job/pipeline parameters. These all adds more workloads and complexity to this tool. It is for this consideration that I discard this feature.
