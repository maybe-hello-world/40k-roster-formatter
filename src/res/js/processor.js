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

    let result;
    const url = "/api/formatter";

    try {
        const formData = new FormData(form);
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });

        result = await response.text();
    } catch (error) {
        result = await error.text();
    }
    let out = document.getElementById("output");
    out.textContent = result;

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