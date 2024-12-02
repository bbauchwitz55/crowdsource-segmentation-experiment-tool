let socket = io(); //"http://127.0.0.1:5000"
let canvas;
let ctx;
let debug_console;


// Data for drawing annotations in a way consistent with the study script
let showAnnotations = true;
let currentLink;
let currentPolygon;
let currentBbox;
let currentOutline;
let currentPaint;
let currentObject;
let eraser_mode = false;
let classes = {};
let colors = {};
let annotations = [];



function start() {

    debug_console = document.getElementById('debug_console');
    debug_console.innerHTML = "Created debug console";

    debug_console.innerHTML = "Created socket";

    canvas = document.getElementById('myCanvas');
    debug_console.innerHTML = "Created canvas";

    ctx = canvas.getContext('2d');
    debug_console.innerHTML = "Created context";

    //let debug_console = document.getElementById('debug_console');
    debug_console.innerHTML = "Initialized page";

    // Load the class colors - it is important that the colors be the same every time so that the masks are consistent
    class_data = "airplane-backpack-bicycle-boat-bus-car-cat-dog-motorcycle-person-train-truck";
    loadClassColors(class_data);
    debug_console.innerHTML = "Loaded class colors";

}


//const socket = io.connect('http://' + document.domain + ':' + location.port);

socket.on('connect', function() {
    console.log('Connected to the server');
    debug_console.innerHTML = "Connected to the server";
});


socket.on('update_data', function(data) {
    // Render the data on the canvas
    console.log('--Front end: Received data from server');
    debug_console.innerHTML = "Received data from server";

    // Parse the input data
    let assignment_id = data.assignment_id;
    let offset_index = data.offset_index;
    let image_width = parseInt(data.img_width);
    let image_height = parseInt(data.img_height);

    debug_console.innerHTML = "Image width: " + image_width + " Image height: " + image_height + " Cavnas: " + canvas;

    // Load the current annotations
    let ann_in_progress_str = data.ann_in_progress;
    ann_in_progress_str = fixJsonStringQuotes(ann_in_progress_str);
    let ann_in_progress;
    try {
        ann_in_progress = JSON.parse(ann_in_progress_str);
        loadAnnotations(ann_in_progress, "current");
        debug_console.innerHTML = "Loaded current annotations.";
    } catch (e) {
        debug_console.innerHTML = "Error loading current annotations: " + e;
    }

    // Load the final annotations
    let ann_final_str = data.ann_final;
    ann_final_str = fixJsonStringQuotes(ann_final_str);
    let ann_final;
    try {
        ann_final = JSON.parse(ann_final_str);
        loadAnnotations(ann_final, "final");
        debug_console.innerHTML = "Loaded final annotations.";
    } catch (e) {
        debug_console.innerHTML = "Error loading final annotations: " + e;
    }

    // Your canvas rendering logic here using the data
    // Set the canvas size to the image size and fill with all black pixels
    canvas.width = image_width;
    canvas.height = image_height;
    debug_console.innerHTML = ann_in_progress_str + "<br><br>" + ann_final_str;
    updateGraphics()

    // Once rendered, send the canvas image back to the server
    let classMaskURL = canvas.toDataURL('image/png');

    resetDrawingData();

    //
    //
    // TODO: also need to get the instance mask and add that to the returned data
    //
    //

    // Pass the relevant data back to the server
    socket.emit('canvas_image', { "class_mask": classMaskURL, "offset_index": offset_index, "assignment_id": assignment_id });
    console.log('--Front end: Sent data to server');
});


function send_png_to_flask() {
    let dataURL = canvas.toDataURL('image/png');

    fetch('/upload', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ image: dataURL })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.message);
    });
}


function fixJsonStringQuotes(json_string) {
/**
 * Fixes the quotes in a JSON string so that it can be parsed into a JSON object
 * @param {string} json_string - The JSON string to fix.
 * @return the fixed JSON string.
 */
    if (json_string === null) {
        return null;
    }
    let fixed_json_string = json_string.replace(/'/g, '"');
    return fixed_json_string;
}


function loadAnnotations(anns, kind) {
/**
 * Reads the HIT results and saves the current and final annotation data to the appropriate drawing variables
 * @param {Object} line - The line of the csv file that contains the HIT data
 * @param {String} kind - The type of annotation to be loaded: "current" or "final"
 **/

    // If current annotations were found, set the appropriate drawing variables and print a summary of the annotations
    if (anns != null && kind == "current") {

        for (let ann of anns) {
            if (Object.hasOwn(ann, "mode") && ann.mode === "polygon") {
                currentPolygon = ann;
            } else if (Object.hasOwn(ann, "mode") && ann.mode === "bbox") {
                currentBbox = ann;
            } else if (Object.hasOwn(ann, "mode") && ann.mode === "outline") {
                currentOutline = ann;
            } else if (Object.hasOwn(ann, "mode") && ann.mode === "link") {
                currentLink = ann;
            } else if (Object.hasOwn(ann, "mode") && ann.mode === "paint") {
                currentPaint = ann;
            } else if (Object.hasOwn(ann, "modes") && Object.hasOwn(ann, "strokes")) {
                currentObject = ann;
            } else {
                debug_console.innerHTML = "Encountered an unrecognized annotation type";
            }
        }

    // If final annotations were found, set the appropriate drawing variables and print a summary of the annotations
    } else if (anns != null && kind == "final") {
        annotations = anns;
    
    // If no annotations were found for the given query, print a message
    } else {
        debug_console.innerHTML += "<br" + kind + " annotations is null";
    }
}


function resetDrawingData() {
/**
 * Resets the drawing variables to their initial values
 **/
    currentLink = null;
    currentBbox = null;
    currentPolygon = null;
    currentOutline = null;
    currentPaint = null;
    currentObject = null;
    eraser_mode = false;
    colors = {};
    classes = {};
    annotations = [];
    //showAnns(true);
}



function drawBbox(annotation, options) {
/**
 * Draws a bounding box annotation
 * @param annotation: the annotation to be rendered
 * @param options: indicates whether the annotation is being hovered over in delete mode and whether the annotation is currently being drawn
 **/
    const [r, g, b] = getColor(annotation, options);
    ctx.fillStyle = "rgba(1, 1, 1, 0)";
    if (eraser_mode) {
        ctx.strokeStyle = "rgba(1, 1, 1, 1)";
    } else {
        ctx.strokeStyle = "rgba(" + r + "," + g + "," + b + ", 1.0)";
    }
    // Always use the same globalCompositeOperation because only a current box is rendered with this method
    // Once the box is finalized, it is added to an object and rendered that way as an interior or exterior
    ctx.globalCompositeOperation = "source-over";

    // Unlike in the labeling tool, the visualization script only considers bounding boxes with two fixed corners
    if (annotation.data.length == 2) {
        const xmin = annotation.data[0][0];
        const ymin = annotation.data[0][1];
        const xmax = annotation.data[1][0];
        const ymax = annotation.data[1][1];
        const corners = [
            [xmin, ymin],
            [xmax, ymin],
            [xmax, ymax],
            [xmin, ymax],
        ];
        fillPolygon(corners);
    }
}


function drawPolygonOutline(corners) {
/**
 * Draws the outline of a polygon
 * @param corners: the corners of the polygon to be drawn
 **/

    let dotSize = 4;
    for (let j = 0; j < corners.length; j++) {
        ctx.fillRect(
            corners[j][0] - dotSize / 2,
            corners[j][1] - dotSize / 2,
            dotSize,
            dotSize
        );
    }
    ctx.beginPath();
    ctx.moveTo(corners[0][0], corners[0][1]);
    for (let j = 1; j < corners.length; j++) {
        ctx.lineTo(corners[j][0], corners[j][1]);
        ctx.stroke();
    }
    ctx.stroke();
    ctx.closePath();
}


function fillPolygon(corners) {
/**
 * Fills the polygon defined by the corners with the current color
 * @param corners: the corners of the polygon to be filled
 **/
    ctx.beginPath();
    ctx.moveTo(corners[0][0], corners[0][1]);
    for (let j = 1; j < corners.length; j++) {
        ctx.lineTo(corners[j][0], corners[j][1]);
        ctx.stroke();
    }
    ctx.lineTo(corners[0][0], corners[0][1]);
    ctx.stroke();
    ctx.closePath();
    ctx.fill();
}


function drawPolygon(annotation, options) {
/**
 * Draws a polygon annotation
 * @param annotation: the annotation to be rendered
 * @param options: indicates whether the annotation is being hovered over in delete mode and whether the annotation is currently being drawn
 **/
    debug_console.innerHTML = "entered drawPolygon()";
    const [r, g, b] = getColor(annotation, options);
    debug_console.innerHTML = "got color";
    const corners = annotation.data;
    debug_console.innerHTML = "got corners";
    ctx.fillStyle = "rgba(" + r + "," + g + "," + b + ", " + 0.5 + ")";
    debug_console.innerHTML = "set fill style";
    if (eraser_mode) {
        ctx.strokeStyle = "rgba(1, 1, 1, 1)";
    } else {
        ctx.strokeStyle = "rgba(" + r + "," + g + "," + b + ", " + 0.5 + ")";
    }      
    debug_console.innerHTML = "set stroke style";
    if (options.current) {
        // Shapes that are in proress are drawn as solid, and then become transparent once they are finalized
        // The globalCompositeOperation is set to source-over to ensure that the shape is drawn on top of other shapes
        ctx.globalCompositeOperation = "source-over";
        debug_console.innerHTML = "set globalCompositeOperation";
        drawPolygonOutline(corners);
    } else {
        fillPolygon(corners);
    }
}


function drawPoints(corners, options) {
/**
 * Fills the shape enclosed by a set of points
 * @param corners: the points that enclose the shape
 * @param options: indicates whether the annotation is being hovered over in delete mode and whether the annotation is currently being drawn
 **/
    
    // If drawing a single point
    if (corners.length == 1) {
        ctx.fillRect(
            corners[0][0],
            corners[0][1],
            1,
            1
        );
    
    // If drawing a line
    } else if (corners.length == 2) {
        ctx.strokeStyle = "rgba(" + r + "," + g + "," + b + ", " + 0.5 + ")";
        ctx.beginPath();
        ctx.moveTo(corners[0][0], corners[0][1]);
        ctx.lineTo(corners[1][0], corners[1][1]);
        ctx.closePath();
        ctx.stroke();
    
    // If drawing a shape with three or more points
    } else {
        fillPolygon(corners);
    }
}


function drawObject(object, options) {
/**
 * Function that is called to draw an object, which may include multiple component annotations
 * Each object may include both positive and negative (erasure) marks
 * @param object: the object to be rendered
 * @param options: indicates whether the annotation is being hovered over in delete mode and whether the annotation is currently being drawn
 **/

    const [r, g, b] = getColor(object, options);
    if (options.current) {
        ctx.fillStyle = "rgba(" + r + "," + g + "," + b + ", " + 0.5 + ")";
        ctx.globalCompositeOperation = "source-over";
    } else {
        ctx.fillStyle = "rgba(" + r + "," + g + "," + b + ", " + 0.5 + ")";
        ctx.globalCompositeOperation = "xor";     // "source-over";
    }

    // Draw the strokes in order so that later strokes are overlaid on top of earlier strokes
    for (let stroke of object.strokes) {

        // Set the fill style, stroke style, and global composite operation based on the type of stroke
        // Positive strokes are filled in portions of the annotation
        if (stroke.type == "positive") {

            // If the annotation is currently being worked on, fill and composite are set so that this is drawn on top
            if (options.current) {
                ctx.fillStyle = "rgba(" + r + "," + g + "," + b + ", " + 0.5 + ")";
                ctx.globalCompositeOperation = "source-over";
            
            // If the annotation is complete, fill and composite are set so that it is transparent and overlaid on the other annotations
            } else {
                ctx.fillStyle = "rgba(" + r + "," + g + "," + b + ", " + 0.5 + ")";
                ctx.globalCompositeOperation = "xor";     // "source-over";
            }
            ctx.strokeStyle = "rgba(" + r + "," + g + "," + b + ", " + 0 + ")";

        // Negative strokes are treated erasures of portions of the annotation
        // An erasure eliminates all drawn pixels below it, including from preceding annotations, though the data is still stored for those
        } else if (stroke.type == "negative") {

            // For an erasure, fill and composite are always set to remove the drawn pixels underneath
            ctx.fillStyle = "rgba(" + 0 + "," + 0 + "," + 0 + ", " + 1 + ")";
            ctx.strokeStyle = "rgba(" + 0 + "," + 0 + "," + 0 + ", " + 1 + ")";
            ctx.globalCompositeOperation = "destination-out";
        }

        // Draw the points of the stroke as a shape
        const corners = stroke.points;
        drawPoints(corners, options);
    }
}


function updateGraphics() {
/**
 * Draws the annotations on the image
 **/
    //debug_console.innerHTML = "entered updateGraphics()";

    // Remove the prior annotations and replace with the updated annotations
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "black";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    //debug_console.innerHTML = "cleared canvas";

    if (showAnnotations) {
        // Draw  the completed annotations
        annotations.forEach((ann, idx) => {
            drawObject(ann, { current: false, idx });
        });

        // Draw an in-progress bounding box, if it exists
        if (currentBbox.data.length != 0) {
            drawBbox(currentBbox, { current: true });
        }

        // Draw an in-progress polygon, if it exists
        if (currentPolygon.data.length != 0) {
            debug_console.innerHTML = "drawing currentPolygon";
            drawPolygon(currentPolygon, { current: true });
        }

        // Draw an in-progress outline, if it exists
        if (currentOutline.data.length != 0) {
            debug_console.innerHTML = "drawing currentOutline";
            drawPolygon(currentOutline, { current: true });
        }

        // Draw the initial shapes of an in-progress object that has not been finalized
        if (currentObject.strokes.length != 0) {
            debug_console.innerHTML = currentObject.class;
            drawObject(currentObject, { current: true });
        }
    }

    //debug_console.innerHTML = "finished updateGraphics()";
}


function getColor(annotation, options) {
/**
 * Determines which color to rener an annotation based on its class and the current annotation state
 * @param annotation: the annotation to be rendered
 * @param options: indicates whether the annotation is being hovered over in delete mode
 **/
    return className2Color(annotation.class);
}




function HSVtoRGB(h, s, v) {
/**
 * Converts an HSV color to RGB
 * Borrowed from https://stackoverflow.com/a/17243070/4970438
 * @param {number} h: the hue
 * @param {number} s: the saturation
 * @param {number} v: the value
 **/
    let r, g, b, i, f, p, q, t;
    if (arguments.length === 1) {
        (s = h.s), (v = h.v), (h = h.h);
    }
    i = Math.floor(h * 6);
    f = h * 6 - i;
    p = v * (1 - s);
    q = v * (1 - f * s);
    t = v * (1 - (1 - f) * s);
    switch (i % 6) {
        case 0:
            (r = v), (g = t), (b = p);
            break;
        case 1:
            (r = q), (g = v), (b = p);
            break;
        case 2:
            (r = p), (g = v), (b = t);
            break;
        case 3:
            (r = p), (g = q), (b = v);
            break;
        case 4:
            (r = t), (g = p), (b = v);
            break;
        case 5:
            (r = v), (g = p), (b = q);
            break;
    }
    return {
        r: Math.round(r * 255),
        g: Math.round(g * 255),
        b: Math.round(b * 255),
    };
}


function loadClassColors(classData) {
/**
 * Gets the colors of the classes depicted in the HIT
 * @param {Object} line - The line of the csv file that contains the HIT data
 **/

    // Parse the classes input into a dictionary of class name to class index
    let classList = classData.split("-");

    for (let i = 0; i < classList.length; i++) {
        let key = classList[i];
        classes[key] = i;
    }

    // For each class in the class list, add it to the class list selector element and assign a unique color for visualizing annotations of that class
    for (var theClass in classes) {
        let codeName = "class" + classes[theClass];
        let hue = Math.abs(hashCode(codeName) % 360) / 360;
        let color = [hue, 1.0, 1.0];
        colors[theClass] = color;
    }
}


function className2Color(className) {
/**
 * Queries the class name for the corresponding HSV olor and then converts to RGB
 * @param {string} className: the class name
 **/
    let color = colors[className];
    let h = color[0];
    let s = color[1];
    let v = color[2];
    let rgbColors = HSVtoRGB(h, s, v);
    let r = rgbColors.r.toString();
    let g = rgbColors.g.toString();
    let b = rgbColors.b.toString();
    return [r, g, b];
}


function hashCode(str) {
/**
 * Hashes an object class name to a unique number that is used to derive the color for displaying the annotations for that class
 * @param {string} str: the class name
 **/
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash += Math.pow(str.charCodeAt(i) * 31, str.length - i);
        hash = hash & hash; // Convert to 32bit integer
    }
    return hash;
}


window.addEventListener('DOMContentLoaded', start, false);

