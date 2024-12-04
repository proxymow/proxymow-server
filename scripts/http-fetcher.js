class HttpFetcher {

    constructor(url, refreshRate, useCacheBuster, isFreeRunning) {

        //capture this
        const self = this;
        this.url = url;
        this.refreshRate = refreshRate;
        this.useCacheBuster = useCacheBuster;
        this.isFreeRunning = isFreeRunning;
        this.isPaused = false;

        this.eventTarget = document.createDocumentFragment();

        [
            "addEventListener",
            "dispatchEvent",
            "removeEventListener"
        ].forEach(this.delegate, this);

        if (typeof refreshRate !== 'undefined' && refreshRate > 0) {
            if (typeof isFreeRunning !== 'undefined' && isFreeRunning) {
                //Free Running every n seconds regardless
                this.timerId = setInterval(function() {
                    if (!self.isPaused) {
                        self.refresh();
                    } else {
                        self.fireEvent('fetch-paused', null);
                    }
                }, refreshRate);
            }//end recurring timer
            else {
                self.reschedule();
            }
        }//end auto-refresh

    }//end constructor

    delegate(method) {
        this[method] = this.eventTarget[method].bind(this.eventTarget)
    }

    refresh() {
        let url = this.url;
        if (typeof this.useCacheBuster !== 'undefined' && this.useCacheBuster) {
            url = this.url + new Date().getTime();
        }
        const myRequest = new Request(url, {
          method: 'GET',
          cache: 'no-store'
        });
        let self = this;
        const startTime = performance.now();
        try {
            self.fireEvent('pre-fetch', null);
            fetch(myRequest)
                .then(
                    function(response) {
                        const contentType = response.headers.get("content-type");
                        if (!response.ok) {
                            const elapsedTime = performance.now() - startTime;
                            self.fireEvent('http-error', response.status, elapsedTime);                            
                        }
                        else if (response.status == 204) {
                            const elapsedTime = performance.now() - startTime;
                            self.fireEvent('no-content', response.status, elapsedTime);                            
                        }                        
                        else if (contentType && contentType.indexOf("image/") !== -1) {
                            response.blob()
                                .then(
                                    function(myBlob) {
                                        if (myBlob.size == 0) {
                                            const elapsedTime = performance.now() - startTime;
                                            self.fireEvent('body-unavailable', null, elapsedTime);
                                        } else {
                                            const objectURL = URL.createObjectURL(myBlob);
                                            //++++++ Image available +++++
                                            const elapsedTime = performance.now() - startTime;
                                            self.fireEvent('body-available', objectURL, elapsedTime);
                                        }//end image available
                                    }//end function
                                )//end then
                        } else if (contentType && contentType.indexOf("text/html") !== -1) {
                            response.text()
                                .then(
                                    function(myText) {
                                        if (myText.length == 0) {
                                            const elapsedTime = performance.now() - startTime;
                                            self.fireEvent('body-unavailable', null, elapsedTime);
                                        } else {
                                            const elapsedTime = performance.now() - startTime;
                                            self.fireEvent('body-available', myText, elapsedTime);
                                        }//end image available
                                    }//end function
                                )//end then
                        } else {
                            response.json()
                                .then(
                                    function(myJson) {
                                        if (myJson.length == 0) {
                                            const elapsedTime = performance.now() - startTime;
                                            self.fireEvent('body-unavailable', null, elapsedTime);
                                        } else {
                                            //++++++ Data available +++++
                                            const elapsedTime = performance.now() - startTime;
                                            self.fireEvent('body-available', myJson, elapsedTime);
                                        }//end data available
                                    }//end function
                                )//end then                            
                        }//end json
                        //++++++ Headers available ++++++
                        const elapsedTime = performance.now() - startTime;
                        self.fireEvent('headers-available', response.headers, elapsedTime);
                        self.reschedule();                       
                    }//end function
                )//end then            
                .catch(error => {
                    console.log('Error:', error);
                    const elapsedTime = performance.now() - startTime;
                    self.fireEvent('fetch-error', null, elapsedTime);
                });//end catch
        } catch (err) {
            console.log(err);
            const elapsedTime = performance.now() - startTime;
            self.fireEvent('fetch-error', null, elapsedTime);
        }//end catch
        
    }//end refresh
    
    reschedule() {
        if (typeof this.refreshRate !== 'undefined' && this.refreshRate > 0 && (typeof this.isFreeRunning === 'undefined' || !this.isFreeRunning)) {
            //Periodic every n seconds after completion
            let self = this;
            this.timerId = setTimeout(function() {
                if (!self.isPaused) {
                    self.refresh();
                } else {
                    self.fireEvent('fetch-paused', null);
                    self.reschedule();
                }
            }, self.refreshRate);//end one-shot timer        
        }//end auto-periodic re-request
    }//end reschedule
    
    reset() {
        //clears scheduled timer, immediately refreshes, reschedules
        clearTimeout(this.timerId);
        this.refresh();
        this.reschedule();
    }//end reset

    fireEvent(eventName, eventDetail, elapsedTime) {
        const event = new Event(eventName);
        event.detail = eventDetail;
        event.elapsed = elapsedTime;
        return this.dispatchEvent(event);
    }//end fire event
}//end class