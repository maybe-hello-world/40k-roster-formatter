// $.post('/api/formatter/formatter.py', {query: 'test'}, function(data) {
//     console.log(data); // ответ от сервера
// })
// .success(function() { console.log('Успешное выполнение'); })
// .error(function(jqXHR) { console.log('Ошибка выполнения'); })
// .complete(function() { console.log('Завершение выполнения'); });


let xhr = new XMLHttpRequest();
xhr.open('POST','/api/formatter/formatter.py');
xhr.responseType = 'json';
xhr.send();

xhr.onload = function() {
  if (xhr.status != 200) { // анализируем HTTP-статус ответа, если статус не 200, то произошла ошибка
    alert(`Ошибка ${xhr.status}: ${xhr.statusText}`); // Например, 404: Not Found
  } else { // если всё прошло гладко, выводим результат
    alert(`Готово, получили ${xhr.response.length} байт`); // response -- это ответ сервера
  }
};

xhr.onprogress = function(event) {
  if (event.lengthComputable) {
    alert(`Получено ${event.loaded} из ${event.total} байт`);
  } else {
    alert(`Получено ${event.loaded} байт`); // если в ответе нет заголовка Content-Length
  }

};

xhr.onerror = function() {
  alert("Запрос не удался");
};
