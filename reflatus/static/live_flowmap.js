function drawflow(){

    // Set up zoom support
    var svg = d3.select("svg"),
        inner = svg.select("g"),
        zoom = d3.behavior.zoom().on("zoom", function() {
            inner.attr("transform", "translate(" + d3.event.translate + ")" +
                    "scale(" + d3.event.scale + ")");
            });
    svg.call(zoom);

    var render = new dagreD3.render();

    // function to format string
    String.prototype.format = function()
    {
       var content = this;
       for (var i=0; i < arguments.length; i++)
       {
            var replacement = '{' + i + '}';
            content = content.replace(replacement, arguments[i]);  
       }
       return content;
    };

    function draw() {
        // Left-to-right layout
        var g = new dagreD3.graphlib.Graph();
        g.setGraph({
            nodesep: 50,
            ranksep: 20,
            rankdir: "TD",
            marginx: 20,
            marginy: 20
            });

        for (var id in jobs) {
            var job = jobs[id];
            var className = "stopped";
            if (job.status) {
                className = job.status;
                if (className == "running") {
                    className += " warn";
                }
            }

            var html = "<div>";
            html += "<span class=status></span>";
            html += "<span class=name>"+job.name+"</span>";

            if (job.build) {
                html += "<span class=buildurl><a href='{0}'>#{1}</a></span>".format(job.build.full_url, job.build.number);

                if (job.duration) {
                    html += "<span class=buildurl>{0}sec</span>".format(job.duration);
                    }

                }

            html += "</div>";
            g.setNode(id, {
                labelType: "html",
                label: html,
                rx: 5,
                ry: 5,
                padding: 0,
                class: className
                });

            if (job.previous) {
                var jp_len = job.previous.length
                while (jp_len--) {
                    g.setEdge(job.previous[jp_len], id, {
                        width: 40
                        });
                    }
                }
            }

        inner.call(render, g);

        // Zoom and scale to fit
        var zoomScale = zoom.scale();
        var graphWidth = g.graph().width + 80;
        var graphHeight = g.graph().height + 40;
        var width = parseInt(svg.style("width").replace(/px/, ""));
        var height = parseInt(svg.style("height").replace(/px/, ""));
        zoomScale = Math.min(width / graphWidth, height / graphHeight);
        var translate = [(width/2) - ((graphWidth*zoomScale)/2), (height/2) - ((graphHeight*zoomScale)/2)];
        zoom.translate(translate);
        zoom.scale(zoomScale);
        zoom.event(d3.select("svg"));
        }

    // Do some status updates
    setInterval(function() {
        //Get some updated values from the server
        $.getJSON(url_root + 'flowdata/{0}/{1}'.format(server_name, flow_name),  // At this URL
                  {},                         // With no extra parameters
                  function(data) {
                      // Update the graph
                      if (jobs!=data) {
                          jobs = data;
                          draw();
                      }
                  });
        }, 5000);
    draw();
    }
