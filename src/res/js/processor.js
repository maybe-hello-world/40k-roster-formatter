/*jshint esversion: 8 */
/* global console*/

function copyToClipboard() {
    "use strict";
    let copytext = document.getElementById("output").innerText;
    navigator.clipboard.writeText(copytext).then(function () {
    }, function (err) {
        console.error("Could not copy text", err);
    });
}

document.getElementById("roster").onchange = async (e) => {
    "use strict";
    // UI
    document.getElementById("copyBtn").disabled = true;
    document.getElementById("copyBtn").textContent = "Uploading...";

    e.preventDefault();
    const form = document.getElementById("bsdataform");

    let info, debug_text;
    const url = "/api/formatter";

    try {
        const formData = new FormData(form);
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });

        let result = await response.json();
        info = result.info;
        debug_text = result.debug;
    } catch (error) {
        info = await error.text();
        debug_text = "";
    }
    let out = document.getElementById("output");
    out.textContent = info;
    debug_text.split(/\r?\n/).forEach(function (line) {
        console.log(line);
    });


    document.getElementById("copyBtn").disabled = false;
    document.getElementById("copyBtn").textContent = "Copy to clipboard";
};

document.getElementById('formats').onchange = async (e) => {
    "use strict";
    let minimize = document.getElementById('hide_basic_selections');
    let secondaries = document.getElementById('show_secondaries');
    let costs = document.getElementById('remove_costs');
    let model_count = document.getElementById('show_model_count');

    switch (e.target.value) {
        case 'default':
            minimize.checked = true;
            secondaries.checked = true;
            costs.checked = false;
            model_count.checked = false;
            break;
        case 'wtc':
            minimize.checked = true;
            secondaries.checked = true;
            costs.checked = false;
            model_count.checked = true;
            break;
        case 'rus':
            minimize.checked = true;
            secondaries.checked = true;
            costs.checked = false;
            model_count.checked = false;
            break;
    }
};