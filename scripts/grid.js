class Grid {

    constructor(targetsTableId) {
        this.tgtId = targetsTableId;
    }//end constructor
           
    processBody(json) {
        const tbl_placeholder = document.getElementById(this.tgtId);
        const hdrRow = Array.from(tbl_placeholder.tHead.rows);
        const hdgs = hdrRow.map(row => Array.from(row.cells).map(cell => cell.textContent.toLowerCase()))[0];
        const newTbody = document.createElement('tbody')   
        this.populateBody(newTbody, json, hdgs);
        tbl_placeholder.replaceChild(newTbody, tbl_placeholder.tBodies[0]);
    }//end process body
    
    populateBody(tbody, bodyJson, hdgs) {
        const blankables = ["null", "None", "undefined", "-1"];
        const capitalize = ["true", "false"];
        const colCount = hdgs.length;
        const rowCount = bodyJson.length;
        for (let r = 0; r < rowCount; r++) {
            let tr = tbody.insertRow();
            for (let c = 0; c < colCount; c++) {
                const hdg = hdgs[c];
                const content = String(bodyJson[r][c]);
                //apply row-level and cell-level attributes
                const rowAtt = '@row_';
                const cellAtt = '@cell_';
                const rowAttPos = hdg.indexOf(rowAtt);
                const cellAttPos = hdg.indexOf(cellAtt);
                if (rowAttPos >= 0) {
                    //row-level attribute
                    const attName = hdg.substring(rowAttPos + rowAtt.length);
                    tr.setAttribute(attName, content);
                }//end row level attribute
                else if (cellAttPos >= 0) {
                    //previous column cell-level attribute
                    const attName = hdg.substring(cellAttPos + cellAtt.length);
                    tr.lastElementChild.setAttribute(attName, content);
                }//end cell level attribute
                
                if (!hdg.startsWith('_')) {
                    const td = tr.insertCell();
                    //graphical widget?
                    if (content.indexOf('<') != -1) {  
                        td.innerHTML = content;
                    }//end snippet exists
                    else {
                        const cellText = blankables.includes(content) ? '' : 
                            capitalize.includes(content) ? content.charAt(0).toUpperCase() + content.slice(1): 
                                content.replace(/,/g, ', ');
                        td.appendChild(document.createTextNode(cellText));
                    }//end text cell 
                }//end include
            }//next body column  
        }//next body row      
    }//end populate body json
}//end class
function isNumber(n) {
  return !isNaN(parseFloat(n)) && isFinite(n);
}