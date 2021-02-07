# Install: sudo apt install v4l-utils
#
# Based on:
# - https://github.com/azeam/camset/blob/master/camset/camset.py
# - https://www.raspberrypi.org/forums/viewtopic.php?t=117268

import os
if __name__ == "__main__":
    from python3_v4l2 import v4l2  # Python3 compatible fork from https://github.com/aspotton/python3-v4l2
else:
    from .python3_v4l2 import v4l2
import fcntl
import time


class CameraControl:
    def __init__(self, path):
        self.path = path
        self.vd = None
        self.encoding = "utf-8"

    def openVd(self):
        return open(self.path, 'rb+', buffering=0)

    def getVd(self):
        if not self.vd:
            self.vd = self.openVd()
        return self.vd

    def getControls(self):
        vd = self.getVd()
        qctrl = v4l2.v4l2_queryctrl()
        vctrl = v4l2.v4l2_control()
        mctrl = v4l2.v4l2_querymenu()

        qctrl.id = v4l2.V4L2_CID_BASE
        mctrl.index = 0

        back = {}
        type_names = {1: "int", 2: "bool", 3: "menu"}

        for x in range(1000):
            try:
                fcntl.ioctl(vd, v4l2.VIDIOC_QUERYCTRL, qctrl)
            except OSError:
                break

            """if qctrl.flags and v4l2.V4L2_CTRL_FLAG_DISABLED != 0:
                continue"""

            vctrl.id = qctrl.id
            fcntl.ioctl(vd, v4l2.VIDIOC_G_CTRL, vctrl)

            control = {}
            name = str(qctrl.name, self.encoding)
            back[name] = control

            control["control_id"] = qctrl.id
            control["type"] = qctrl.type
            control["type_name"] = type_names.get(qctrl.type, "unknown")

            control["maximum"] = qctrl.maximum
            control["minimum"] = qctrl.minimum
            control["step"] = qctrl.step
            control["flags"] = qctrl.flags
            control["default"] = qctrl.default_value
            control["value"] = vctrl.value

            if qctrl.type == 3:  # is menu
                control["value_names"] = {}
                while mctrl.index <= qctrl.maximum:
                    mctrl.id = qctrl.id
                    try:  # needed because sometimes index 0 doesn't exist but 1 does
                        fcntl.ioctl(vd, v4l2.VIDIOC_QUERYMENU, mctrl)
                    except OSError:
                        mctrl.index += 1
                        continue

                    value_name = str(mctrl.name, self.encoding)
                    control["value_names"][value_name] = mctrl.index
                    mctrl.index += 1

            index = qctrl.id
            qctrl = v4l2.v4l2_queryctrl()
            qctrl.id = index

            qctrl.id |= v4l2.V4L2_CTRL_FLAG_NEXT_CTRL
        return back

    def setValue(self, control_id, value):
        vd = self.getVd()
        vctrl = v4l2.v4l2_control()
        vctrl.id = control_id
        vctrl.value = value
        fcntl.ioctl(vd, v4l2.VIDIOC_S_CTRL, vctrl)
        return "ok"


if __name__ == "__main__":
    import pprint

    device = "/dev/v4l/by-id/" + os.listdir("/dev/v4l/by-id/")[-1]
    s = time.time()
    camera = CameraControl(device)
    time_connect = time.time() - s

    s = time.time()
    controls = camera.getControls()
    time_query = time.time() - s

    pprint.pprint(controls)

    value_before = camera.getControls()["Brightness"]["value"]
    s = time.time()
    camera.setValue(controls["Brightness"]["control_id"], 0)
    time_set = time.time() - s

    assert camera.getControls()["Brightness"]["value"] == 0

    camera.setValue(controls["Brightness"]["control_id"], value_before)
    assert camera.getControls()["Brightness"]["value"] == value_before

    print("Time connect: %.3fs, query: %.3fs, set: %.3fs" % (time_connect, time_query, time_set))
