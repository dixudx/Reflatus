"""
load/parse flow yaml file
"""
import yaml
import logging
from retflatus.utils import ConfigInfo

class Serial(list):
    """
    used to mark up serial jobs
    """
    def __str__(self):
        return 'Serial(%s)' % super(Serial, self).__str__()


class Parallel(list):
    """
    used to mark up parallel job
    """
    def __str__(self):
        return 'parallel(%s)' % super(Parallel, self).__str__()


class FlowConfig(ConfigInfo):
    def __repr__(self):
        return "<Flow {0.name}>".format(self)


class JobConfig(ConfigInfo):
    def __repr__(self):
        return "<Job {0.name} 0x{1:x}>".format(self, id(self))


class Loader(object):
    """
    Read and reshape conf
    """
    log = logging.getLogger('loader.Loader')

    def __init__(self, path):
        """
        @param path: the path of the yaml file
        """
        self.path = path
        self.original_data = None

    def getConfig(self):
        self.read()
        return self.conf.reshaped_flows, self.conf.flows_map

    def read(self):
        self.log.info("Read conf file %s" % self.path)
        self._read()
        self.reshape()
        self.getMap()

    def _read(self):
        """
        read the native conf file into a well-constructed format
        """
        self.original_data = yaml.load(open(self.path))
        self.conf = ConfigInfo()
        self.conf.flows = {}
        flows = self.original_data.get('flows', None)

        if not flows:
            return None

        for flow in flows:
            f = FlowConfig()
            f.name = flow['name']

            if f.name in self.conf.flows.keys():
                self.log.warning(" ".join(["There already exists a same flow",
                                           "name <%s> in your" % f.name,
                                           "configuration file."]))
                self.log.warning(" ".join(["If you do want to override it,",
                                           "please ignore this warning"]))

            f.label = flow.get('label', False)
            if f.label:
                labeledBy = f.name
            else:
                labeledBy = None
            f.jobs = self._read_jobs(flow.get('jobs'), labeledBy)
            self.conf.flows[f.name] = f

    def _read_jobs(self, jobs, labeledBy=None):
        """
        read jobs info
        """
        jobs_list = Serial()
        for job in jobs:
            job_type = job.keys()[0]

            if job_type == "serial":
                job_list = Serial()
                subjobs = job.get('serial')

            if job_type == "parallel":
                job_list = Parallel()
                subjobs = job.get('parallel')

            for subjob in subjobs:
                sj = JobConfig()
                sj.name = subjob.get('name')
                sj.description = subjob.get('description', None)
                sj.label = subjob.get('label', False)
                sj.identifier = subjob.get('identifier', None)
                sj.labeledBy = labeledBy
                job_list.append(sj)

            jobs_list.append(job_list)
        return jobs_list

    def reshape(self):
        """
        substitute and remove labeled flows
        """
        flows = self.conf.flows
        reshaped_flows = {}
        for (flow_name, flow_info) in flows.iteritems():
            if flow_info.getattr('label'):
                continue
            f = FlowConfig()
            f.name = flow_name
            f.jobs = self._reshape(flow_name)
            reshaped_flows[f.name] = f
        self.conf.reshaped_flows = reshaped_flows

    def _reshape(self, flow_name):
        """
        TBD: only support flows with single serial or parallel label
        """
        try:
            jobs = self.conf.flows[flow_name].jobs
            reshaped_jobs = Serial()
            for job in jobs:

                job_serial = self.is_serial(job)
                if job_serial:
                    job_list = Serial()
                else:
                    job_list = Parallel()

                for subjob in job:
                    if subjob.getattr('label'):
                        labeled_jobs = self.conf.flows[subjob.name].jobs
                        if len(labeled_jobs) == 1:
                            labeled_job = labeled_jobs[0]
                            labeled_job_serial = self.is_serial(labeled_job)

                            if job_serial == labeled_job_serial:
                                job_list.extend(labeled_job)
                            else:
                                job_list.append(labeled_job)

                        else:
                            self.log.error(" ".join(["Unsupported Structure.",
                                                     "Will support later."]))
                            return None
                    else:
                        job_list.append(subjob)

                reshaped_jobs.append(job_list)
            return reshaped_jobs
        except Exception, excp:
            self.log.error("Unable to reshape flow %s" % flow_name)
            self.log.error(excp)
            return None

    def getMap(self):
        """
        Generate flow map used for plotting in the front-end
        """
        flows = self.conf.reshaped_flows
        flow_map = dict()
        for (flow_name, flow_info) in flows.iteritems():
            flow_map[flow_name] = self.generateMap(flow_info.jobs)
        self.conf.flows_map = flow_map

    def generateMap(self, jobs):
        """
        Generate map through jobs list
        """
        return self._generateMap(jobs)[0]

    def _generateMap(self, jobs, previous=None):

        jobs_map = dict()
        jobs_serial = self.is_serial(jobs)

        if not jobs_serial:
            previous_list = list()

        for job in jobs:
            if not isinstance(job, JobConfig):
                (job_map, subprevious) = self._generateMap(job,
                                                           previous)
                jobs_map.update(job_map)

                if jobs_serial:
                    previous = subprevious
                else:
                    previous_list.extend(subprevious)

                continue

            if previous:
                job.previous = previous

            job_id = str(job)
            jobs_map[job_id] = job
            if jobs_serial:
                previous = [job_id]
            else:
                previous_list.append(job_id)

        if not jobs_serial:
            previous = previous_list

        return jobs_map, previous

    def is_serial(self, job):
        """
        check whether the job is a serial job
        """
        if isinstance(job, Serial):
            return True
        return False

    def is_parallel(self, job):
        """
        check whether the job is a parallel job
        """
        if isinstance(job, Parallel):
            return True
        return False


if __name__ == "__main__":
    from retflatus.utils import setup_logging
    setup_logging()
    filepath = './conf/flows.yaml'
    c = Loader(filepath)
    d = c.getConfig()
    print d
