// Makes an element in an SVG document draggable.
// Fires custom `dragstart`, `drag`, and `dragend` events on the
// element with the `detail` property of the event carrying XY
// coordinates for the location of the element.
function makeDraggable(el) {
    if (!el) return console.error('makeDraggable() needs an element');
    let svg = el;
    while (svg && svg.tagName != 'svg') svg = svg.parentNode;
    if (!svg) return console.error(el, 'must be inside an SVG wrapper');
    let pt = svg.createSVGPoint(), doc = svg.ownerDocument;
    let root = doc.rootElement || doc.body || svg;
    let txStartX, txStartY, mouseStart;

    svg.addEventListener('mousemove', handlePointer, false);
    el.addEventListener('mousedown', startMove, false);

    function startMove(evt) {
        // We listen for mousemove/up on the root-most
        // element in case the mouse is not over el.
        evt.stopPropagation();
        root.addEventListener('mousemove', handleMove, false);
        root.addEventListener('mouseup', finishMove, false);

        txStartX = 0;
        txStartY = 0;
        mouseStart = inElementSpace(evt);
        eventDetail = { x: 0, y: 0 };
        fireEvent('dragstart', eventDetail, evt);
    }//end start move

    function handlePointer(evt) {
        const point = inElementSpace(evt);
        const x = point.x;
        const y = point.y;
        eventDetail = { x: x, y: y };
        const event = new Event('pointer');
        event.detail = eventDetail;
        event.sourceEvent = evt;
        return evt.currentTarget.dispatchEvent(event);
    }//end handle pointer

    function handleMove(evt) {
        const point = inElementSpace(evt);
        const x = txStartX + point.x - mouseStart.x;
        const y = txStartY + point.y - mouseStart.y;
        eventDetail = { x: x, y: y };
        fireEvent('drag', eventDetail, evt);
    }//end handle move

    function finishMove(evt) {
        root.removeEventListener('mousemove', handleMove, false);
        root.removeEventListener('mouseup', finishMove, false);
        const point = inElementSpace(evt);
        const x = txStartX + point.x - mouseStart.x;
        const y = txStartY + point.y - mouseStart.y;
        eventDetail = { x: x, y: y };
        fireEvent('dragend', eventDetail, evt);
    }//end finish move

    function fireEvent(eventName, eventDetail, sourceEvent) {
        const event = new Event(eventName);
        event.detail = eventDetail; // { x:xlate.matrix.e, y:xlate.matrix.f };
        event.sourceEvent = sourceEvent;
        return el.dispatchEvent(event);
    }//end fire event

    // Convert mouse position from screen space to coordinates of el
    function inElementSpace(evt) {
        pt.x = evt.clientX; pt.y = evt.clientY;
        return pt.matrixTransform(el.parentNode.getScreenCTM().inverse());
    }//end in element space
}//end make draggable