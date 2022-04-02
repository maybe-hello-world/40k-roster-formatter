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

document.getElementById("bsdataform").onsubmit = async (e) => {
    "use strict";
    // UI
    document.getElementById("copyBtn").disabled = true;
    document.getElementById("uploadBtn").disabled = true;
    document.getElementById("uploadSpan").style.display = 'inline-block';
    document.getElementById("submitText").textContent = "Uploading...";

    e.preventDefault();
    const form = e.currentTarget;

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
    document.getElementById('uploadBtn').disabled = false;
    document.getElementById("uploadSpan").style.display = 'none';
    document.getElementById("submitText").textContent = "Upload";
};