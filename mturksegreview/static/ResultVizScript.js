let app_state;

let debug_console;

let state_button;
let batch_summary_refresh_button;
let pull_new_results_button;
let next_image_button;

let batch_summary_page;
let batch_summary_div;

let annotation_review_page;
let current_image_summary_label;

let result_pull_summary;

let current_hit_id;
let current_assignment_id;

// Establish references to the drawing surfaces
let parent = document.getElementById("parent");
let child = document.getElementById("child");
let canvas = document.getElementById("myCanvas");
let ctx = canvas.getContext("2d");
let img = document.getElementById("pic");

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
    app_state = "batch_summary";
    debug_console = document.getElementById("debug_console");

    state_button = document.getElementById("state_button");
    batch_summary_refresh_button = document.getElementById("batch_summary_refresh_button");
    pull_new_results_button = document.getElementById("pull_new_results_button");
    next_image_button = document.getElementById("next_image_button");

    batch_summary_page = document.getElementById("batch_summary_page");
    batch_summary_div = document.getElementById("batch_summary_div");
    annotation_review_page = document.getElementById("annotation_review_page");

    result_pull_summary = document.getElementById("result_pull_summary");
    current_image_summary_label = document.getElementById("current_image_summary_label");

    change_state("batch_summary");
    refresh_batch_summary();

    state_button.addEventListener("click", function () {
        debug_console.innerHTML = "State button clicked";
        if (app_state === "batch_summary") {
            change_state("annotation_review");
        } else if (app_state === "annotation_review") {
            change_state("batch_summary");
        }
    });

    batch_summary_refresh_button.addEventListener("click", function () {
        debug_console.innerHTML = "Refresh button clicked";
        refresh_batch_summary();
    });

    pull_new_results_button.addEventListener("click", function () {
        debug_console.innerHTML = "Pull new results button clicked";
        pull_new_results();
    });

    next_image_button.addEventListener("click", function () {
        debug_console.innerHTML = "Next image button clicked";
        loadNextHit(false);
    });

    window.addEventListener("keydown", hotKeys, true);
}



function change_state(state) {
    app_state = state;
    update_state_buttons(state);
    display_page(state);
}


function update_state_buttons(state) {
/**
 * Update the state button to reflect the updated state.
 * @param {string} state - The updated state of the app.
 */
    if (state === "batch_summary") {
        state_button.value = "Review Annotations";
    } else if (state === "annotation_review") {
        state_button.value = "View Batch Summary";
    }
}


function display_page(state) {
/**
 * Display the page corresponding to the updated state.
 * @param {string} state - The updated state of the app.
 */
    if (state === "batch_summary") {
        batch_summary_page.style.display = "block";
        annotation_review_page.style.display = "none";
    } else if (state === "annotation_review") {
        batch_summary_page.style.display = "none";
        annotation_review_page.style.display = "block";
    }
}


function refresh_batch_summary() {
/**
 * Calls the Python app to sync the batch result database with Mechanical Turk
 * Then queries each batch and displays the number of approved, submitted, and open assignments for each HIT
 */
    debug_console.innerHTML = "Refreshing batch summary data...";

    fetch('/call_refresh_batch_summary', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        display_batch_summary(data.result);
        debug_console.innerHTML = "Batch summary data up to date.";
    })
    .catch((error) => {
        debug_console.innerHTML = error;
    });
}


function display_batch_summary(batch_summary_data) {
    let batches = Object.keys(batch_summary_data);
    for (let batch of batches) {
        let batch_summary = batch_summary_data[batch];
        
        // Create a new label for each batch
        let batch_summary_label = create_batch_summary_label(batch, batch_summary);

        // Add the batch_summary_label to the page
        batch_summary_div.appendChild(batch_summary_label);
    }
}


function create_batch_summary_label(batch_name, batch_summary) {
/**
 * Creates a label with the batch name and the number of approved, submitted, and open assignments for each HIT
 * @param {string} batch_name - The name of the batch.
 * @param {object} batch_summary - The batch summary data.
 * @return the label containing the batch summary data.
 */

    // Get the data for the production HITs of this batch
    let summary_production = batch_summary.production;
    let prod_posted = summary_production.posted;
    let prod_approved = summary_production.approved;
    let prod_rejected = summary_production.rejected;
    let prod_outstanding = summary_production.outstanding;

    // Get the data for the sandbox HITs of this batch
    let summary_sandbox = batch_summary.sandbox;
    let sandbox_posted = summary_sandbox.posted;
    let sandbox_approved = summary_sandbox.approved;
    let sandbox_rejected = summary_sandbox.rejected;
    let sandbox_outstanding = summary_sandbox.outstanding;

    // Create the label
    let batch_summary_label = document.createElement("label");
    batch_summary_label.innerHTML = "Batch: <b>" + batch_name + "</b>"
        + "<br><u>Production:</u> " 
        + prod_posted + " posted<br>"
        + prod_approved + " approved, " 
        + prod_rejected + " rejected, "
        + prod_outstanding + " open<br><u>Sandbox:</u> " 
        + sandbox_posted + " posted<br>"
        + sandbox_approved + " approved, " 
        + sandbox_rejected + " rejected, "
        + sandbox_outstanding + " open";

    // Apply label styling
    batch_summary_label.style.width = "320px";
    batch_summary_label.style.marginLeft = "10px";
    batch_summary_label.style.marginTop = "10px";
    batch_summary_label.style.outline = "1px solid black";
    batch_summary_label.style.backgroundColor = "#D3D3D3";
    batch_summary_label.style.fontSize = "15px";

    return batch_summary_label;
}


function display_result_pull_summary(results) {
    let num_assignments_under_review = results.num_assignments_under_review;
    let num_auto_rejected = results.num_auto_rejected;
    result_pull_summary.innerHTML = "Pulled " + num_assignments_under_review + " new assignments.<br>" + num_auto_rejected + " assignments were auto-rejected due to empty responses.";
}


function pull_new_results() {
/**
 * Calls the python app to pull a new set of submitted results from mechanical turk
 * The python app will update the batch result database with the new results
 * The python app will indicate how many new results were pulled and how many were auto-rejected due to empty responses
 */
    debug_console.innerHTML = "Pulling new submitted assignments...";

    fetch('/call_pull_new_result_set', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        display_result_pull_summary(data.result);
        debug_console.innerHTML = "Pulled a new batch of results.";
    })
    .catch((error) => {
        debug_console.innerHTML = error;
    });
}


function loadNextHit(selectQual) {
/**
 * Loads the next image in the batch result database into the annotation review page
 */

    function_call = '/call_get_next_result_to_review';
    if (selectQual) {
        function_call = '/call_get_next_qualifier_result_to_review';
    }

    // Reset the drawing variables
    resetDrawingData();
    
    debug_console.innerHTML = "Loading next image...";

    fetch(function_call, {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {

        hit_data = loadHitData(data);
        img_url = hit_data[0];
        loadImage(img_url);
        debug_console.innerHTML = "Loaded next image.";

        class_list = hit_data[1];


        // Load the current annotations
        let ann_in_progress_str = data.result.annotation_in_progress;
        ann_in_progress_str = fixJsonStringQuotes(ann_in_progress_str);
        let ann_in_progress;
        try {
            ann_in_progress = JSON.parse(ann_in_progress_str);
            loadAnnotations(ann_in_progress, "current");
            debug_console.innerHTML = "Loaded current annotations.";
        } catch (e) {
            debug_console.innerHTML = "Error loading current annotations: " + e;
        }

        // load the final annotations
        let ann_final_str = data.result.annotation_final;
        ann_final_str = fixJsonStringQuotes(ann_final_str);
        let ann_final;
        try {
            ann_final = JSON.parse(ann_final_str);
            loadAnnotations(ann_final, "final");
            debug_console.innerHTML += "<br><br>Loaded final annotations.";
        } catch (e) {
            debug_console.innerHTML += "<br><br>Error loading final annotations: " + e;
        }

        // Show the annotations
        loadClassColors(class_list);
        //debug_console.innerHTML = "Loaded class colors.";

        updateGraphics();
        debug_console.innerHTML = "Updated graphics.";
        debug_console.innerHTML = "Ann in progress string:<br>" + ann_in_progress_str + "<br><br>Ann final string:<br>" + ann_final_str + "<br><br>Current object:<br>" + JSON.stringify(currentObject) + "<br><br>Annotations:<br>" + JSON.stringify(annotations);

    })
    .catch((error) => {
        debug_console.innerHTML = error;
    });
}


function loadHitData(data) {
        // Get the important assignment parameters
        let hit_id = data.result.hit_id;
        let assignment_id = data.result.assignment_id;
        let ann_mode = data.result.annotation_mode;
        let class_list = data.result.classes;
        let exp_group = data.result.exp_group;
        let auto_approve_time = data.result.auto_approve_time;

        current_hit_id = hit_id;
        current_assignment_id = assignment_id;
    
        // Fill the summary label with key HIT properties
        current_image_summary_label.innerHTML = "<b>HIT ID:</b> " + current_hit_id 
        + "<br><b>Experiment Group:</b> " + exp_group 
        + "<br><b>Auto-Approve Time:</b> " + auto_approve_time 
        + "<br><b>Annotation Mode:</b> " + ann_mode 
        + "<br><b>Classes:</b> " + class_list;

        // Show the image
        let img_url = data.result.image_url;
        return [img_url, class_list];
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


function markCurrentLineAsGood() {
    debug_console.innerHTML = "Marking current line as good...";

    if (current_hit_id != null && current_assignment_id != null) {
        let argToSend = {'hit_id': current_hit_id, 'assignment_id': current_assignment_id};

        fetch('/call_mark_current_qual_record_as_good', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(argToSend)
        })
        .then(response => response.json())
        .then(data => {
    
        })
        .catch((error) => {
            debug_console.innerHTML = error;
        });

    } else {
        debug_console.innerHTML = "Error approving current HIT: hit id or assignment_id is null";
    }
}


function markCurrentLineAsBad() {
    debug_console.innerHTML = "Marking current line as bad...";

    if (current_hit_id != null && current_assignment_id != null) {
        let argToSend = {'hit_id': current_hit_id, 'assignment_id': current_assignment_id};

        fetch('/call_mark_current_qual_record_as_bad', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(argToSend)
        })
        .then(response => response.json())
        .then(data => {
    
        })
        .catch((error) => {
            debug_console.innerHTML = error;
        });

    } else {
        debug_console.innerHTML = "Error approving current HIT: hit id or assignment_id is null";
    }
}


function approveCurrentLine() {

    debug_console.innerHTML = "Approving current line...";

    if (current_hit_id != null) {
        let argToSend = {'hit_id': current_hit_id};

        fetch('/call_approve_current_record', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(argToSend)
        })
        .then(response => response.json())
        .then(data => {
    
        })
        .catch((error) => {
            debug_console.innerHTML = error;
        });
    
        current_hit_id = null;
        current_assignment_id = null;
    } else {
        debug_console.innerHTML = "Error approving current HIT: hit id is null";
    }
}


function rejectCurrentLineTooInaccurate() {

    debug_console.innerHTML = "Rejecting current line...";

    if (current_hit_id != null) {
        let argToSend = {'hit_id': current_hit_id};

        fetch('/call_reject_current_record_too_inaccurate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(argToSend)
        })
        .then(response => response.json())
        .then(data => {
    
        })
        .catch((error) => {
            debug_console.innerHTML = error;
        });
    
        current_hit_id = null;
        current_assignment_id = null;
    } else {
        debug_console.innerHTML = "Error rejecting current HIT: hit id is null";
    }
}


function rejectCurrentLineTooFew() {

    debug_console.innerHTML = "Rejecting current line...";

    if (current_hit_id != null) {
        let argToSend = {'hit_id': current_hit_id};

        fetch('/call_reject_current_record_too_few', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(argToSend)
        })
        .then(response => response.json())
        .then(data => {
    
        })
        .catch((error) => {
            debug_console.innerHTML = error;
        });
    
        current_hit_id = null;
        current_assignment_id = null;
    } else {
        debug_console.innerHTML = "Error rejecting current HIT: hit id is null";
    }
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


function loadImage(img_url) {
/**
 * Reads the image url from the csv line and loads it into the image element
 * @param {Object} img_url - The image url to load.
 **/
    img.setAttribute("src", img_url);
    canvas.width = img.width;
    canvas.height = img.height;
}


function hotKeys(evt) {
    /**
     * A keyboard listener that rejects or approves an image based on keystrokes
     * @param {Object} evt - The keystroke event
     **/

    // Press A to mark the current image as approved
    if (evt.key == "a") {
        approveCurrentLine();
        debug_console.innerHTML = "Approved current line";
        loadNextHit(false);
    // Press R to mark the current image as rejected
    } else if (evt.key == "r") {
        rejectCurrentLineTooInaccurate();
        debug_console.innerHTML = "Rejected current line - too inaccurate";
        loadNextHit(false);

    } else if (evt.key == "f") {
        rejectCurrentLineTooFew();
        debug_console.innerHTML = "Rejected current line - too few annotations";
        loadNextHit(false);
    } else if (evt.key == "n") {
        loadNextHit(false);
    } else if (evt.key == "q") {
        loadNextHit(true);
    } else if (evt.key == "g") {
        markCurrentLineAsGood();
        debug_console.innerHTML = "Marked current line as good";
        loadNextHit(true);
    } else if (evt.key == "b") {
        markCurrentLineAsBad();
        debug_console.innerHTML = "Marked current line as bad";
        loadNextHit(true);
    }
}


function resetDrawingData() {
/**s
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
    debug_console.innerHTML = "entered updateGraphics()";

    // Remove the prior annotations and replace with the updated annotations
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    debug_console.innerHTML = "cleared canvas";

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


function showAnns(show) {
/**
 * Sets the showAnnotations variable, which dictates whether annotations are displayed on the image
 * @param {boolean} show: whether to show the annotations
 **/
    showAnnotations = show;
    updateGraphics();
}


window.addEventListener('DOMContentLoaded', start, false);