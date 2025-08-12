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