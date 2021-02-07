# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals


import octoprint.plugin
import os
import flask

import_error = None
try:
    from . import camera_control
except Exception as err:
    import_error = err
    camera_control = None


def format_exception(err):
    tb = err.__traceback__
    return "%s: %s (%s, %s line %s)" % (
        type(err).__name__, str(err), os.path.basename(tb.tb_frame.f_code.co_filename), tb.tb_frame.f_code.co_name, tb.tb_lineno
    )


class WebcamControlPlugin(octoprint.plugin.SettingsPlugin, octoprint.plugin.AssetPlugin, octoprint.plugin.TemplatePlugin, octoprint.plugin.SimpleApiPlugin):
    def __init__(self):
        self.cameras = {}
        self.devices_root = "/dev/v4l/by-id/"

    def get_assets(self):
        return dict(js=["js/webcam_control.js"], css=["css/webcam_control.css"])

    def get_template_configs(self):
        return [
            dict(type="sidebar", name="Webcam Control", template="webcam_control_sidebar.jinja2", custom_bindings=False)
        ]

    def get_settings_defaults(self):
        try:
            devices = os.listdir(self.devices_root)
        except Exception as err:
            devices = {"error": format_exception(err)}
        return {
            "devices": devices
        }

    def get_template_vars(self):
        return {"devices": self._settings.get(["devices"])}

    def get_update_information(self):
        return dict(
            webcam_control=dict(
                displayName="Webcam Control",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="clonesht",
                repo="OctoPrint-WebcamControl",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/clonesht/OctoPrint-WebcamControl/archive/{target_version}.zip"
            )
        )

    def get_camera(self, device, cache=True):
        if device not in self._settings.get(["devices"]):
            raise Exception("Invalid device, not in %s" % self.devices_root)

        if not camera_control:
            raise import_error

        if not cache or device not in self.cameras:
            self.cameras[device] = camera_control.CameraControl(self.devices_root + device)

        return self.cameras[device]

    def is_api_adminonly(self):
        return True

    def get_api_commands(self):
        return {
            "get_controls": ["device"],
            "set_control": ["device", "control_id", "value"]
        }

    def on_api_command(self, command, data):
        if not octoprint.access.permissions.Permissions.ADMIN.can():
            return flask.make_response("Insufficient rights", 403)

        try:
            if command == "get_controls":
                back = self.action_get_controls(data["device"])
            elif command == "set_control":
                back = self.action_set_control(data["device"], data["control_id"], data["value"])
        except Exception as err:
            back = {"error": format_exception(err)}

        return flask.jsonify(back)

    # -- API Commands --

    def action_get_controls(self, device):
        camera = self.get_camera(device, cache=False)
        return camera.getControls()

    def action_set_control(self, device, control_id, value):
        camera = self.get_camera(device)
        return camera.setValue(control_id, value)

__plugin_name__ = "Webcam Control"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = WebcamControlPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
