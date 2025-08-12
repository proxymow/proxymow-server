const tickChar = '&#10004;';

class MonitorPane {

    constructor(monPaneId, ctrlPaneId, fetcher) {

        //capture this
        const self = this;
        this.nullMower = false;
        this.tpId = monPaneId;
        this.ctrlPaneId = ctrlPaneId;
        this.fetcher = fetcher;

        //attach listener to annotations
        const annotates = document.getElementsByClassName('annotate');
        Array.from(annotates).forEach(function(element) {
            element.addEventListener('click', function() {
                self.toggleAnnotation(this);
            });
        });

        //attach listeners to buttons
        const wifiWidget = getWidget(self.tpId, "WIFISTRENGTH");
        wifiWidget.addEventListener('click', function() {
            self.toggleAnnotation('online-annotation');
        });
        const batWidget = getWidget(self.tpId, "BATTERY");
        batWidget.addEventListener('click', function() {
            self.toggleAnnotation('meas-annotation');
        });
        const eyeWidget = getWidget(self.tpId, "FOUND");
        eyeWidget.addEventListener('click', function() {
            self.toggleAnnotation('found-annotation');
        });
        const stopWidget = getWidget(self.tpId, "EMERGENCYSTOP");
        stopWidget.addEventListener('click', function() {
            self.emergencyStop(self);
        });

        this.fetcher.addEventListener('body-available', function(event) {
            //cache for later processors
            self.locatorJson = event.detail.Locator;
            self.driverJson = event.detail.Driver;
            self.curMower = self.driverJson['cur-mower'];
            self.nullMower = (typeof(self.curMower) !== 'undefined' && self.curMower == 'None');
            self.processTelemetryHeader(self, event.detail.Telemetry);
            self.processPoseHeader(self, event.detail.Pose, self.locatorJson);
            self.processDriverHeader(self, self.driverJson);
        });

    }//end constructor

    emergencyStop(self) {

        sendData('PUT', 'api', 'direct-drive', 'stop()');
        const pauseBtn = getWidget(self.ctrlPaneId, "PAUSE");
        pauseBtn.click();

    }//end emergency stop

    processLocatorHeader(self, locJson) {
        const statusWidget = getWidget(self.ctrlPaneId, "NAVIGATIONSTATUS");
        const statusMsg = locJson.essid;
        if (typeof (statusWidget) != 'undefined') {
            if (typeof statusMsg === 'undefined') {
                statusWidget.value = '';
            } else {
                statusWidget.value = statusMsg;
            }//end status available
        }//end widget defined
        else {
            //display metadata ssid elsewhere
            document.getElementById(self.tpId).title = 'essid: ' + statusMsg;
        }//end alt essid

    }//end process locator header

    processTelemetryHeader(self, telJson) {
        //Start with wifi status
        self.processWifiStatus(self, telJson);
        //Battery
        self.processBatteryLevel(self, telJson);
        //Online Annotation
        self.processOnlineAnnotation(self, telJson);
        //Measurement Annotation
        self.processMeasAnnotation(self, telJson);
    }//end process telemetry header

    processPoseHeader(self, poseJson, locatorJson) {
        //Start with X, Y and theta
        self.processCoordinates(self, poseJson);
        //Set Indicator
        self.processFoundIndicator(self, poseJson, locatorJson);
        //Found Annotation
        self.processFoundAnnotation(self, poseJson, locatorJson);
    }//end process pose header

    processDriverHeader(self, headerJson) {
        //Update last cmds
        self.processLastCommands(headerJson);
    }//end process driver header

    processWifiStatus(self, headerJson) {

        const widget = getWidget(self.tpId, "WIFISTRENGTH");
        if (typeof (headerJson) != 'undefined') {
            const rssi = headerJson['rssi'];
            let cssClass = 'wifi-offline';
            if (!self.nullMower && typeof rssi !== 'undefined') {
                cssClass = 'wifi-1';
                if (rssi > -90 && rssi <= -70) {
                    cssClass = 'wifi-2';
                } else if (rssi > -70 && rssi <= -67) {
                    cssClass = 'wifi-3';
                } else if (rssi > -67 && rssi <= 0) {
                    cssClass = 'wifi-4';
                }
            }//end rssi available

            if (widget.classList.length > 0) {
                widget.classList.replace(widget.classList[0], cssClass);
            }//end sufficient classes
        }//end header available
    }//end process wifi status

    processBatteryLevel(self, headerJson) {

        const widget = getWidget(self.tpId, "BATTERY");
        if (typeof (headerJson) != 'undefined' && typeof (headerJson.analogs) != 'undefined') {
            const battPercent = headerJson.analogs[0]*100/1024;
            let cssClass = 'offline';
            if (typeof battPercent !== 'undefined') {
                if (battPercent > 50) {
                    cssClass = 'high';
                } else if (battPercent > 25) {
                    cssClass = 'medium';
                } else if (battPercent >= 0) {
                    cssClass = 'low';
                }
            }//end battPercent available

            if (widget.classList.length > 0) {
                widget.classList.replace(widget.classList[0], cssClass);
            }//end sufficient classes

            //finally set level
            widget.getElementsByTagName('div')[0].style.height = ((battPercent / 1.33) + 25) + '%';

        }//end header available

    }//end process battery percent

    processCoordinates(self, poseJson) {
        const xWidget = getWidget(self.tpId, "ROBOTXM");
        const yWidget = getWidget(self.tpId, "ROBOTYM");
        const tWidget = getWidget(self.tpId, "ROBOTTHETA");
        const compass = getWidget(self.tpId, "COMPASS");
        if (typeof (poseJson) != 'undefined') {
            const xm = poseJson['c_x_m'];
            const ym = poseJson['c_y_m'];
            const thetaDeg = poseJson['t_deg'];
            if (typeof xm !== 'undefined' && xm >= 0) {
                xWidget.value = xm;
            } else {
                xWidget.value = '';
            }
            if (typeof ym !== 'undefined' && ym >= 0) {
                yWidget.value = ym;
            } else {
                yWidget.value = '';
            }
            if (typeof thetaDeg !== 'undefined' && thetaDeg >= 0) {
                tWidget.value = thetaDeg;
                // Copy numerical angle to compass transform style
                if (typeof compass !== undefined && compass != null) {
                    const tx = `rotate(${thetaDeg * -1}deg)`;
                    compass.style.transform = tx;
                    compass.style.visibility = 'visible';
                }
            } else {
                tWidget.value = '';
                compass.style.visibility = 'hidden';
            }
        }//end pose available
    }//end process coordinates

    processFoundIndicator(self, poseJson, locJson) {
        const widget = getWidget(self.tpId, "FOUND");
        let cssClass = 'robot-lost';
        if (typeof (locJson) != 'undefined') {
            if (locJson['best_proj_found']) {
                cssClass = 'robot-found';
            }//end found
        }//end pose avail
        if (widget.classList.length > 0) {
            widget.classList.replace(widget.classList[0], cssClass);
        }//end sufficient classes
    }//end process found indicator

    processOnlineAnnotation(self, telJson) {
        const onlineAnn = document.getElementById('online-annotation');
        const onlineWidget = getWidget(self.tpId, "WIFISTRENGTH");
        if (onlineWidget !== null && onlineAnn !== null && typeof (telJson) != 'undefined') {
            if (self.nullMower || Object.keys(telJson).length == 0) {
                //Offline
                onlineWidget.title = onlineAnn.innerText = 'Mower Offline';
            } else {
                const essid = telJson['essid'];
                const rssi = telJson['rssi'];
                const qual = telJson['wifi_quality'];
                let upt = '';
                if (typeof (telJson['last-update']) !== 'undefined') {
                    upt = secondsToTime(telJson['last-update'] / 1000);
                }
                let last_fetched = '';
                if (typeof (telJson['last-fetch']) !== 'undefined') {
                    const secs = telJson['last-fetch']
                    const tzoffset = (new Date()).getTimezoneOffset() * 60000; //offset in milliseconds
                    last_fetched = new Date((secs * 1000) - tzoffset).toISOString().slice(11, 19);
                }
                let onlineMsg = 'Mower Online@' + essid + '<br />';
                onlineMsg += 'RSSI: ' + rssi + ' [' + qual + ']<br />';
                onlineMsg += 'Last: ' + last_fetched + ' uptime: ' + upt;
                onlineAnn.innerHTML = onlineMsg;
                onlineWidget.title = onlineMsg.split('<br />').join('\r');

            }//end online        
        }//end present
    }//end process online annotation

    processMeasAnnotation(self, telJson) {
        const measAnn = document.getElementById('meas-annotation');
        const batWidget = getWidget(self.tpId, "BATTERY");
        if (batWidget !== null && measAnn !== null && typeof (telJson) != 'undefined') {
            if (self.nullMower || Object.keys(telJson).length == 0) {
                //Offline
                batWidget.title = measAnn.innerText = 'Mower Offline';
            } else {
                const sensors = telJson['sensors'];
                if (typeof sensors !== 'undefined') {
                    let sensList = '';
                    for (const [key, value] of Object.entries(sensors)) {
                        sensList += `${key}: ${value}<br />`;
                    }//end measurement loop
                    measAnn.innerHTML = sensList;
                    batWidget.title = sensList.split('<br />').join('\r');
                }
            }//end online        
        }//end present
    }//end process measurement annotation

   processFoundAnnotation(self, poseJson, locJson) {
        const indWidget = getWidget(self.tpId, "FOUND");
        const foundAnn = document.getElementById('found-annotation');
        if (indWidget !== null && foundAnn !== null && typeof (poseJson) != 'undefined' && typeof (locJson) != 'undefined') {
            if (self.nullMower) {
                let msg = 'Not Found';
                let reason = locJson['failure_reason'];
                if (reason !== null && typeof reason !== 'undefined') {
                    msg += ': ' + reason;
                };
                foundAnn.innerHTML = indWidget.title = msg;
            } else {
                let annMsg = '';
                const elapsed = locJson['run_elapsed_secs'];
                const fps = elapsed > 0 ? 1/elapsed : 0;
                annMsg += 'locate time: {0} secs {1}fps'.format(
                    elapsed.toFixed(3),
                    fps.toFixed(1)
                );
                const confPc = locJson['best_proj_conf_pc'];
                annMsg += '<br />confidence: {0}%'.format(
                    confPc.toFixed(0)
                );
                annMsg += '<br />quality: {0}% from {1} samples'.format(
                    locJson['loc_quality'],
                    locJson['loc_stat_count']
                );
                annMsg += '<br />contour count: {0}/{1}'.format(
                    locJson['fltrd_count'],
                    locJson['cont_count']
                );
                annMsg += '<br />extrapolation incidents: {0}'.format(
                    locJson['extrapolation_incidents']
                );
                foundAnn.innerHTML = annMsg;
                indWidget.title = annMsg.split('<br />').join('\r').replace(tickChar, '*');
            }//end found
        }//end present
    }//end process found annotation

    processLastCommands(headerJson) {

        // Update last n cmds
        let ul = document.getElementById('last-cmds-list');
        if (typeof (headerJson) != 'undefined') {
            let driveCmds1 = headerJson['last_cmds'];
            if (ul !== null && typeof (driveCmds1) !== 'undefined' && driveCmds1.length > 0) {
                // remove all
                while (ul.firstChild) {
                    ul.removeChild(ul.firstChild);
                }
                for (const cmd of driveCmds1) {
                    let li1 = document.createElement("li");
                    li1.appendChild(document.createTextNode(cmd));
                    ul.appendChild(li1);
                }
            }//end ul is defined
        }//end avail
        ul = document.getElementById('last-comp-cmds-list');
        if (typeof (headerJson) != 'undefined') {
            let driveCmds2 = headerJson['last_comp_cmds'];
            if (ul !== null && typeof (driveCmds2) !== 'undefined' && driveCmds2.length > 0) {
                // remove all
                while (ul.firstChild) {
                    ul.removeChild(ul.firstChild);
                }
                for (const cmd of driveCmds2) {
                    let li2 = document.createElement("li");
                    li2.appendChild(document.createTextNode(cmd));
                    ul.appendChild(li2);
                }
            }//end ul is defined
        }//end avail
    }//end process last commands

    processButtonStates(headerJson) {

        const pauseBtn = getWidget(this.ctrlPaneId, "PAUSE");
        const cancelBtn = getWidget(this.ctrlPaneId, "CANCEL");
        const fenceBtn = getWidget(this.ctrlPaneId, "FENCE");
        const routeBtn = getWidget(this.ctrlPaneId, "ROUTE");

        if (typeof (headerJson) != 'undefined') {
            const drivePath = headerJson.path;

            if (typeof drivePath !== 'undefined' &&
                typeof fenceBtn !== 'undefined' &&
                typeof routeBtn !== 'undefined' &&
                typeof pauseBtn !== 'undefined' &&
                typeof cancelBtn !== 'undefined') {

                if (drivePath === null) {
                    fenceBtn.disabled = false;
                    routeBtn.disabled = false;
                    pauseBtn.disabled = true;
                    cancelBtn.disabled = false;
                } else if (drivePath === 'Fence') {
                    fenceBtn.disabled = false;
                    routeBtn.disabled = true;
                    pauseBtn.disabled = false;
                    cancelBtn.disabled = false;
                } else if (drivePath === 'Route') {
                    fenceBtn.disabled = true;
                    routeBtn.disabled = false;
                    pauseBtn.disabled = false;
                    cancelBtn.disabled = false;
                } else if (drivePath === 'Single') {
                    fenceBtn.disabled = true;
                    routeBtn.disabled = true;
                    pauseBtn.disabled = true;
                    cancelBtn.disabled = false;
                }//end

            }//end drive path defined

            if (headerJson.drive_pause) {
                pauseBtn.classList.add("depressed");
            } else {
                pauseBtn.classList.remove("depressed");
            }//end unpausing
            
        }//end avail
    }//end process button states

    toggleAnnotation(annElemOrId) {

        if (typeof (annElemOrId) == 'string') {
            //clicked icon
            const annElem = document.getElementById(annElemOrId);
            const curAnn = document.querySelector('.expose');
            if (curAnn != null && (curAnn.id != annElem.id)) {
                //close other
                curAnn.classList.remove('expose');
            }
            annElem.classList.toggle('expose');
        } else {
            //clicked annotation to close
            annElemOrId.classList.remove('expose');
        }

    }//end toggle annotation

}//end class

function secondsToTime(e) {
    const h = Math.floor(e / 3600).toString().padStart(2, '0'),
        m = Math.floor(e % 3600 / 60).toString().padStart(2, '0'),
        s = Math.floor(e % 60).toString().padStart(2, '0');
    return `${h}:${m}:${s}`;
}