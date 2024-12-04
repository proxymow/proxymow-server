function refreshComponent(routeName, elemId, callback, errcallback) {
    var result = -1;
    if (typeof elemId === 'undefined') {
        elemId = routeName;
    }
    if (typeof refreshImages === 'undefined') {
        refreshImages = false;
    }
    const isSVG = routeName.toLowerCase().endsWith('svg');
    const xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4) {
            if (this.status == 200) {
                const tgt = document.getElementById(elemId);
                const html = this.responseText.trim(); // Never return a text node of whitespace as the result
                let domTmplt = null;
                if (isSVG) {
                    domTmplt = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    domTmplt.innerHTML = html;
                    tgt.parentNode.replaceChild(domTmplt.firstChild, tgt);
                } else {
                    domTmplt = document.createElement('template');                
                    domTmplt.innerHTML = html;
                    tgt.parentNode.replaceChild(domTmplt.content.firstChild, tgt);
                }
                result = 0;
                if (typeof callback !== 'undefined') {
                    callback(this.responseText);
                }//end callback
            } else {
                response = xhttp.responseText;
                if (typeof errcallback !== 'undefined') {
                    errcallback(this.responseText);
                }//end callback
            }
        }//end ready state 4
    };//end function
    xhttp.open("GET", "/" + routeName);
    xhttp.send();
    return result;
}//end refresh component

function enableToolpane(toolPaneId, enabMask) {
    //enable where enabMask is a 1 for each widget in toolpane
    let bitMask = 1;
    const toolPaneButtons = document.querySelectorAll('#' + toolPaneId + ' .widget');
    for (const toolPaneButton of toolPaneButtons) {
        toolPaneButton.disabled = !(enabMask & bitMask);
        bitMask *= 2;
    }//next button
}//end enableToolpane

function enableTool(toolPaneId, toolConst, enab) {
    //enable tool in toolpane
    //fails silently if widget unavailable
    const widget = getButton(toolPaneId, toolConst);
    if (typeof widget !== 'undefined') {
        widget.disabled = !(enab);
    }
}//end enableTool

function getButton(toolPaneId, toolConst) {
    let index = Math.log2(toolConst);
    const toolPaneButtons = document.querySelectorAll('#' + toolPaneId + ' .widget');
    return toolPaneButtons[index];    
}//end get button

function getWidget(toolPaneId, toolKey) {
    let result = undefined;
    try {
        if (toolPaneId in window && 'TOOLS' in window[toolPaneId] && toolKey in window[toolPaneId]['TOOLS']) {
            const toolConst = window[toolPaneId]['TOOLS'][toolKey]
            const index = Math.log2(toolConst);
            const toolPaneWidgets = document.querySelectorAll('#' + toolPaneId + ' .widget');
            result = toolPaneWidgets[index];
        }
    } catch(err) {
        console.log('Error toolPaneId', toolPaneId);
    }
    return result;   
}//end get widget

function sendData(verb, endpoint, path, value, asynchronous, callback, errcallback) {
    if (typeof asynchronous === 'undefined') {
        asynchronous = true;// don't block request awaiting response
    }
    const xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4) {
            if (xhttp.status === 200) {
                websiteErrors = 0;//clear down
                if (typeof callback !== 'undefined') {
                    callback(xhttp.responseText);
                }
            } else {
                response = xhttp.responseText;
                if (typeof errcallback !== 'undefined') {
                    errcallback(this.responseText);
                }//end callback
            }
        }
    };
    xhttp.open(verb, "/" + endpoint + "/" + path.replace(/\./g, '/'), asynchronous);
    xhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    xhttp.send('value=' + value);
}//end send data

function getFromApi(keyName, callback, errorCallback) {
    getData("/api/" + keyName, callback, errorCallback);
}//end get from api

function getData(url, callback, errorCallback) {
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4) {
            if (this.status == 200) {
                if (typeof callback !== 'undefined') {
                    callback(this.responseText);
                }
            } else {
               if (typeof errorCallback !== 'undefined') {
                    errorCallback();
                }
            }
        }
    };
    xhttp.open("GET", url, true);//don't block
    xhttp.send();
    
}//end getData

// First, checks if it isn't implemented yet.
if (!String.prototype.format) {
  String.prototype.format = function() {
    var args = arguments;
    return this.replace(/{(\d+)}/g, function(match, number) { 
      return typeof args[number] != 'undefined'
        ? args[number]
        : match
      ;
    });
  };
}//end format

function getRenderedRect(img) {
    const cWidth =  img.width;
    const cHeight = img.height;
    const width =   img.naturalWidth;
    const height =  img.naturalHeight;
    const oRatio = width / height;
    const cRatio = cWidth / cHeight;
    if (oRatio > cRatio) {
        rwidth = cWidth;
        rheight = cWidth / oRatio;
    } else {
        rwidth = cHeight * oRatio;
        rheight = cHeight;
    }      
    let left = (cWidth - rwidth) / 2;
    let top = (cHeight - rheight) / 2;
    return {
        width: Math.round(rwidth), 
        height: Math.round(rheight), 
        left: Math.round(left), 
        top: Math.round(top)
    };
}//end get rendered size

// sleep time expects milliseconds
function sleep (time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}
