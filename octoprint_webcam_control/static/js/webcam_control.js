$(function() {
    function WebcamControlViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.controlViewModel = parameters[1];

        self.isDisabled = ko.observable(false);
        self.selectedDevice = ko.observable();
        self.controls = ko.observableArray([]);
        self.output = ko.observable("");

        self.getDevices = ko.pureComputed(function() {
            back = [{"name": "-- Select device --"}];
            devices = self.settingsViewModel.settings.plugins.webcam_control.devices();
            for (var device of devices) {
                back.push({"name": device});
            }
            return back;
        });

        self.onStartupComplete = function() {
            window.plugin_webcam_control = self;
            $("#sidebar_plugin_webcam_control_wrapper > div.accordion-heading > a").prepend("<i class='fa icon-black fa-sliders-h'/>");
            self.sidebar = $("#sidebar_plugin_webcam_control_wrapper #webcam_control");

            self.selectedDevice.subscribe(self.handleDeviceChange);
        };

        self.displayControls = function(controls) {
            var controls_list = []
            for (var key in controls) {
                control = controls[key]
                control.name = key;
                if (control.maximum)
                    control.range = `${control.minimum} - ${control.maximum}, `;
                else
                    control.range = "";
                control.default_value = control.default;
                control.previous_value = control.value;
                control.set_value = ko.observable(control.value);
                control.value = ko.observable(control.value);
                control.error = ko.observable("");
                control.delay_timer = null;
                if (!control.value_names) control.value_names = null;
                controls_list.push(controls[key]);
            }

            if (controls_list.length == 0) {
                self.handleError("No controls found for " + self.device);
            }
            self.controls(controls_list);
        }

        self.handleError = function(error) {
            console.error(error);
            self.output("Error: " + error);
        }

        self.handleDeviceChange = function(item_id) {
            self.controls([]);
            self.output("");
            devices = self.getDevices();
            self.device = devices[item_id]["name"];

            $(".UICLargeSpan").css({position: "", top: ""});

            if (!self.device || item_id == 0) return false;

            $(".UICLargeSpan").css({position: "sticky", top: "20px"});  // Control list can be long, keep webcam picture on the screen

            self.isDisabled(true);
            OctoPrint.simpleApiCommand("webcam_control", "get_controls", {"device": self.device})
                .done(self.displayControls)
                .fail(function () { self.handleError("Unable to get controls") } )
                .always(function () { self.isDisabled(false); });
        }

        self.handleControlChange = function(control, e) {
            if (control.value() == control.set_value()) return false;  // Value not changed
            if (control.delay_timer) return false;  // Value update already scheduled

            control.delay_timer = setTimeout(function() {
                self.doControlChange(control);
            }, 500);
        }

        self.doControlChange = function(control) {
            self.output(`Saving: ${control.name} -> ${control.value()}`)
            OctoPrint.simpleApiCommand("webcam_control", "set_control", {"device": self.device, "control_id": control.control_id, "value": parseInt(control.value())})
                .done(function(res) {
                    if (res.error) {
                        self.output(`Error: ${control.name} -> ${control.value()} (${res.error})`);
                        control.error(res.error);
                    } else {
                        self.output(`Done: ${control.name} -> ${control.value()} (${res})`);
                        control.error("");
                    }
                    control.set_value(control.value());
                })
                .fail(function (res) { self.handleError("Unable to save control") } )
                .always(function (res) {
                    self.isDisabled(false);
                    control.delay_timer = null;
                });
        }

        self.handleControlRender = function(elems, control) {
            // Mouse wheel update fix
            var input_elem = $(elems).find("input")[0];
            input_elem.onwheel = function(e) {
                var target = e.currentTarget;
                setTimeout(function() {
                    control.value(target.value);
                    self.handleControlChange(control, e);
                }, 10);
            }
            input_elem.onkeyup = input_elem.onwheel;
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: WebcamControlViewModel,
        dependencies: ["settingsViewModel", "controlViewModel"],
        elements: ["#sidebar_plugin_webcam_control"]
    });
});
