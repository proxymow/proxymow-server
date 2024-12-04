//classes

class Queue {
	constructor(name, period, callback, errcallback) {
		this.name = name;
		this.callback = callback;
        this.errcallback = errcallback;
		this.period = period;
		this.items = {};
	}//end constructor
	
	add(key, itm) {
		this.items[key] = itm;
		clearTimeout(this.timerId);
		const self = this;
		this.timerId = setTimeout(function() {
			self.update();
		}, this.period);
		return this.size;
	}//end add to queue method
	update() {
		//first clone the queue - so it can continue to be updated
		const clonedQueue = JSON.parse(JSON.stringify(this.items));
		this.clear();
		const self = this;
		for(let id in clonedQueue) {
			const value = clonedQueue[id];
            const idNum = parseInt(id.match(/\d+$/));
            let url = this.name + '.' + idNum;            
            if (isNaN(idNum)) {
                url = id;
            }
			sendData('PUT', 'api', url, value, true, function(resp) {
				if (typeof self.callback !== 'undefined') {
					// requires callback?
					self.callback(resp);		
				}
			}, function(resp) {
                if (typeof self.errcallback !== 'undefined') {
                    // requires callback?
                    self.errcallback(resp);        
                }                
            });	
		}//next item
	}//end update
	clear() {
		this.items = {};
	}//end clear
	// Getter
	get size() {
		return Object.keys(this.items).length;
	}//end getter
}//end queue class

class QueueManager {
	constructor() {
		this.queues = {};
	}//end constructor
	addQueue(name, period, callback) {
		const q = new Queue(name, period, callback);
		this.queues[name] = q;
	}//end add queue
	
	addToQueue(qName, key, itm) {
		const q = this.queues[qName]; 
		q.add(key, itm);
		return q.size;
	}//end add to queue method
	
	clearQueue(qName) {
		const q = this.queues[qName]; 
		q.clear();  				
	}//end clear queue
}//end queue manager class