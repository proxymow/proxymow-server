function prepareMenu() {
    var toggler_nodelist = document.querySelectorAll("#settings-menu-list div");
    var toggler_arr = [...toggler_nodelist];

    toggler_arr.forEach((userItem) => {
        userItem.addEventListener("click", function() {
            let ul = this.nextElementSibling;
            if (ul != null) {
                ul.classList.toggle("active");//ul
                this.classList.toggle("caret-down");//div
            }//end sub-tree
        });
    });
}//end prepare menu

function renderForm(id, xpath_qry, mode, klassname) {
    const animWrpEl = document.getElementById('animation-wrapper');
    animWrpEl.classList.add('saving-animate');
    if (typeof mode === 'undefined') {
        mode = 'edit';
    }
    let url = `form?id=${id}&xp=${xpath_qry}&mode=${mode}`;
    if (typeof klassname !== 'undefined') {
        url += `&klass=${klassname}`;
    }
    refreshComponent(url, "settings-form", 
        function() {
            //initialise with forced change event
            var selects = document.querySelectorAll(".form-pane select");
            var selectsArr = [...selects];
            selectsArr.forEach((select) => {
                const event = new Event('change');
                select.dispatchEvent(event);
            });
            animWrpEl.classList.remove('saving-animate');
            window.setTimeout(function() {
                const settingsFormEl = document.getElementById('settings-form');
                const firstFocusable = settingsFormEl.querySelector('input:not([disabled]),select:not([disabled])');
                if (firstFocusable !== null) {
                    firstFocusable.focus();
                }
            }, 0);
        }, //end success
        function() {
            animWrpEl.classList.remove('saving-animate');
            alert('There was a problem fetching the form!');
        }//end failure
    );
}//end render form

function save(menuOptId, url, mode, btn) {
    url += `?mode=${mode}`;
    if (mode == 'edit') {
        method = 'PATCH';
    } else {
        method = 'POST';
    }
    let success = false;
    let isFormValid = true;
    if (isFormValid) {
        const [json, errors] = getNestedFieldsetJson();
        if (errors.length > 0) {
            alert(errors.join('\n'));
            isFormValid = false;
        } else {
            const animWrpEl = document.getElementById('animation-wrapper');
            animWrpEl.classList.add('saving-animate');
            const encJson = encodeURIComponent(json);
            
            sendData(method, "xapi", url, encJson, true, 
            function(resp) {
                animWrpEl.classList.remove('saving-animate');
                success = processSaveResponse(resp);
                resyncMenu(menuOptId, mode, btn, success);
            },
            function(resp) {
                animWrpEl.classList.remove('saving-animate');
                success = processSaveResponse(resp);
            });
        }
    }//end submit
    else {
        firstErrorFld.focus();
        firstErrorFld.scrollIntoView();
        setTimeout(function() {
            alert(errors.join("\n"));
        }, 1000);
    }//end errors
}//end save

function resyncMenu(menuOptId, mode, btn, success) {
    if (menuOptId === 'null') {
        //launched from Navigator
        btn.parentElement.parentElement.style.display="none";
        cancel(menuOptId, success, btn); 
    } else if (['create', 'duplicate'].includes(mode)) {
        refreshComponent("settings_menu", "settings-menu-list", function() {
            prepareMenu();
            expandMenuTree(menuOptId);
            if (success) {
                cancel(menuOptId, success, btn);                
            }
        });
    }//end create
    else {
        cancel(menuOptId, success, btn);        
    }//end edit
}//end refresh menu

function cancel(menuOptId, success, btn) {
    if (menuOptId === 'null') {
        //launched from Navigator
        btn.parentElement.parentElement.style.display="none";           
    } else {
        refreshComponent(`form_shell?success=${success}`, "settings-form");
    }
}//end cancel

function getNestedFieldsetJson() {
    const fieldsets = document.querySelectorAll(".form-pane fieldset");
    let json = '';
    let isFormValid = true;
    let errors = [];
    let firstErrorFld = null;
    for (let j = 0; j < 1; j++) { //fieldsets.length
        const fs = fieldsets[j];
        if (fs.style.display !== 'none') {
            json += getNestedFormJson(fs, isFormValid, errors, firstErrorFld);
        }
    }//next fs
    return [json, errors];
}//end
function getNestedFormJson(fs, isFormValid, errors, firstErrorFld) {
    let json = '';
    var flds = fs.querySelectorAll(":scope > div > input, :scope > div > select, :scope > input, :scope > fieldset");
    for (var j = 0; j < flds.length; j++) {
        var fld = flds[j];
        if (fld.type === 'fieldset') {
            if (fld.style.display !== 'none') {
                const varName = fld.dataset.var;
                let nvp = '"' + varName + '": ' + getNestedFormJson(fld, isFormValid, errors, firstErrorFld);
                json += nvp + ",";
            }
        } else {
            //iterate through fields
            const fldName = fld.dataset.key;
            const fldType = fld.dataset.type;
            const isReadOnly = fld.readOnly;
            //check validation
            const assLabelText = fld.previousElementSibling.innerText;
            const regexStr = fld.dataset.validate;
            if (typeof regexStr !== "undefined") {
                const regex = new RegExp(regexStr);
                isValid = regex.test(fld.value);
                if (!isValid) {
                    const msgStr = fld.dataset.valmsg;
                    if (typeof msgStr !== "undefined") {
                        errors.push(assLabelText + " " + msgStr);
                    } else {
                        errors.push(assLabelText + " is invalid!");
                    }//end no custom message
                    if (firstErrorFld === null) {
                        firstErrorFld = fld;
                    }
                    isFormValid = false;
                }//end invalid
            } else if (fldType == "number") {
                const minVal = fld.getAttribute("min");
                const maxVal = fld.getAttribute("max");
                //Number('') returns zero, so check for nulls seperately
                const numValid = fld.value !== '' && Number(minVal) <= Number(fld.value) && Number(fld.value) <= Number(maxVal);
                if (!numValid) {
                    errors.push(assLabelText + ` must be in the range ${minVal} to ${maxVal} incl.`);
                }
            }//end validity check
            if (fld != null && !isReadOnly && isFormValid) {
                if (fldType == "boolean") {
                    value = fld.checked ? "true" : "false";
                } else if (fldType == "string") {
                    value = '"' + fld.value + '"';
                } else {
                    value = fld.value;
                }//end numeric
                if (value === '') {
                    value = 'null';
                }
                const nvp = '"' + fldName + '": ' + value;
                json += nvp + ",";
            }//end valid
        }//end input element
    }//next widget
    return "{" + json.replace(/,\s*$/, "") + "}";
}//end get nested form json

function getFormJson() {
    var nvps = [];
    var flds = document.querySelectorAll(".form-pane input");
    var isFormValid = true;//assume ok
    let errors = [];
    let firstErrorFld = null;
    for (var j = 0; j < flds.length; j++) {
        var fld = flds[j];
        //iterate through fields
        var fldName = fld.dataset.key;
        var fldType = fld.dataset.type;
        var isReadOnly = fld.readOnly;
        //check validation
        var regexStr = fld.dataset.validate;
        if (typeof regexStr !== "undefined") {
            const regex = new RegExp(regexStr);
            isValid = regex.test(fld.value);
            if (!isValid) {
                const assLabelText = fld.previousElementSibling.innerText;
                const msgStr = fld.dataset.valmsg;
                if (typeof msgStr !== "undefined") {
                    errors.push(assLabelText + " " + msgStr);
                } else {
                    errors.push(assLabelText + " is invalid!");
                }//end no custom message
                if (firstErrorFld === null) {
                    firstErrorFld = fld;
                }
                isFormValid = false;
            }//end invalid
        }//end validity check
        if (fld != null && !isReadOnly && isFormValid) {
            if (fldType == "boolean") {
                value = fld.checked ? "true" : "false";
            } else if (fldType == "string") {
                value = '"' + fld.value + '"';
            } else {
                value = fld.value;
            }//end numeric
            var nvp = '"' + fldName + '": ' + value;
            nvps.push(nvp);
        }//end valid
    }//next widget
    const json = "{" + nvps.join(",") + "}";
    return json;
}//end get form json

function expandMenuTree(menuOptId) {
    let clickedAnchorTag = document.getElementById(menuOptId);
    let ancestors = menuOptId.split('.');
    while(ancestors.length > 1) {
        ancestors.pop();
        let parListId = ancestors.join('.');
        let parList = document.getElementById(parListId);
        parList.classList.toggle("active");//ul
        parList.previousElementSibling.classList.toggle("caret-down");//div
    }//wend
    //try to expand self e.g. new_strategy to expose rules & terms
    //only required for add entries
    if (menuOptId.endsWith('.0')) {
        const numEntries = clickedAnchorTag.parentElement.parentElement.childElementCount - 1;
        ancestors = menuOptId.split('.');
        ancestors.pop();//remove trailing 0
        ancestors.push(numEntries);//add n
        let newChildId = ancestors.join('.');//reconstruct id
        let newChildElem = document.getElementById(newChildId); 
        const childLists = newChildElem.parentElement.querySelectorAll("ul");
        childLists.forEach((childList) => {
            childList.classList.toggle("active");//ul
            childList.previousElementSibling.classList.toggle("caret-down");//div        
        });
    }//end inserts
}//end expand menu tree

function clickNewEntry(menuOptId) {
    let clickedAnchorTag = document.getElementById(menuOptId);
    clickedAnchorTag.parentElement.previousElementSibling.firstElementChild.click();
}//end post process

function processSaveResponse(resp) {
    var success = false;
    if (resp == 1) {
       success = true;
    }
    else if (isNaN(resp)) {
        alert("Settings - there was a problem saving the data!\n" + resp);        
    }
    else { 
        alert("Settings - there was a problem saving the data!");
    }//end error
    return success;
}//end process save response

function del(menuOptId, url) {
    if (confirm('Are you sure you want to delete this item?')) {
        sendData("DELETE", "xapi", url, null, true, 
            function() {
                refreshComponent("settings_menu", "settings-menu-list", function() {
                    prepareMenu();
                    expandMenuTree(menuOptId);
                    cancel(true);
                });
            },//end success callback
            function() {
                alert("Settings - there was a problem deleting the data!");
            }//end failure callback
        );//end send data
    }//end confirmation
}//end del

function syncFieldsets(el) {
    let selValue = el.value;
    const selText = el.options[el.selectedIndex].text;
    //find matching fieldset...
    if (selValue.substring(0, 6) == 'Remote') {
        selValue = selValue.substring(6);
    }
    const fs = document.querySelector(`fieldset[data-class="${selValue}"]`);
    //find siblings (not me) of same element type...
    const siblings = getSiblings(fs);
    //hide siblings
    siblings.forEach((fldSet) => {
        fldSet.style.display = "none";
    });
    //copy nice name to legend
    fs.querySelector('legend').innerText = selText;
    //make selected fieldset visible
    fs.style.display = "block";
    
    //hide device index for non-usb cameras
    const devIndexDiv = el.parentElement.nextElementSibling;
    if (selValue.toLowerCase().indexOf('usb') != -1) {
        devIndexDiv.style.display = "block";        
    } else {
        devIndexDiv.style.display = "none";
    }//end show usb
    //hide endpoint for non remote devices
    const devEndpointDiv = devIndexDiv.nextElementSibling;
    if (selText.toLowerCase().indexOf('remote') != -1) {
        devEndpointDiv.style.display = "block";        
    } else {
        devEndpointDiv.style.display = "none";
    }//end show endpoint
}//end sync fieldsets

function getSiblings(e) {
    // for collecting siblings
    let siblings = []; 
    // if no parent, return no sibling
    if(e === null || !e.parentElement) {
        return siblings;
    }
    // first child of the parent node
    let sibling  = e.parentElement.firstElementChild;
    // collecting siblings
    while (sibling) {
        if (sibling !== e && sibling.type === e.type) {
            siblings.push(sibling);
        }
        sibling = sibling.nextElementSibling;
    }
    return siblings;
};
    
function display_json(json) {
    document.getElementById("jsondata").innerText = json;
}//end display json

function strategyTermDelete(name) {
    if (confirm('Are you sure you want to delete this term?')) {
        sendData('PUT', 'api', 'DeleteStrategyTerm|' + name, null, true, function(resp) {
            if (resp < 1) {
                alert('There was a problem deleting the term!')
            }//end error
        });
    }//end confirmed
}//end strategy Term delete

function strategyRuleDelete(name) {
    if (confirm('Are you sure you want to delete this rule?')) {
        sendData('PUT', 'api', 'DeleteStrategyRule|' + name, null, true, function(resp) {
            if (resp < 1) {
                alert('There was a problem deleting the rule!')
            }//end error
        });
    }//end confirmed
}//end strategy rule delete

function strategyRuleDuplicate(stratName, ruleName) {
    xpath = `navigation_strategies/strategy[@name="${stratName}"]/rules/rule[@name="${ruleName}"]`;
    document.getElementsByClassName('settings-form')[0].style.display='block';
    renderForm(null, xpath, 'duplicate');
}//end strategy rule duplicate

function reposition(evt, preIndex, prePriority, index, priority, succIndex, succPriority) {
    //promote if clicked upper half, demote if lower
    var rect = evt.target.getBoundingClientRect();
    const y = evt.clientY;  //y position within the element.
    const top = rect.top;  //top of element.
    const height = rect.height;  //height of element.
    const inUpperHalf = y - top < height / 2;
    const dir = inUpperHalf ? "up":"down";
    if (dir === 'up') {
        rulePrioritySwitch(index, priority, preIndex, prePriority);
    } else {
        rulePrioritySwitch(index, priority, succIndex, succPriority);
    }
    document.querySelectorAll('.up-arrow, .down-arrow, .up-down-arrow').forEach(el => {
        el.style.pointerEvents = 'none';
        el.style.transition = "opacity 0.5s linear 0s";
        el.style.opacity = 0.0;
    });
}//end reposition

function rulePrioritySwitch(i1, p1, i2, p2) {
    const patchUrlTmplt = 'strategy.rules.{0}';
    const patchJsonTmplt = '{"priority": {0}}';
    const p1Url = patchUrlTmplt.format(i1);
    const p2Url = patchUrlTmplt.format(i2);
    const p1Json = patchJsonTmplt.format(p2);
    const p2Json = patchJsonTmplt.format(p1);
    const animWrpEl = document.getElementById('animation-wrapper');
    if (typeof animWrpEl !== 'undefined') animWrpEl.classList.add('saving-animate');
    sendData('PATCH', 'api', p1Url, p1Json, true, function(resp) {
        if (resp < 1) {
            alert('There was a problem patching the data!');
            tidyUp();
        }//end error
        else {
            sendData('PATCH', 'api', p2Url, p2Json, true, function(resp) {
                tidyUp();
                if (resp < 1) {
                    alert('There was a problem patching the data!');
                }//end error
            });//end send 
        }//end else
    });//end send
}//end rule priority switch

function tidyUp() {
    const animWrpEl = document.getElementById('animation-wrapper');
    if (typeof animWrpEl !== 'undefined') animWrpEl.classList.remove('saving-animate');
}//end tidy up