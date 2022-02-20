let formData = new FormData(document.forms.formatter);


 let xhr = new XMLHttpRequest();
 xhr.open("POST", "/api/formatter/formatter.py");
 xhr.send(formData);

 xhr.onload = () => alert(xhr.response);

