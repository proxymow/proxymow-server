from collections import UserDict


class FixedLengthDict(UserDict):
    '''
        abstract class
    '''
    def __init__(self, length):
        self.length = length
        super().__init__()

    def __setitem__(self, key, value):
        self.data[key] = value
        while len(self.data) > self.length:
            min_key = list(self.data.keys())[0]
            self.data.pop(min_key)

    def latest(self):
        return None if len(self.data) == 0 else self.data[list(self.data.keys())[-1]]

    def penultimate(self):
        return None if len(self.data) <= 1 else self.data[list(self.data.keys())[-2]]

    def antepenultimate(self):
        return None if len(self.data) <= 2 else self.data[list(self.data.keys())[-3]]

    def keys(self):
        return self.data.keys()

    def __repr__(self):
        result = ''
        for k in self.data:
            result += '{0}: => {1}\n'.format(
                k,
                self.data[k].as_public_dict()
            )
        return result


class SnapshotBuffer(FixedLengthDict):
    '''
        buffer for Snapshots
    '''

    def latest_pose(self):
        result = None
        if self.latest() is not None:
            result = self.latest()._pose
        return result

    def penultimate_pose(self):
        result = None
        if self.penultimate() is not None:
            result = self.penultimate()._pose
        return result

    def antepenultimate_pose(self):
        result = None
        if self.antepenultimate() is not None:
            result = self.antepenultimate()._pose
        return result

    def latest_extrap_pose(self):
        result = None
        if self.latest() is not None:
            result = self.latest()._extrapolated_pose
        return result

    def penultimate_extrap_pose(self):
        result = None
        if self.penultimate() is not None:
            result = self.penultimate()._extrapolated_pose
        return result

    def latest_ssid(self):
        result = -1
        if self.latest() is not None:
            result = self.latest().ssid
        return result

    def latest_pose_delta(self):
        delta_pose = None
        if self.latest_pose() is not None and self.penultimate_pose() is not None:
            delta_pose = self.latest_pose() - self.penultimate_pose()
        return delta_pose

    def penultimate_pose_delta(self):
        delta_pose = None
        if self.penultimate_pose() is not None and self.antepenultimate_pose() is not None:
            delta_pose = self.penultimate_pose() - self.antepenultimate_pose()
        return delta_pose
