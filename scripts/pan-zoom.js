const dict = {
        scale: 1,
        panning: false,
        pointX: 0,
        pointY: 0,
        start: { x: 0, y: 0 }
    };
let dicts = {};    
function setTransform(zoomable) {
    const bbox = zoomable.parentElement.getBoundingClientRect();
    const bboxWidth = bbox.width;
    const bboxHeight = bbox.height;
    let dict = dicts[zoomable.id];
    dict.scale = Math.min(Math.max(1, dict.scale), 4);
    const maxHorExtent = (dict.scale - 1) * bboxWidth;
    const maxVertExtent = (dict.scale - 1) * bboxHeight;
    dict.pointX = Math.min(0, Math.max(-maxHorExtent, dict.pointX));
    dict.pointY = Math.min(0, Math.max(-maxVertExtent, dict.pointY));
    zoomable.style.transform = "translate(" + dict.pointX + "px, " + dict.pointY + "px) scale(" + dict.scale + ")";
}
function startPan(e){
    let dict = dicts[this.id];
    dict.start = { x: e.clientX - dict.pointX, y: e.clientY - dict.pointY };
    dict.panning = true;
    this.addEventListener('mousemove', handlePan, false);
    this.addEventListener('mouseup', finishPan, false);
}//end start pan
function handlePan(e){
    e.preventDefault();
    let dict = dicts[this.id];
    if (!dict.panning) {
        return;
    }
    dict.pointX = (e.clientX - dict.start.x);
    dict.pointY = (e.clientY - dict.start.y);
    setTransform(this);        
}//end handle pan
function finishPan(){
    let dict = dicts[this.id];
    dict.panning = false;
    this.removeEventListener('mousemove', handlePan, false);
    this.removeEventListener('mouseup', finishPan, false);
}//end finish pan
[...document.getElementsByClassName("zoomable")].forEach(function(zoomable) {
    dicts[zoomable.id] = dict;
    zoomable.addEventListener('mousedown', startPan, false);
    zoomable.addEventListener('wheel', function(e) {
        e.preventDefault();
        let dict = dicts[this.id];
        const clientX = e.clientX - this.parentElement.getBoundingClientRect().x,
            clientY = e.clientY - this.parentElement.getBoundingClientRect().y;
        const xs = (clientX - dict.pointX) / dict.scale,
            ys = (clientY - dict.pointY) / dict.scale,
            delta = (e.wheelDelta ? e.wheelDelta : -e.deltaY);
        (delta > 0) ? (dict.scale *= 1.2) : (dict.scale /= 1.2);
        dict.pointX = clientX - xs * dict.scale;
        dict.pointY = clientY - ys * dict.scale;
        setTransform(this);
    },false);
});
