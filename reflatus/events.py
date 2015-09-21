"""
This events.py focuses on listening and handling events
"""
import zmq
import threading
from six.moves import queue as Queue
from reflatus.utils import StoppedException
import logging
import json
from abc import ABCMeta, abstractmethod
import re


STATUS_MAP = {"SUCCESS": "success",
              "FAILURE": "failure",
              "ABORTED": "aborted"
              }


class ZMQListener(threading.Thread):
    """
    a wrapped class to listen zmq events from Jenkins
    """
    log = logging.getLogger('events.ZMQListener')

    def __init__(self, name, addr, jenkinsmgr, flows):
        """
        @param name: the name of the zmq
        @param addr: the address of the zmq
        @param jenkinsmgr: JenkinsManager instance
        @param flows: flows object
        """
        threading.Thread.__init__(self, name=name)
        self.addr = addr
        self.name = name
        self._context = zmq.Context()
        self.socket = self._context.socket(zmq.SUB)
        self._stopped = False
        self.handler = EventsHandler('%s-handler' % self.name,
                                     jenkinsmgr,
                                     flows)

    def run(self):
        self._setup_socket()
        self.handler.start()
        self.log.debug('ZMQListenner %s Starts Listening' % self.name)
        while not self._stopped:
            event = self.socket.recv().decode('utf-8')
            self.handler.submitEvent(event)
            self.log.debug(event)

    def stop(self):
        self._stopped = True
        if self._context:
            self.log.debug('ZMQListenner %s Stops Listening' % self.name)
            self._context.destroy()

    def _setup_socket(self):
        self.log.debug('Setup Socket for ZMQListenner %s' % self.name)
        self.socket.connect(self.addr)
        self.socket.setsockopt(zmq.SUBSCRIBE, '')


class EventsHandler(threading.Thread):
    """
    events handler
    """
    log = logging.getLogger("events.EventsHandler")

    def __init__(self, name, jenkinsmgr, flows):
        threading.Thread.__init__(self, name=name)
        self.queue = Queue.Queue()
        self.lock = threading.Lock()
        self.name = name
        self.jenkinsmgr = jenkinsmgr
        self.flows = flows
        self._stopped = False

    def run(self):
        self.log.debug('Handler %s Starts Handling Events' % self.name)
        while not self._stopped:
            event = self.queue.get()
            if not event:
                continue
            self.handle_event(event)

    def stop(self):
        self._stopped = True
        self.queue.put(None)

    def submitEvent(self, event):
        if self._stopped:
            raise StoppedException("Handler %s is no longer running"
                                   % self.name)
        self.queue.put(event)

    def handle_event(self, event):
        pattern = re.compile(r"(on\w+) (\{.*\})", re.DOTALL)
        topic, data = pattern.match(event).groups()

        if topic == 'onStarted':
            self._handle_started_event(data)
        elif topic == 'onCompleted':
            pass
        elif topic == 'onFinalized':
            self._handle_finalized_event(data)

    def _handle_started_event(self, data):
        """
        handle started event
        """
        event_thread = StartedEventThread(data,
                                          self.jenkinsmgr,
                                          self.flows,
                                          self.lock)
        event_thread.start()
        if event_thread.isrootflow:
            self.log.debug("Waiting for cleanup.")
            event_thread.join()

    def _handle_finalized_event(self, data):
        """
        handle finalized event
        """
        event_thread = FinalizedEventThread(data,
                                            self.jenkinsmgr,
                                            self.flows,
                                            self.lock)
        event_thread.start()


class EventThread(threading.Thread):
    """
    thread to handle single event
    """
    __metaclass__ = ABCMeta
    log = logging.getLogger("events.EventThread")

    def __init__(self, data, jenkinsmgr, flows, lock):
        self.data = json.loads(data)
        super(EventThread, self).__init__(name=self.data["name"])
        self.name = self.data["name"]
        self.build = self.data["build"]
        self.jenkinsmgr = jenkinsmgr
        self.flows = flows
        self.lock = lock

    @abstractmethod
    def run(self):
        pass

    def getCauses(self):
        """
        get the causes of a certain build
        @return: causes list that containing upstream build names
                 None for empty list
        """
        return self.jenkinsmgr.getRootCauses(self.name,
                                             self.build["number"])

    @property
    def isflow(self):
        """
        identify whether the event is a flow event
        @return: True or False
        """
        if not hasattr(self, "_isflow"):
            self._isflow = self.jenkinsmgr.is_flow(self.name)
        return self._isflow

    @property
    def isrootflow(self):
        """
        identify whether the event is a root flow event
        """
        if not hasattr(self, "_isrootflow"):
            if self.isflow and not self.causes:
                self._isrootflow = True
            else:
                self._isrootflow = False
        return self._isrootflow

    @property
    def causes(self):
        if not hasattr(self, "_causes"):
            self._causes = self.getCauses()
        return self._causes

    @property
    def status(self):
        """
        event status
        """
        if not hasattr(self, "_status"):
            self._status = self._getStatus()
        return self._status

    @abstractmethod
    def _getStatus(self):
        """
        get the status from the event
        """
        pass

    def checkEventOutdated(self):
        """
        check whether the job event is outdated
        only need to check for job/subflow event
        @return: True for outdated, otherwise False
        """
        self.log.debug("check whether Event <%s> is out-dated." % self.name)
        outdated_msg = "The Event <%s> is out-dated. Ignore it." % self.name

        if self.isrootflow:
            flow = self.flows.get(self.name, None)
            if not flow:
                # return True for None
                self.log.debug(" ".join(["Unable to find Flow",
                                         "<%s> in" % self.name,
                                         "configuration file"]))
                return True

            new_buildno = int(self.build["number"])
            try:
                # to avoid missing attribute or number info
                current_buildno = int(flow.build["number"])
            except:
                return False

            if new_buildno < current_buildno:
                self.log.debug(outdated_msg)
                return True
            return False
        else:
            upstream_flow = self.causes[0]
            upstream_flowname = upstream_flow.upstreamProject
            upstream_flowno = upstream_flow.upstreamBuild
            self.log.info("upstream %s: %s" % (upstream_flowname,
                                               upstream_flowno))
            try:
                current_flow = self.flows.get(upstream_flowname)
                current_flowno = current_flow.build["number"]
                self.log.info("current %s: %s" % (upstream_flowname,
                                                  current_flowno))
            except:
                self.log.error("Missing Flow <%s> Info." % upstream_flowname)
                return False
            if upstream_flowno < current_flowno:
                self.log.debug(outdated_msg)
                return True
            else:
                return False

    def updateStatus(self):
        """
        update Event status
        """
        if self.causes:
            # subflows or jobs
            self._updateJobStatus()
        else:
            # no causes jobs
            if not self.isflow:
                self.log.debug("Job <%s> has no upstream flow." % self.name)
                return

            # uppermost flow
            self._updateFlowStatus()

    def _updateJobStatus(self):
        """
        update job status
        """
        upstream_flow = self.causes[0]
        upstreamProject = upstream_flow.upstreamProject

        try:
            jobs = self.flows[upstreamProject].jobs
        except KeyError:
            self.log.error(" ".join(["Unable to find Job",
                                     "<%s>'s upstream" % self.name,
                                     "Project <%s>" % upstreamProject,
                                     "in the configuration file."]))
            return
        except AttributeError:
            self.log.error(" ".join(["Job <%s>'s upstream" % self.name,
                                     "Project <%s> has" % upstreamProject,
                                     "no jobs in the",
                                     "configuration file."]))
            return

        event_jobs = self._findJobs(jobs)
        if not event_jobs:
            return

        with self.lock:
            self.log.debug("Job <%s> acquires the lock" % self.name)
            # check outdated
            if self.checkEventOutdated():
                return

            # update status
            parameters = self.build.get("parameters", None)
            for event_job in event_jobs:
                identifiers = event_job.identifier
                if self._isMatched(identifiers, parameters):
                    event_job.build = self.build
                    event_job.status = self.status

                    self.log.debug(" ".join(["Successfully Update Job",
                                             "<%s> status" % self.name
                                             ]))
                    break

            else:
                self.log.error(" ".join(["No matched Job <%s> " % self.name,
                                         "in configuration file"]))

    def _updateFlowStatus(self):
        """
        update flow status
        """
        with self.lock:
            self.log.debug("Flow <%s> acquires the lock" % self.name)
            flow = self.flows.get(self.name, None)
            if flow:
                if self.checkEventOutdated():
                    return
                self._cleanupFlowStatus()
                flow.build = self.build
                flow.status = self.status
                self.log.debug(" ".join(["Successfully Update Flow",
                                         "<%s> status" % self.name
                                         ]))
            else:
                self.log.debug(" ".join(["Unable to find Flow",
                                         "<%s> in" % self.name,
                                         "configuration file"]))

    def _cleanupFlowStatus(self):
        """
        cleanup the build status and info
        Mainly for "STARTED" event
        """
        pass

    def _findJobs(self, jobs):
        """
        find jobs that matches job_name
        @param jobs: the jobs config
        @return: jobs list
        """
        jobs_list = list()

        if not hasattr(jobs, "__iter__"):
            if jobs.name == self.name:
                jobs_list.append(jobs)
                return jobs_list
            return None

        for job in jobs:
            job_list = self._findJobs(job)
            if job_list:
                jobs_list.extend(job_list)

        return jobs_list if jobs_list else None

    def _isMatched(self, identifiers, parameters):
        """
        check whether the job's identifiers match job's triggered parameters
        """
        if identifiers is None or not parameters:
            return True

        flag = False
        for (key, value) in identifiers.iteritems():
            if value != parameters.get(key):
                break
        else:
            flag = True

        return flag


class StartedEventThread(EventThread):
    log = logging.getLogger("events.StartedEventThread")

    def _getStatus(self):
        return "running"

    def _cleanupFlowStatus(self):
        flow = self.flows.get(self.name, None)
        try:
            jobs = flow.jobs
        except AttributeError:
            self.log.error(" ".join(["Flow <%s> has" % self.name,
                                     "no jobs in the",
                                     "configuration file."]))
            return
        flow.build = None
        flow.status = None
        jobs_list = self._getJobsList(jobs)
        for job in jobs_list:
            job.build = None
            job.status = None
        self.log.debug("Successfully cleanup all the downstream jobs.")
        return

    def _getJobsList(self, jobs):
        """
        get jobs list from jobs config
        @param jobs: the jobs config
        @return: jobs list
        """
        jobs_list = list()

        if not hasattr(jobs, "__iter__"):
            jobs_list.append(jobs)
            return jobs_list

        for job in jobs:
            job_list = self._getJobsList(job)
            if job_list:
                jobs_list.extend(job_list)

        return jobs_list if jobs_list else None

    def run(self):
        self.log.info("Start to Update Flow/Job <%s> Status" % self.name)
        self.updateStatus()


class FinalizedEventThread(EventThread):
    log = logging.getLogger("events.FinalizedEventThread")

    def _getStatus(self):
        status = STATUS_MAP[self.build["status"]]
        return status

    def run(self):
        self.log.info("Start to Update Flow/Job <%s> Status" % self.name)
        self.updateStatus()

if __name__ == "__main__":
    from reflatus.utils import setup_logging
    setup_logging()
    zmql = ZMQListener('local_zmq', 'tcp://localhost:8888', None, None)
    zmql.start()
