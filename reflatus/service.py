from reflatus.web import Reflatus
from flask import request, jsonify, render_template
import os

# change to real directory
# used for relative path configuration in config.conf
os.chdir(os.path.dirname(os.path.realpath(__file__)))

app = Reflatus("Reflatus",
               beconfig="./config/config.conf",
               static_folder="./static",
               template_folder="./templates")


@app.route("/")
def index():
    """
    list flows
    """
    flows_list = list()
    url_root = request.url_root
    for flowname in app.flow_map.keys():
        flows_list.append([flowname, "".join([url_root,
                                              "liveflows/",
                                              flowname])])
    return render_template('index.html',
                           flows_list=flows_list)


@app.route("/<server_name>/<flow_name>")
def liveflow(server_name, flow_name):
    """
    show a status graph of a certain flowname
    """
    url_root = request.url_root

    try:
        flow = convert_flow(app.servers_info[server_name].flow_maps[flow_name])
    except KeyError:
        ret_msg = " ".join(["Unable to find Flow <%s> in the" % flow_name,
                            "back-end configuration file.",
                            "Please check the validity of your flow name."])
        return ret_msg
    except Exception as excp:
        ret_msg = " ".join(["Unable to handle Flow <%s> with" % flow_name,
                            "the following message: %s." % excp,
                            "Please contact the back-end administrator."])
        return ret_msg

    return render_template('liveflow.html',
                           servers_info=app.servers_info,
                           flow_name=flow_name,
                           server_name=server_name,
                           flow=flow,
                           url_root=url_root)


@app.route("/flowdata/<server_name>/<flow_name>")
def flowupdated(server_name, flow_name):
    """
    updated json data of a certain flowname
    used by ajax in js
    """

    flow = convert_flow(app.servers_info[server_name].flow_maps[flow_name])
    return jsonify(flow)


def convert_flow(flow):
    """Convert the obj info to dict

    @param flow: a dict contains all jobs info
    """

    newflow = dict()
    for (job_name, job_info) in flow.iteritems():
        newflow[job_name] = job_info.__dict__
    return newflow


if __name__ == "__main__":
    from reflatus.utils import setup_logging
    setup_logging()
    app.run()
