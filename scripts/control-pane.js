class ControlPane {

    constructor(tpId, fetcher) {

        //capture this
        const self = this;
        
        this.tpId = tpId;
        this.fetcher = fetcher;
        
        //then locate button constants        
        this.btns = window[tpId].TOOLS;
        
        //disable any driving buttons
        const btnValArr = Object.keys(this.btns).map(key => this.btns[key]);
        //remove any buttons that never need disabling...
        this.allBtns = btnValArr.reduce((partialSum, a) => partialSum + a, 0);
        this.disabMask =  this.btns.CUTTER1ENABLED |
                          this.btns.CUTTER2ENABLED |
                          this.btns.ROBOTSPEED | 
                          this.btns.DIRECTCOMMAND |
                          this.btns.DRIVE |
                          this.btns.ROUTE |
                          this.btns.PAUSE |
                          this.btns.STEP |
                          this.btns.SKIP;
        enableToolpane(self.tpId, this.allBtns ^ this.disabMask);
        
        //attach listeners to buttons
        const robotSelectWidget = getWidget(self.tpId, "CURRENTMOWER");
        if (typeof(robotSelectWidget) != 'undefined') {
            robotSelectWidget.dataset.changed = "false";
            robotSelectWidget.addEventListener('change', function() {
                robotSelectWidget.dataset.changed = "true";
                setTimeout(function() {
                            robotSelectWidget.dataset.changed = "false";
                            }, 5000);
                sendData('PUT', 'api', 'current.mower', this.value, true, function() {location.reload(true)}); 
            });
        }
        const speedSelectWidget = getWidget(self.tpId, "ROBOTSPEED");
        if (typeof(speedSelectWidget) != 'undefined') {
            speedSelectWidget.addEventListener('change', function() {
                speedSelectWidget.dataset.changed = "true";
                sendData('PUT', 'api', 'set_speeds', this.value, true);
            });
        }
        const cutSlideWidget1 = getWidget(self.tpId, "CUTTER1ENABLED");
        if (typeof(cutSlideWidget1) != 'undefined') {
            cutSlideWidget1.addEventListener('click', function() {
                self.switchCutter(1);    
            });
        }
        const cutSlideWidget2 = getWidget(self.tpId, "CUTTER2ENABLED");
        if (typeof(cutSlideWidget2) != 'undefined') {
            cutSlideWidget2.addEventListener('click', function() {
                self.switchCutter(2);    
            });
        }
        const enrolWidget = getWidget(self.tpId, "ENROL");
        if (typeof(enrolWidget) != 'undefined') {
            enrolWidget.addEventListener('click', function() {
                self.enrolHotSpot(); 
            });
        }
        const rebootWidget = getWidget(self.tpId, "REBOOT");
        if (typeof(rebootWidget) != 'undefined') {
            rebootWidget.addEventListener('click', function() {
                self.reboot();
            });
        }
        const shutdownWidget = getWidget(self.tpId, "SHUTDOWN");
        if (typeof(shutdownWidget) != 'undefined') {
            shutdownWidget.addEventListener('click', function() {
                self.shutdown();
            });
        }
        const directWidget = getWidget(self.tpId, "DIRECTCOMMAND");
        if (typeof(directWidget) != 'undefined') {
            directWidget.addEventListener('change', function() {
                self.directDrive(this); 
            });
        }
        const driveWidget = getWidget(self.tpId, "DRIVE");
        if (typeof(driveWidget) != 'undefined') {
            driveWidget.addEventListener('click', function() {
                self.driveTo();
            });
        }
        const cancelWidget = getWidget(self.tpId, "CANCEL");
        if (typeof(cancelWidget) != 'undefined') {
            cancelWidget.addEventListener('click', function() {
                self.cancelDrive(); 
            });
        }
        const driveToWidget = getWidget(self.tpId, "DIRECTDRIVE");
        if (typeof(driveToWidget) != 'undefined') {
            driveToWidget.addEventListener('change', function() {
                self.computeDriveTo(this);
            });
        }
        const driveRouteWidget = getWidget(self.tpId, "ROUTE");
        if (typeof(driveRouteWidget) != 'undefined') {
            driveRouteWidget.addEventListener('click', function() {
                self.driveRoute();
            });
        }
        const skipWidget = getWidget(self.tpId, "SKIP");
        if (typeof(skipWidget) != 'undefined') {
            skipWidget.addEventListener('click', function() {
                self.skip();
            });
        }
        const pauseWidget = getWidget(self.tpId, "PAUSE");
        if (typeof(pauseWidget) != 'undefined') {
            pauseWidget.addEventListener('click', function() {
                self.pauseDrive(this);
            });
        }
        const stepWidget = getWidget(self.tpId, "STEP");
        if (typeof(stepWidget) != 'undefined') {
            stepWidget.addEventListener('click', function() {
                self.stepDrive(); 
            });
        }
        const resetWidget = getWidget(self.tpId, "RESET");
        if (typeof(resetWidget) != 'undefined') {
            resetWidget.addEventListener('click', function() {
                self.reset(); 
            });
        }
        
        this.fetcher.addEventListener('body-available', function(event) {
            //cache for later processors
            self.locatorJson = event.detail.Locator;
            self.processTelemetryHeader(self, event.detail.Telemetry);
            self.processPoseHeader(self, event.detail.Pose, self.locatorJson);
            self.driverJson = event.detail.Driver;
            self.processDriverHeader(self, self.driverJson);
        });
        
        //initialise driving flag
        this.driving = false;
        
        //initialise time system offset
        this.lastUpdateJsSecs = 0;
        this.minTimeSystemOffset = Number.MAX_SAFE_INTEGER;

        //check mower list for any changes
        window.setInterval(function(){ // Set interval for checking
            try {
                getFromApi('mowers', function(data) {
                    var arr1 = JSON.parse(data);
                    const opts = robotSelectWidget.options;
                    const arr2 = Array.from(opts).map(el => el.value); 
                    arr2.shift();
                    var changed = !(arr1.length === arr2.length && arr1.every(function(value, index) { return value === arr2[index]}));
                    if (changed) {
                        //dynamic update
                        //clear leaving first
                        while (robotSelectWidget.options.length > 1) {                
                                robotSelectWidget.remove(robotSelectWidget.options.length - 1);
                        }  
                        for(var i = 0; i < arr1.length; i++) {
                            var opt = arr1[i];
                            var el = document.createElement("option");
                            el.textContent = opt;
                            el.value = opt;
                            robotSelectWidget.appendChild(el);
                        }                    
                    }
                });
            } catch { };
        }, 15000); // Repeat every 15000 milliseconds (15 seconds)
    }//end constructor
    
    processTelemetryHeader(self, headerJson) {

        //Start with cutter
        self.processCutterIndicator(self, headerJson);

    }//end process telemetry header
    
    processPoseHeader(self, headerJson) {
        //cache pose so X, Y and theta are available for relative drive tos
        self.poseJson = headerJson;
    }//end process pose header
    
    processDriverHeader(self, headerJson) {
        //Capture last visited
        if (typeof(headerJson) != 'undefined') {
            self.driverJson = headerJson;//cache for later
            self.lastVisitedRouteNode = headerJson['last_visited_route_node']; 
            //Update status
            self.processDriverStatus(self, headerJson);
            //Align selector
            self.processRobotSelector(self, headerJson);
        }//end header available
    }//end process driver header

    synchronizeWidgets(stateIndex) {
        
        switch(stateIndex) {
            case 4:
                // robot paused - enable step
                enableTool(this.tpId, this.btns.STEP, true);  
                break;
            case 3:
                // robot driving path - enable cancel/pause, disable yourself, drive route, mower selection, step
                enableTool(this.tpId, this.btns.CANCEL, true);  
                enableTool(this.tpId, this.btns.PAUSE, true);  
                enableTool(this.tpId, this.btns.DRIVE, false);  
                enableTool(this.tpId, this.btns.ROUTE, false);  
                enableTool(this.tpId, this.btns.CURRENTMOWER, false);  
                enableTool(this.tpId, this.btns.STEP, false);  
                break;
            case 2:
                // robot driving route - enable cancel/skip/pause, disable yourself, driveto, mower selection, step
                enableTool(this.tpId, this.btns.ROBOTSPEED, true);   
                enableTool(this.tpId, this.btns.CUTTER1ENABLED, true);  
                enableTool(this.tpId, this.btns.CUTTER2ENABLED, true);  
                enableTool(this.tpId, this.btns.CANCEL, true);  
                enableTool(this.tpId, this.btns.SKIP, true);  
                enableTool(this.tpId, this.btns.PAUSE, true);  
                enableTool(this.tpId, this.btns.ROUTE, false);  
                enableTool(this.tpId, this.btns.DRIVE, false);  
                enableTool(this.tpId, this.btns.CURRENTMOWER, false);  
                enableTool(this.tpId, this.btns.STEP, false);  
                break;
            case 13:
                // robot idle and destination planned - enable speeds/direct drive/cutter/drive, disable pause/skip/step
                enableTool(this.tpId, this.btns.DRIVE, true);
                break;  
            case 1:
                // robot idle - enable speeds/direct drive/cutter/drive/route, disable pause/skip/step
                enableTool(this.tpId, this.btns.CURRENTMOWER, true);  
                enableTool(this.tpId, this.btns.ROBOTSPEED, true);  
                enableTool(this.tpId, this.btns.DIRECTCOMMAND, true);  
                enableTool(this.tpId, this.btns.CUTTER1ENABLED, true);  
                enableTool(this.tpId, this.btns.CUTTER2ENABLED, true);  
                enableTool(this.tpId, this.btns.DIRECTDRIVE, true);  
                enableTool(this.tpId, this.btns.ROUTE, true);  
                enableTool(this.tpId, this.btns.PAUSE, false);  
                enableTool(this.tpId, this.btns.SKIP, false);  
                enableTool(this.tpId, this.btns.STEP, false);  
                break;
            case 0:
                // no robot selected - de-activate cutter widgets
                const cutSlideWidget1 = getWidget(this.tpId, "CUTTER1ENABLED");
                const cutSlideWidget2 = getWidget(this.tpId, "CUTTER2ENABLED");
                if (typeof cutSlideWidget1 !== 'undefined') {
                    cutSlideWidget1.checked = false;
                }
                if (typeof cutSlideWidget2 !== 'undefined') {
                    cutSlideWidget2.checked = false;
                }
                //Disable All Buttons
                enableToolpane(this.tpId, this.allBtns ^ this.disabMask);
                break;
            
        }//end switch 
    }//end sync widgets
     
    processRobotSelector(self, headerJson) {
        //Ensure robot dropdown is showing current robot
        const botSelWidget = getWidget(self.tpId, "CURRENTMOWER");
        if (typeof(botSelWidget) != 'undefined') {
            const curBot = botSelWidget.value;
            const curMower = headerJson['cur-mower'];
            const usrSelected = botSelWidget.dataset.changed == 'true';
            if (typeof curMower !== 'undefined' && curMower !== curBot && !usrSelected) {
                botSelWidget.value = curMower;
            }
            else if (typeof curMower === 'undefined' || curMower === 'None') {
                //save mower for button state
                self.curMower = null;
                botSelWidget.selectedIndex = 0;
            }//end null state
        }//end defined
    }//end process robot selector
    
    processCutterIndicator(self, headerJson) {
        const chkWidget1 = getWidget(self.tpId, "CUTTER1ENABLED");
        if (typeof(chkWidget1) != 'undefined') {
            if (typeof(headerJson) != 'undefined') {
                const cutterActivated = headerJson['cutter1'];
                //Only update widget if it is enabled
                //It will be disabled during cutter command processing
                if (typeof cutterActivated !== 'undefined' && !chkWidget1.disabled) {
                    if (cutterActivated == 0) {
                        chkWidget1.checked = false;                    
                    } else if (cutterActivated == 1) {
                        chkWidget1.checked = true;                                            
                    }
                }//end valid enab
            }//end defined
        }//end widget defined
        const chkWidget2 = getWidget(self.tpId, "CUTTER2ENABLED");
        if (typeof(chkWidget2) != 'undefined') {
            if (typeof(headerJson) != 'undefined') {
                const cutterActivated = headerJson['cutter2'];
                //Only update widget if it is enabled
                //It will be disabled during cutter command processing
                if (typeof cutterActivated !== 'undefined' && !chkWidget2.disabled) {
                    if (cutterActivated == 0) {
                        chkWidget2.checked = false;                    
                    } else if (cutterActivated == 1) {
                        chkWidget2.checked = true;                                            
                    }
                }//end valid enab
            }//end defined
        }//end widget defined
    }//end process cutter indicator
    
    processDriverStatus(self, headerJson) {
        
        const speedSelectWidget = getWidget(self.tpId, "ROBOTSPEED");
        if (typeof(speedSelectWidget) != 'undefined') {
            //ensure robot speeds are updated?
            // check for focus
            const isFocused = (document.activeElement === speedSelectWidget);
            if (!isFocused) {
                const rotSpeed = headerJson['rot-speed'];        
                const drvSpeed = headerJson['drv-speed'];
                const speedPair = rotSpeed + '.' + drvSpeed;
                if (speedSelectWidget.value !== speedPair && speedSelectWidget.dataset.changed != "true") {
                    speedSelectWidget.value = speedPair;
                }//end speed selector updated
            }//end unfocused
        }//end widget defined

        const statusWidget = getWidget(self.tpId, "NAVIGATIONSTATUS");
        if (typeof(statusWidget) != 'undefined') {
            const statusMsg = headerJson['state'];
            if (typeof statusMsg === 'undefined') {
                statusWidget.value = '';
            } else {
                statusWidget.value = statusMsg;
            }//end status available
        }//end widget defined
        
        //synchronise buttons
        const stateIndex = headerJson['state-index'];
        this.synchronizeWidgets(stateIndex);
        
    }//end process drive status

    switchCutter(cutNum) {
        const chkWidget = getWidget(this.tpId, `CUTTER${cutNum}ENABLED`);
        const that = this;
        if (!chkWidget.checked) {
            chkWidget.disabled = true;
            sendData('PUT', 'api', 'direct-drive', `>cutter(${cutNum-1}, 0)`, true, function() {
                that.switchCutterCallback(chkWidget);    
            });
        } else if (confirm('Are you sure you want to turn on the cutter?')) {
            chkWidget.disabled = true;
            sendData('PUT', 'api', 'direct-drive', `>cutter(${cutNum-1}, 1)`, true, function() {
                that.switchCutterCallback(chkWidget);
            });
        }
    }//end switch cutter
    
    switchCutterCallback(chkWidget) {
        chkWidget.disabled = false;    
    }//end switch cutter callback
    
    driveRoute() {
    
        //Prompt user to resume or restart
        let cmdData = null;
        if (typeof this.lastVisitedRouteNode !== undefined && this.lastVisitedRouteNode !== null) {
            let msg = 'The previous operation did not complete.';
            msg += '\nHit OK to Resume or Cancel to Restart.';
            if (confirm(msg)) {
                cmdData = this.lastVisitedRouteNode;
            }//end resume
        }//end resumable

        this.driving = true;
        
        const stateIndex = 2;
        this.synchronizeWidgets(stateIndex);

        //Update server
        sendData('PUT', 'api', 'drive-route', cmdData);
        
    }//end drive route
    
    skip() {
        
        //Update server
        sendData('PUT', 'api', 'skip', null);
        
    }//end skip
    
    cancelDrive() {
        
        const pauseBtn = getWidget(this.tpId, "PAUSE");   
        pauseBtn.classList.remove("depressed");

        //Hide map marker
        document.getElementsByClassName('marker')[0].style.top = '-9999px';

        this.driving = false;
        
        const stateIndex = 1;
        this.synchronizeWidgets(stateIndex);

        //Update server
        sendData('PUT', 'api', 'cancel-drive', -1);
        
    }//end cancel drive
    
    directDrive(sel) {

        const selCmd = sel.value;
        
        //Update server
        sendData('PUT', 'api', 'direct-drive', selCmd);
        
        //Reset Dropdown
        setTimeout(() => { sel.selectedIndex = 0; }, 4000);
            
    }//end direct drive
    
    computeDriveTo(sel) {

        const itm = sel.value;
        const xWidget = getWidget(this.tpId, "DRIVETOX");   
        const yWidget = getWidget(this.tpId, "DRIVETOY");   
        const tAng = this.poseJson['t_deg'];
        const xPos = this.poseJson['c_x_m'];
        const yPos = this.poseJson['c_y_m'];

        let x = 0;
        let y = 0;
    
        if (itm !== '') {
            const itmParts = itm.split('|');
            if (itmParts.length == 2) {
                //drive to location
                if (xPos != '' && yPos != '') {
                    //can't drive to absolute negative location, so any symbol indicates relative
                    if (itm.indexOf('+') != -1 || itm.indexOf('-') != -1) {
                        //relative drive
                        x = parseFloat(itmParts[0]) + parseFloat(xPos);
                        y = parseFloat(itmParts[1]) + parseFloat(yPos);             
                    } else {
                        //absolute
                        x = parseFloat(itmParts[0]);
                        y = parseFloat(itmParts[1]);                                    
                    }
                    xWidget.value = x.toFixed(2);
                    yWidget.value = y.toFixed(2);
                }//end valid values
            }  else if (itmParts.length == 1) {
                //forward
                if (itm.charAt(0) == 'F') {
                    const distance = itm.replace( /^\D+/g, '');
                    const xChange = distance * Math.sin((tAng * Math.PI / 180) - Math.PI);
                    const yChange = distance * Math.cos((tAng * Math.PI / 180) - Math.PI);
                    //relative drive
                    x = parseFloat(xPos) + xChange;
                    y = parseFloat(yPos) - yChange;             
                    xWidget.value = x.toFixed(2);
                    yWidget.value = y.toFixed(2);
                }//end fwd           
            }//end length 1
        }//end valid itm
        
        enableTool(this.tpId, this.btns.DRIVE, true); 
             
    }//end compute drive to
    
    driveTo() {
        const xWidget = getWidget(this.tpId, "DRIVETOX");   
        const yWidget = getWidget(this.tpId, "DRIVETOY");   
        const ddlWidget = getWidget(this.tpId, "DIRECTDRIVE");   
        let x = 'None';
        let y = 'None';
        if (xWidget != null) {
            x = xWidget.value;
            if (x == '') {
                x = 'None';
            }
        }
        if (yWidget != null) {
            y = yWidget.value;
            if (y == '') {
                y = 'None';
            }
        }
        if (x == y == 'None') {
            console.log('Can\'t Drive to unknown location!');
        } else {
            //Update server and refresh manual overlay
            sendData('PUT', 'api', 'drive', [x, y], true);               
        }
        
        //Reset dropdown so it can accept same request again!
        if (ddlWidget != null) {
            ddlWidget[0].selected = true; 
        }

        enableTool(this.tpId, this.btns.DRIVE, false); 
             
    }//end drive to
    
    reboot() {
        if (confirm('Are you sure you want to reboot the server?')) {
            sendData('PUT', 'api', 'reboot', 0);
        }//end confirmed    
    }//end reboot
    
    shutdown() {
        if (confirm('Are you sure you want to shutdown the server?')) {
            sendData('PUT', 'api', 'shutdown', 0);
        }//end confirmed    
    }//end shutdown
    
    enrolHotSpot() {
        if (confirm('Are you sure you want to enroll exclusively in this hotspot?. Make sure the hotspot is available as this enrolment cannot be undone without restarting mower!')) {
            sendData('PUT', 'api', 'enrol-hotspot', 0, true, function(resp) {
                if (resp !== 'ACK') {
                    alert('Problem enrolling in Hotspot: ' + resp);
                }    
            });
        }
    }//end enrol hotspot

    pauseDrive(btn) {
        
        let stateIndex = 4;//paused
        
        //indent radio button
        if (btn.classList.contains("depressed")) {
            btn.classList.remove("depressed");
            if (this.driverJson['path'] == 'Route') {
                stateIndex = 2;//unpaused            
            } else {
                stateIndex = 3;//unpaused                            
            }
        } else {
            btn.classList.add("depressed");
        }//end pause
        
        this.synchronizeWidgets(stateIndex);
    
        //Update server
        sendData('PUT', 'api', 'pause-drive', -1);
        
    }//end pause drive
    
    stepDrive() {
        
        //Update server
        sendData('PUT', 'api', 'step-drive', -1);
        
    }//end step drive
    
    reset() {
        
        //Update server
        sendData('PUT', 'api', 'reset', -1);
        
    }//end reset

}//end class