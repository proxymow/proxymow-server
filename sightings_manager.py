from sighting_cluster import SightingCluster

class SightingsManager():
    '''
        Represents a list of sighting_cluster(s)
    '''
    

    def __init__(self, threshold):
        '''
            constructor
        '''
        self.threshold = threshold
        self.sighting_clusters = []
        
    def add(self, p):
        if len(self.sighting_clusters) == 0:
            acc = False
        for sc in self.sighting_clusters:
            acc = sc.accept(p)
            if acc:
                # print('accepted')
                # print(sc)
                break
        if not(acc):
            # print('new cluster')
            sc = SightingCluster(self.threshold)
            self.sighting_clusters.append(sc)
            sc.add(p)
            # print(sc)
        
    @property
    def count(self):
        return len(self.sighting_clusters)
            
        
    def __repr__(self):
        return 'Num Sightings: {} {}'.format(self.count, self.sighting_clusters)

if __name__ == '__main__':
    '''
        Class Tests
    '''
    threshold = 0.1 # m
    mgr = SightingsManager(threshold)
    p1 = (3.1, 2.1, 0)
    p2 = (3.15, 2.15, 30)
    p3 = (3.0, 2.0, 60)
    p4 = (3.125, 2.125, 90)
    p5 = (4.0, 5.0, 180)
    p6 = (3.1, 2.1, 270)
    poses = [p1, p2, p3, p4, p5, p6]
    
    for p in poses:
        print('adding', p)
        mgr.add(p)
    print(mgr)