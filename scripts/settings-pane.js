class SettingsPane {
    
    constructor(tpId, bpId) {

        //capture this
        const self = this;

        this.tpId = tpId;
        this.bpId = bpId;
        this.dirty = false;
        
        this.eventTarget = document.createDocumentFragment();

        [
            "addEventListener",
            "dispatchEvent",
            "removeEventListener"
        ].forEach(this.delegate, this);
        
        //Add Event Handlers
        
        //First locate toolpane...
        let tp = document.getElementById(tpId);
                        
        //then find all check tools
        const checks = tp.querySelectorAll('input[type="checkbox"]');
        for (const c of checks) {
            c.addEventListener('change', function () {
                self.toggle(this);
            }, false);
        }//next check
        
        //then find all select tools
        const selects = tp.getElementsByTagName('select');
        for (const s of selects) {
            s.addEventListener('change', function () {
                self.doSelection(this);
            }, false);
        }//next select
        
        //then find all nudge tools
        const nudgers = tp.querySelectorAll('input[type="number"].widget');
        for (const n of nudgers) {
            n.addEventListener('change', function () {
                self.nudge(this);
            }, false);
        }//next nudger

        //then find all slide tools
        const sliders = tp.querySelectorAll('.tpt-slider input');
        for (const n of sliders) {
            n.addEventListener('change', function () {
                self.slide(this);
            }, false);
        }//next slider
        
        //establish base_line
        this.assembleQueryString();
        this.cache_qs = this.qs;  
        
    }//end constructor
    
    delegate(method) {
        this[method] = this.eventTarget[method].bind(this.eventTarget)
    }

    assembleQueryString() {
        
        let qs = 'tstmp=' + Math.round(new Date().getTime() / 1000);
        const widgets = document.querySelectorAll('.ToolPaneSettings [data-key]');
        widgets.forEach((widget) => {
            const key = widget.dataset.key;
            const dtype = widget.dataset.type;
            let value = widget.value;
            if (value !== null) {
                if (dtype == 'boolean') {
                    value = widget.checked ? 1 : 0;
                }
                qs += '&' + key + '=' + value;
            }//end enabled
        });//next key
        this.qs = qs;
    }//end assemble url
        
   slide(elem) {
    
        //slide slider - keeping nudger in step
        let val = elem.value;
    
        //copy value to other widget
        const nudger = document.getElementById(elem.dataset.peer);
        nudger.value = val;
    
        this.notify();
    
    }//end slide
    
    nudge(elem) {
    
        //nudge input - keeping slider in step
        let val = elem.value;
    
        //copy value to slider?
        const slider = document.getElementById(elem.dataset.peer);
        if (slider) slider.value = val;
        
        this.notify();
    
    }//end nudge
    
    doSelection() {        
        this.notify();
    }//end do selection
    
    notify() {
    
        this.dirty = true;
        this.assembleQueryString();
        
        //fire settings changed event
        this.fireEvent('settings-changed', null);
        
    }//end set value
    
    toggle(elem) {
        //Update dict
        const master = document.getElementById(elem.id.slice(0, -6));
        if (master) {
            master.disabled = !elem.checked;
            let slider = document.getElementById(elem.id.replace('check', 'slide'));
            if (slider) slider.disabled = !elem.checked;
        } 
        this.notify();
    }//end toggle
    
    zoom(slider) {
        const el = document.getElementById(this.imgId);
        const baseWidth = parseInt(el.dataset.width, 10);
        newVal = slider.value * baseWidth;
        el.style.width = newVal + 'px';
    }//end zoom

    clearAllCheckboxes() {
        const checkboxes = document.querySelectorAll('input[type=checkbox]');
        [...checkboxes].map((el) => {
            el.checked = false;
        })
        this.dirty = true;
        this.assembleQueryString(); 
    }//end clear
    
    fireEvent(eventName, eventDetail) {
        const event = new Event(eventName);
        event.detail = eventDetail;
        return this.dispatchEvent(event);
    }//end fire event
}//end class