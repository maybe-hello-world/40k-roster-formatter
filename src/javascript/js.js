let formData = new FormData(document.forms.formatter);


 let xhr = new XMLHttpRequest();
 xhr.open("POST", "/api/formatter");
 xhr.send(formData);

 xhr.onload = () => alert(xhr.response);

xhr.upload.onprogress = function(event) {
  alert(`Отправлено ${event.loaded} из ${event.total} байт`);
};

xhr.upload.onload = function() {
  alert(`Данные успешно отправлены.`);
};

xhr.upload.onerror = function() {
  alert(`Произошла ошибка во время отправки: ${xhr.status}`);
};
