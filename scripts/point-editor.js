class PointEditor {
    
    constructor(svgId, buttonPaneId, crosshairId, cursorPosId, configKey, depView) {

        //capture this
        const self = this;

        this.svgId = svgId;
        this.buttonPaneId = buttonPaneId;
        this.configKey = configKey;
        this.selectedClassname = "pt-selected";
        this.selectableClassname = "selectable-point";
        this.editor = document.getElementById(svgId);
        this.tempPointQueue = [];
        
        this.pointQueue = new Queue(configKey, 1000, function() {
            refreshComponent(depView);
        });
        
        //then locate button constants
        this.btns = window[buttonPaneId].TOOLS;

        //add specific actions to toolbar buttons
        const selectBtn = getButton(buttonPaneId, this.btns.SELECT);
        selectBtn.addEventListener('click', function () {
            self.selectOne();
        }, false);
        const extendBtn = getButton(buttonPaneId, this.btns.EXTEND);
        extendBtn.addEventListener('click', function () {
            self.selectMore();
        }, false);
        const allBtn = getButton(buttonPaneId, this.btns.ALL);
        allBtn.addEventListener('click', function () {
            self.selectAll();
        }, false);
        const clrBtn = getButton(buttonPaneId, this.btns.CLEAR);
        clrBtn.addEventListener('click', function () {
            self.selectNone();
        }, false);
        const expandBtn = getButton(buttonPaneId, this.btns.EXPAND);
        if (expandBtn) {
            expandBtn.addEventListener('click', function (evt) {
                self.expand(5, evt);self.updateSelected();
            }, false);
        }
        const contractBtn = getButton(buttonPaneId, this.btns.CONTRACT);
        if (contractBtn) {
            contractBtn.addEventListener('click', function (evt) {
                self.contract(5, evt);self.updateSelected();
            }, false);
        }
        const leftBtn = getButton(buttonPaneId, this.btns.LEFT);
        leftBtn.addEventListener('click', function (evt) {
            self.moveBy(-10, 0, evt);self.updateSelected();
        }, false);
        const rightBtn = getButton(buttonPaneId, this.btns.RIGHT);
        rightBtn.addEventListener('click', function (evt) {
            self.moveBy(10, 0, evt);self.updateSelected();
        }, false);
        const upBtn = getButton(buttonPaneId, this.btns.UP);
        upBtn.addEventListener('click', function (evt) {
            self.moveBy(0, -10, evt);self.updateSelected();
        }, false);
        const downBtn = getButton(buttonPaneId, this.btns.DOWN);
        downBtn.addEventListener('click', function (evt) {
            self.moveBy(0, 10, evt);self.updateSelected();
        }, false);
        const delBtn = getButton(buttonPaneId, this.btns.DELETE);
        if (delBtn) {
            delBtn.addEventListener('click', function () {
                if (confirm('Are You Sure?')) self.deleteSelected(['fencesvg', 'routeviewsvg']);
            }, false);
        }
        const rstBtn = getButton(buttonPaneId, this.btns.RESET);
        const cmdPrefix = configKey.split('.')[1].replace(/[\[\]]/gi,'');
        rstBtn.addEventListener('click', function () {
            self.reset(cmdPrefix + '-reset');
        }, false);
        
        this.editor.addEventListener('keydown', function () { self.handleKeyDown(event); });
        this.editor.addEventListener('keyup', function () { self.handleKeyUp(event); });
    
        this.initPoints(this);
        
        //Add cursor facility?
        if (crosshairId && cursorPosId) {
            this.editor.addEventListener('pointer', function (e) {
                const xPx = Math.round(e.detail.x * deviceWidth / 10000);
                const yPx = Math.round(e.detail.y * deviceHeight / 10000);
                const ptArray = [[xPx, yPx, 1]];
                const arenaPt = self.mmultiply(ptArray, arenaMatrix);
                const xArenaMetres = arenaPt[0][0]/arenaPt[0][2];//de-projectioned
                const yArenaMetres = arenaPt[0][1]/arenaPt[0][2];
                const xArenaMetresRnd = Math.round(xArenaMetres * 100) / 100;
                const yArenaMetresRnd = Math.round(yArenaMetres * 100) / 100;
                const xArenaHdpc = 10000 * xArenaMetres / arenaWidth;
                const yArenaHdpc = 10000 * (1 - (yArenaMetres / arenaLength));
                //position crosshair cursor in arena view
                const crossHair = document.getElementById(crosshairId);
                crossHair.x.baseVal.value = xArenaHdpc;
                crossHair.y.baseVal.value = yArenaHdpc;
                const cursorPos = document.getElementById(cursorPosId);
                cursorPos.textContent = `(${xArenaMetresRnd}, ${yArenaMetresRnd}) m`;
                let dx = cursorPos.getBBox().height;
                if (xArenaHdpc >= 10000 || yArenaHdpc >= 10000 || xArenaHdpc <= 0 || yArenaHdpc <= 0) {
                    cursorPos.textContent = ''; 
                    crossHair.x.baseVal.value = crossHair.y.baseVal.value = -10000; 
                } else if (xArenaHdpc < 5000 && yArenaHdpc < 5000) {
                    cursorPos.style.textAnchor = "start";
                    cursorPos.style.dominantBaseline = "text-before-edge";
                } else if (xArenaHdpc < 5000 && yArenaHdpc > 5000) {
                    cursorPos.style.textAnchor = "start";
                    cursorPos.style.dominantBaseline = "text-after-edge";
                } else if (xArenaHdpc > 5000 && yArenaHdpc < 5000) {
                    cursorPos.style.textAnchor = "end";
                    dx *= -1;
                    cursorPos.style.dominantBaseline = "text-before-edge";
                } else if (xArenaHdpc > 5000 && yArenaHdpc > 5000){
                    cursorPos.style.textAnchor = "end";
                    dx *= -1;
                    cursorPos.style.dominantBaseline = "text-after-edge";
                }
                cursorPos.x.baseVal[0].value = xArenaHdpc + dx;
                cursorPos.y.baseVal[0].value = yArenaHdpc;   
            }, false);
        }//end cursor required

        this.syncToolPaneState();
        
        //grab focus
        this.editor.focus();
    
    }//end constructor
    
    initPoints(self) {
        const hiddenLines = self.editor.getElementsByClassName('fence-line-hidden');
        for (const line of hiddenLines) {
            line.addEventListener('dblclick', function () { 
                self.addPointInLine(event, ['fencesvg', 'routeviewsvg']); 
            });
        }//next
        const selectablePoints = self.editor.getElementsByClassName('selectable-point');
        for (const sp of selectablePoints) {
            makeDraggable(sp);
            sp.addEventListener('dragstart', function (e) {
               self.psx = Math.round(e.target.x.baseVal.value);
               self.psy = Math.round(e.target.y.baseVal.value);
               self.selectOne(e.target.id);
            }, false);
            sp.addEventListener('drag', function (e) { 
               const x = e.detail.x;
               const y = e.detail.y;
               self.moveElemTo(e.target, self.psx + x, self.psy + y, true);
            }, false);
            sp.addEventListener('dragend', function (e) { 
               if (Math.abs(e.detail.x) > 0 || Math.abs(e.detail.y) > 0) {
                   self.updateSelected();
               }//end significant change
            }, false);
        }//next selectable
    }//end init points

    selectOne(ptId) {
        /*
            select first or designated point
            or next if selections exist
        */
        if (typeof ptId !== 'undefined') {
            
            //deselect all
            this.selectNone();
    
            //select designated
            this.selectPoint(ptId);
                       
        } else {
            
            const selecteds = this.editor.querySelectorAll("." + this.selectedClassname);
            const selectedCount = selecteds.length;
            const selectables = this.editor.querySelectorAll("." + this.selectableClassname);
            const selectableCount = selectables.length;
            if (selectedCount == 0) {
                //selectables[0].classList.add(this.selectedClassname);
                this.selectPoint(selectables[0].id);
            } else {
                //select next
                const lastPoint = selecteds[selecteds.length - 1];
                const lastIndex = [].indexOf.call(selectables, lastPoint);
                const nextPoint = selectables[(lastIndex + 1) % selectableCount];
                //deselect all
                this.selectNone();
                this.selectPoint(nextPoint.id);
            }//end next
        }//end
                
        this.syncToolPaneState();
        this.syncScaffold(typeof selecteds !== 'undefined' && selecteds.length == selectables.length);
    }//end select one

    selectMore() {
        //extend selection
        const selectables = this.editor.querySelectorAll("." + this.selectableClassname);
        let selectableCount = selectables.length;
        const selecteds = this.editor.querySelectorAll("." + this.selectedClassname);
        let selectedCount = selecteds.length;
        if (selectedCount == 0) {
            //select first
            selectables[0].classList.add(this.selectedClassname);
        } else if (selectedCount < selectableCount) {
            //select next
            const lastPoint = selecteds[selecteds.length - 1];
            const lastIndex = [].indexOf.call(selectables, lastPoint);
            const nextPoint = selectables[(lastIndex + 1) % selectableCount];
            this.selectPoint(nextPoint.id);
        }//end select next
        this.syncToolPaneState();
        this.syncScaffold(selecteds.length == selectables.length - 1);
        this.clrNodeInfo();
    }//end select more

    selectAll() {
        //select all points
        const selectables = this.editor.querySelectorAll("." + this.selectableClassname);
        for (let i = 0; i < selectables.length; i++) {
            selectables[i].classList.add(this.selectedClassname);
        }//next
        this.syncToolPaneState();
        this.syncScaffold(true);
        this.clrNodeInfo();
    }//end select all

    selectNone() {
        //clear selections
        const selecteds = this.editor.querySelectorAll("." + this.selectedClassname);
        for (let i = 0; i < selecteds.length; i++) {
            selecteds[i].classList.remove(this.selectedClassname);
        }//next
        this.syncToolPaneState();
        this.syncScaffold(false);
        this.clrNodeInfo();
    }//end select none

    selectPoint(id) {
        /*
            select designated point
        */
        const nextPt = this.editor.getElementById(id);
        nextPt.classList.add(this.selectedClassname);

        //report location in status label
        this.nodeinfo();
         
    }//end select one

    handleKeyDown(event) {
        const zoomableFocussed = document.activeElement.classList.contains('zoomable');
        if (zoomableFocussed) {
            let useDefaultAction = false;
            let isShiftDown = event.shiftKey;
            let isCtrlDown = event.ctrlKey;
            let incr = 10;
            if (event.keyCode == 37) {
                //left
                this.moveBy(-incr, 0, event);
            } else if (event.keyCode == 38) {
                //up
                this.moveBy(0, -incr, event);
            } else if (event.keyCode == 39) {
                //right
                this.moveBy(incr, 0, event);
            } else if (event.keyCode == 40) {
                //down
                this.moveBy(0, incr, event);
            } else if (event.keyCode == 187) {
                //+ expand selection respecting aspect ratio
                this.expand(growPc, event);
            } else if (event.keyCode == 189) {
                //- contract selection respecting aspect ratio
                this.contract(growPc, event);
            } else if (event.keyCode == 9) {
                //tab
                if (isShiftDown) {
                    //expand
                    this.selectMore();
                } else {
                    this.selectOne();
                }
            } else if (event.keyCode == 27) {
                //esc
                this.selectNone();
            } else if (event.keyCode == 65 && isCtrlDown) {
                //ctrl-A
                this.selectAll();
            } else if (event.keyCode == 46) {
                //del
                if (confirm('Are you sure?')) {
                    this.deleteSelected(['fencesvg', 'routeviewsvg']);
                }//end confirmed
            } else {
                //pass key to OS
                useDefaultAction = true;
            }
            if (!useDefaultAction) event.preventDefault(true);
        }//end zoomable focussed  
        
    }//end handle keydown

    handleKeyUp(event) {
        const selOnly = [9, 16, 17, 27, 65, 46].includes(event.keyCode);
        if (!selOnly) this.updateSelected();
    }//end handle key up

    syncToolPaneState() {
        //count selections
        const selecteds = this.editor.querySelectorAll("." + this.selectedClassname);
        const selectables = this.editor.querySelectorAll("." + this.selectableClassname);
        const enabPerm = this.btns.RESET;
        const enabNudge = this.btns.UP | this.btns.DOWN | this.btns.LEFT | this.btns.RIGHT;
        let enabMask = 0;
        if (selecteds.length == selectables.length) {
            //all selected - can nudge, expand, contract, cancel
            enabMask = enabPerm | enabNudge | this.btns.EXPAND | this.btns.CONTRACT | this.btns.CLEAR;
        } else if (selecteds.length == 0) {
            //none selected - can't nudge, expand, contract, cancel
            enabMask = enabPerm | this.btns.SELECT | this.btns.ALL | this.btns.EXTEND;
        } else if (selecteds.length == 1) {
            //one selected - can delete if enough, select next, extend, nudge or cancel
            enabMask = enabPerm | enabNudge | this.btns.ADD | (selectables.length > 3 ? this.btns.DELETE : 0) | this.btns.SELECT | this.btns.ALL | this.btns.EXTEND | this.btns.CLEAR;
        } else {
            //2..n-1 selected - can select next, extend, nudge or cancel
            enabMask = enabPerm | enabNudge | this.btns.ADD | this.btns.SELECT | this.btns.ALL | this.btns.EXTEND | this.btns.CLEAR;
        }
        enableToolpane(this.buttonPaneId, enabMask);
        
    }//end sync tool pane state

    moveBy(dx, dy, evt) {
        const isAltDown = evt.altKey;
        if (isAltDown) {
            dx /= 10;
            dy /= 10;
        }//end fine control
        const selecteds = this.editor.querySelectorAll("." + this.selectedClassname);
        let valid = true;
        for (let i = 0; i < selecteds.length; i++) {
            let elem = selecteds[i];
            let curValX = parseInt(elem.getAttribute('x'));
            let newValX = curValX + dx;
            let curValY = parseInt(elem.getAttribute('y'));
            let newValY = curValY + dy;
            valid &= this.moveElemTo(elem, newValX, newValY, false);
        }//next selected
        if (valid) {
            this.commitMove();
            //report location in status label
            this.nodeinfo();
        }//end valid move
    }//end moveby

    validateMove(x, y) {
        return x >= 0 && y >=0 && x <= 10000 && y <= 10000;
    }//end validate move

    moveElemTo(elem, x, y, autocommit) {
        let valid = false;
        if (this.validateMove(x, y)) {
            this.tempPointQueue.push(elem, x, y);
            valid = true;        
        }//end valid
        if (autocommit && valid) {
            this.commitMove();
        }//end autocommit
        return valid;
    }//end move element to

    commitMove() {
        while (this.tempPointQueue.length > 0) {
            const y = this.tempPointQueue.pop();
            const x = this.tempPointQueue.pop();
            const elem = this.tempPointQueue.pop();
            elem.setAttribute('x', x);
            elem.setAttribute('y', y);
            this.repositionConnectedLines(elem.id, x, y);        
        }//wend
    }//end commit

    repositionConnectedLines(ptId, x, y) {   
        //find visible and hidden lines that finish at this point...
        const finishers = this.editor.querySelectorAll(`line[data-finish='${ptId}']`);
        for (const finisher of finishers) {
            const prevPtId = finisher.dataset.start;
            const prevPt = this.editor.getElementById(prevPtId);
            const x1 = parseInt(prevPt.getAttribute('x'));
            const y1 = parseInt(prevPt.getAttribute('y'));
            const rad = parseInt(prevPt.dataset.r);
            const isVisible = finisher.classList.contains('visible-line');
            this.repositionLine(finisher, x1, y1, x, y, isVisible ? rad : 0);
        }//next finisher
        //find visible and hidden lines that start at this point...
        const starters = this.editor.querySelectorAll(`line[data-start='${ptId}']`);
        for (const starter of starters) {
            const nextPtId = starter.dataset.finish;
            const nextPt = this.editor.getElementById(nextPtId);   
            const x2 = parseInt(nextPt.getAttribute('x'));
            const y2 = parseInt(nextPt.getAttribute('y'));
            const rad = parseInt(nextPt.dataset.r);
            const isVisible = starter.classList.contains('visible-line');
            this.repositionLine(starter, x, y, x2, y2, isVisible ? rad : 0);
        }//next starter
        //find any text that resides at this point...
        const connectedTextLabels = this.editor.querySelectorAll(`text[data-connect='${ptId}']`);
        for (let label of connectedTextLabels) {
            label.attributes['x'].value = x;
            label.attributes['y'].value = y;        
        }//next label
    }//end reposition connected lines

    repositionLine(line, x1, y1, x2, y2, rad) {  
        const x_span = x2 - x1;
        const y_span = y2 - y1;
        const h1 = Math.sqrt(Math.pow(x_span, 2) + Math.pow(y_span, 2));
        const h2 = h1 - (2 * rad);
        const ratio = h2 / h1;
        const x_span2 = x_span * ratio;
        const y_span2 = y_span * ratio;
        const x3 = x1 + ((x_span - x_span2) / 2);
        const y3 = y1 + ((y_span - y_span2) / 2);
        const x4 = x2 - ((x_span - x_span2) / 2);
        const y4 = y2 - ((y_span - y_span2) / 2);
    
        line.attributes['x1'].value = x3;
        line.attributes['y1'].value = y3;
        line.attributes['x2'].value = x4;
        line.attributes['y2'].value = y4;
    }//end reposition line

    updateSelected() {
        const selecteds = this.editor.querySelectorAll("." + this.selectedClassname);
        for (let i = 0; i < selecteds.length; i++) {
            let elem = selecteds[i];
            let xval = parseInt(elem.getAttribute('x'));
            let yval = parseInt(elem.getAttribute('y'));
            this.updatePosition(elem, xval, yval);
        }//next selected    
    }//end update selected

    syncScaffold(show) {
        let scafGrp = this.editor.getElementById('scaffold');
        if (scafGrp) {
            if (!show) {
                //hide scaffolding
                scafGrp.style.visibility = 'hidden';        
            } else {
                //calculate centroid
                const pts = this.editor.querySelectorAll("." + this.selectedClassname);
                const centroid = this.getPolygonCentroid(pts);
                const svg_centroid = this.editor.getElementById('centroid');
                svg_centroid.cx.baseVal.value = centroid.x;
                svg_centroid.cy.baseVal.value = centroid.y;    
                //copy pts to scaffold pts
                for (let i = 0; i < pts.length; i++) {
                    let pt = pts[i];
                    let id = pt.getAttribute('id');
                    let xval = parseInt(pt.getAttribute('x'));
                    let yval = parseInt(pt.getAttribute('y'));
                    const scafPt = this.editor.getElementById(id.replace(id.split('-')[0], 'scafpt'));
                    scafPt.cx.baseVal.value = xval;
                    scafPt.cy.baseVal.value = yval;
                    //position construction lines - extending to border
                    const scafLn = this.editor.getElementById(id.replace(id.split('-')[0], 'scafln'));
                    const dy = yval - centroid.y;
                    const dx = xval - centroid.x;
                    scafLn.x1.baseVal.value = centroid.x;
                    scafLn.y1.baseVal.value = centroid.y;
                    scafLn.x2.baseVal.value = xval + dx;
                    scafLn.y2.baseVal.value = yval + dy;
                    
                }//next pt
                //visibilise scaffolding
                scafGrp.style.visibility = 'visible';
            }//end show
        }//end scaffolded
    }//end init scaffold

    getPolygonCentroid(ptNodes) {
        let selArr = Array.from(ptNodes);
        const pts = selArr.map(obj => {
            let rObj = {}
            rObj.x = obj.x.baseVal.value;
            rObj.y = obj.y.baseVal.value;
            return rObj
        });
        const first = pts[0], last = pts[pts.length-1];
        if (first.x != last.x || first.y != last.y) pts.push(first);
        let twicearea = 0,
            x = 0, y = 0,
            nPts = pts.length,
            p1, p2, f;
        for ( let i=0, j=nPts-1 ; i<nPts ; j=i++ ) {
            p1 = pts[i]; p2 = pts[j];
            f = (p1.y - first.y) * (p2.x - first.x) - (p2.y - first.y) * (p1.x - first.x);
            twicearea += f;
            x += (p1.x + p2.x - 2 * first.x) * f;
            y += (p1.y + p2.y - 2 * first.y) * f;
        }//next pt
        f = twicearea * 3;
        return { x:x/f + first.x, y:y/f + first.y };
    }//end get polygon centroid

    growShrink(amt_pc, evt, grow) {
        //move pts outwards along construction path
        const isAltDown = evt.altKey;
        if (isAltDown) {
            amt_pc /= 5;
            amt_pc /= 5;
        }//end fine control
        const factor = 100 / amt_pc;
        const pts = this.editor.querySelectorAll("." + this.selectedClassname);
        const centroid = this.editor.getElementById('centroid');
        const centX = centroid.getAttribute('cx');
        const centY = centroid.getAttribute('cy');
        let valid = true;
        for (let i = 0; i < pts.length; i++) {
            const pt = pts[i];
            const id = pt.getAttribute('id');
            const xval = parseInt(pt.getAttribute('x'));
            const yval = parseInt(pt.getAttribute('y'));
            const newId = id.replace(id.split('-')[0], 'scafpt');
            const scafPt = this.editor.getElementById(newId);
            const scafX = scafPt.cx.baseVal.value;
            const scafY = scafPt.cy.baseVal.value;
            const xRange = centX - scafX;    
            const yRange = centY - scafY;
            let newX = xval + (xRange / factor);    
            let newY = yval + (yRange / factor);            
            if (grow) {
                newX = xval - (xRange / factor);    
                newY = yval - (yRange / factor);
            }
            valid &= this.moveElemTo(pt, newX, newY, false); 
        }//next pt
        if (valid) {
            this.commitMove();
        }//end valid move    
    }//end grow shrink

    expand(amt_pc, evt) {
        //move pts outwards along construction path
        this.growShrink(amt_pc, evt, true);
    }//end expand
    
    contract(amt_pc, evt) {
        //move pts inwards along construction path
        this.growShrink(amt_pc, evt, false);
    }//end contract

    updatePosition(elem, xval, yval) {

        //Update server
        //convert non-cartesian svg to cartesian storage json
        const dataPoint = `{ "index": ${ elem.id.match(/\d+/)[0] }, "x": ${ xval/100 }, "y": ${ 100 - (yval/100) }}`;
        this.pointQueue.add(elem.id, dataPoint);
    
    }//end update position

    reset(cmd) {
        //reset point data with specific cmd, then reload
        if (confirm('Are you sure you want to reset?')) {
            sendData('PUT', 'api', cmd, null, true, function() { location.reload(); });
        }//end confirmed
    }//end reset

    addPointAfterPoint(compNames) {
        const selecteds = this.editor.querySelectorAll("." + this.selectedClassname);
        const lastSelectedPt = selecteds[selecteds.length - 1];
        //find first line that start at this point...
        const emanatingLine = this.editor.querySelectorAll(`line[data-start='${lastSelectedPt.id}']`)[0];
        this.addPoint(emanatingLine, compNames);
    }//end add point after point

    addPointInLine(event, compNames) {
        this.addPoint(event.target, compNames);
    }//end add point in line

    addPoint(lineElem, compNames) {
        const startId = lineElem.dataset.start;
        //the finish id will become the new point id
        const startNum = startId.match(/\d+/)[0];
        const x1 = lineElem.x1.baseVal.value;
        const y1 = lineElem.y1.baseVal.value;
        const x2 = lineElem.x2.baseVal.value;
        const y2 = lineElem.y2.baseVal.value;
        //find midpoints as percentages, convert to cartesian y
        const mx = (x1 + x2) / 200;
        const my = 100 - ((y1 + y2) / 200);
        const newId = +startNum + 1;//convert to number and increment
        const dataPoint = `{ "index": ${ newId }, "x": ${ mx }, "y": ${ my } }`;
        let self = this;
        sendData('POST', 'api', this.pointQueue.name, dataPoint, true, function() {
            self.callRecursive(compNames, 0, function() {self.initPoints(self)});
        });
    }//end add point

    callRecursive(compNames, i, finalCallback) {
        const compName = compNames[i];
        let self = this;           
        refreshComponent(compName, compName, function() {
            if (i === compNames.length - 1) {
                finalCallback();        
            }//end last component
            else {
                self.callRecursive(compNames, i + 1, finalCallback);
            }
        });
    }//end call recursive

    deleteSelected(compNames) {
        const selecteds = this.editor.querySelectorAll("." + this.selectedClassname);
        for (let i = 0; i < selecteds.length; i++) {
            const elem = selecteds[i];
            const curId = elem.id.match(/\d+/)[0];
            const self = this;
            sendData('DELETE', 'api', this.pointQueue.name + "." + curId, null, true, function() {
                self.callRecursive(compNames, 0, function() {self.initPoints(self)});
            });
        }//next selected
    }//end delete selected
    
    mmultiply(a, b) {
        const self = this;
        return a.map(function(x, i) {
            return b.map(function(y, k) {
                return self.dotproduct(x, y)
            });
        });
    }//end matrix multiply

    dotproduct(a, b) {
        return a.map(function(x, i) {
            return a[i] * b[i];
        }).reduce(function(m, n) { return m + n; });
    }//end dot product
    
    nodeinfo() {
        //report location in status label
        const labWidget = getWidget(this.buttonPaneId, "NODEXYM");
        const selecteds = this.editor.querySelectorAll("." + this.selectedClassname);
        if (selecteds.length == 0) {
            // clear status
            labWidget.value = '';
        } else {
            const ptId = selecteds[0].id; // first 
            const thePt = this.editor.getElementById(ptId);
            const xhdpc = parseInt(thePt.getAttribute('x'));
            const yhdpc = parseInt(thePt.getAttribute('y'));
            const xm = arenaWidth * xhdpc / 10000;
            const ym = arenaLength * (1 - (yhdpc / 10000));
            const xmRnd = xm.toFixed(3);
            const ymRnd = ym.toFixed(3);
            const msg = `${xmRnd}, ${ymRnd}`;
            labWidget.value = msg;
        }//end some selected    
    }//end node info
    
    clrNodeInfo() {
        const labWidget = getWidget(this.buttonPaneId, "NODEXYM");
        labWidget.value = '';
    }//end clrNodeInfo
    
}//end class