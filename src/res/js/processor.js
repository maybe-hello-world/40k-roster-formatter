let form = document.getElementById("bsdataform");
form.onsubmit = async (e) => {
    // UI
    document.getElementById("uploadBtn").disabled = true;
    document.getElementById("uploadSpan").style.display = 'inline-block';
    document.getElementById("submitText").textContent = "Uploading..."

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
    out.setAttribute('style', 'white-space: pre;');
    out.textContent = result;

    document.getElementById('uploadBtn').disabled = false;
    document.getElementById("uploadSpan").style.display = 'none';
    document.getElementById("submitText").textContent = "Upload"
}