"""
Jenkins utils
"""
from jenkinsapi.jenkins import Jenkins
import logging
import xmltodict
from requests.packages import urllib3
from reflatus.utils import ConfigInfo


# disable warnings of urllib3 used by jenkinsapi
urllib3.disable_warnings()
logging.getLogger("requests").setLevel(logging.WARNING)


class JenkinsManager(object):
    """
    a wrapped class to manage jenkins
    """
    log = logging.getLogger('myjenkins.JenkinsManager')

    def __init__(self, baseurl, username, password):
        """
        @param baseurl: the url of jenkins
        @param username: jenkins username
        @param password: jenkins password
        """
        self.baseurl = baseurl
        self.username = username
        self.password = password
        self.server = Jenkins(baseurl=self.baseurl,
                              username=self.username,
                              password=self.password)
        self.log.info("Access Jenkins %s with username: %s" % (self.baseurl,
                                                               self.username))

    def is_job(self, job_name):
        """
        identify the job type
        """
        return True if self.getConfig(job_name).get('project') else False

    def is_flow(self, flow_name):
        """
        identify the flow type
        """
        return True if self.getConfig(flow_name) \
                           .get('com.cloudbees.plugins.flow.BuildFlow') \
            else False

    def getConfig(self, job_name):
        """
        get the config of the job
        jobname/config.xml
        """
        job = self.server.get_job(job_name)
        job_config = xmltodict.parse(job.get_config())
        return job_config

    def getBuild(self, job_name, build_number):
        return self.server.get_job(job_name).get_build(build_number)

    def getCauses(self, job_name, build_number):
        """
        get the cause/upstream job name
        """
        self.log.debug("Get Cause for <%s/%s>" % (job_name,
                                                  build_number))
        build = self.getBuild(job_name, build_number)
        return build.get_causes()

    def getRootCauses(self, job_name, build_number):
        """
        get all the causes/upstream job names
        @return: upstream jobs list starting from the topmost
        """
        self.log.info("Get Root Causes for <%s/%s>" % (job_name,
                                                       build_number))
        causes_list = list()
        cause = self.getCauses(job_name, build_number)

        if len(cause) > 1:
            self.log.error("Multiple causes for %s/%s" % (job_name,
                                                          build_number))
            return None

        upstreamBuild = cause[0].get("upstreamBuild", None)
        if upstreamBuild:
            self.log.debug("Found upstream Build")
            upstream_info = UpstreamInfo(cause[0])
            causes_list.append(upstream_info)
            original_cause = self.getRootCauses(upstream_info.upstreamProject,
                                                upstream_info.upstreamBuild)
            if original_cause:
                causes_list.extend(original_cause)
        else:
            return None

        causes_list.reverse()
        return causes_list if causes_list else None


class UpstreamInfo(ConfigInfo):
    """
    object to markup upstream job
    """
    def __init__(self, data):
        self.upstreamBuild = data["upstreamBuild"]
        self.upstreamProject = data["upstreamProject"]

    def __repr__(self):
        return "<upstream {0.upstreamProject}/{0.upstreamBuild}>".format(self)


if __name__ == "__main__":
    from reflatus.utils import setup_logging
    setup_logging()
    url = "http://localhost:8080"
    username = "admin"
    password = "passw0rd"
    jm = JenkinsManager(url,
                        username,
                        password)
    print jm.getRootCauses("job_one", 2)
    print jm.getRootCauses("flow_demo", 1)
