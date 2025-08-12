import numpy as np

class SightingCluster():
    '''
        Represents a cluster of sightings in the same place
    '''
    

    def __init__(self, threshold):
        '''
            constructor
        '''
        self.threshold = threshold
        self.pose_tuples = []
        self.mean_pose_x = None
        self.mean_pose_y = None
        
    def add(self, p):
        self.pose_tuples.append((round(p[0], 3), round(p[1], 3), int(p[2])))
        (self.mean_pose_x, self.mean_pose_y, _) = np.mean(self.pose_tuples, axis=0)
        
    def accept(self, p):
        result = False
        if self.mean_pose_x is None:
            self.add(p)
            result = True            
        elif np.hypot(p[0] - self.mean_pose_x, p[1] - self.mean_pose_y) <= self.threshold:
            self.add(p)
            result = True
        return result
    
    @property
    def count(self):
        return len(self.pose_tuples)
            
        
    def __repr__(self):
        return 'Num Entries: {} {}, ({:.2f}, {:.2f})'.format(
            self.count, 
            self.pose_tuples if self.count < 10 else '[...]', 
            self.mean_pose_x, 
            self.mean_pose_y
            )