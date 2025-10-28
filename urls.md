https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains

query Parameters
locale	
string
Default: "ru"
Example: locale=ru
Язык полей ответа subjectName и warehouseName:

ru — русский
en — английский
zh — китайский. Значения warehouseName на английском
groupByBrand	
boolean
Default: false
Example: groupByBrand=true
Разбивка по брендам

groupBySubject	
boolean
Default: false
Example: groupBySubject=true
Разбивка по предметам

groupBySa	
boolean
Default: false
Example: groupBySa=true
Разбивка по артикулам продавца

groupByNm	
boolean
Default: false
Example: groupByNm=true
Разбивка по артикулам WB. Если groupByNm=true, в ответе будет поле volume

groupByBarcode	
boolean
Default: false
Example: groupByBarcode=true
Разбивка по баркодам

groupBySize	
boolean
Default: false
Example: groupBySize=true
Разбивка по размерам

filterPics	
integer
Default: 0
Example: filterPics=1
Фильтр по фото:

-1 — без фото
0 — не применять фильтр
1 — с фото
filterVolume	
integer
Default: 0
Example: filterVolume=3
Фильтр по объёму:

-1 — без габаритов
0 — не применять фильтр
3 — свыше трёх литров

200
Успешно

Response Schema: application/json
data	
object (CreateTaskResponseData)
taskId	
string
ID задания на генерацию




https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains/tasks/{task_id}/download

path Parameters
task_id
required
string
Example: 06e06887-9d9f-491f-b16a-bb1766fcb8d2
ID задания на генерацию

200
Успешно

Response Schema: application/json
Array 
brand	
string
Бренд

subjectName	
string
Название предмета

vendorCode	
string
Артикул продавца

nmId	
integer
Артикул WB

barcode	
string
Баркод

techSize	
string
Размер

volume	
number
Объём, л

warehouses	
Array of objects
Остатки на складах и товары в пути. Будут в ответе только при ненулевом quantity

Array 
warehouseName	
string
Название склада

quantity	
integer
Количество, шт.





https://statistics-api.wildberries.ru/api/v1/supplier/orders

query Parameters
dateFrom
required
string <RFC3339>
Дата и время последнего изменения по заказу.
Дата в формате RFC3339. Можно передать дату или дату со временем. Время можно указывать с точностью до секунд или миллисекунд.
Время передаётся в часовом поясе Москва (UTC+3).
Примеры:

2019-06-20
2019-06-20T23:59:59
2019-06-20T00:00:00.12345
2017-03-25T00:00:00
flag	
integer
Default: 0
Если параметр flag=0 (или не указан в строке запроса), при вызове API возвращаются данные, у которых значение поля lastChangeDate (дата время обновления информации в сервисе) больше или равно переданному значению параметра dateFrom. При этом количество возвращенных строк данных варьируется в интервале от 0 до примерно 100 000.
Если параметр flag=1, то будет выгружена информация обо всех заказах или продажах с датой, равной переданному параметру dateFrom (в данном случае время в дате значения не имеет). При этом количество возвращенных строк данных будет равно количеству всех заказов или продаж, сделанных в указанную дату, переданную в параметре dateFrom.


200
Успешно

Response Schema: application/json
Array 
date	
string <date-time>
Дата и время заказа. Это поле соответствует параметру dateFrom в запросе, если параметр flag=1. Если часовой пояс не указан, то берётся Московское время (UTC+3).

lastChangeDate	
string <date-time>
Дата и время обновления информации в сервисе. Это поле соответствует параметру dateFrom в запросе, если параметр flag=0 или не указан. Если часовой пояс не указан, то берётся Московское время (UTC+3).

warehouseName	
string <= 50 characters
Склад отгрузки

warehouseType	
string
Enum: "Склад WB" "Склад продавца"
Тип склада хранения товаров

countryName	
string <= 200 characters
Страна

oblastOkrugName	
string <= 200 characters
Округ

regionName	
string <= 200 characters
Регион

supplierArticle	
string <= 75 characters
Артикул продавца

nmId	
integer
Артикул WB

barcode	
string <= 30 characters
Баркод

category	
string <= 50 characters
Категория

subject	
string <= 50 characters
Предмет

brand	
string <= 50 characters
Бренд

techSize	
string <= 30 characters
Размер товара

incomeID	
integer
Номер поставки

isSupply	
boolean
Договор поставки

isRealization	
boolean
Договор реализации

totalPrice	
number
Цена без скидок

discountPercent	
integer
Скидка продавца, %

spp	
number
Скидка WB, %

finishedPrice	
number
Цена с учетом всех скидок, кроме суммы по WB Кошельку

priceWithDisc	
number
Цена со скидкой продавца (= totalPrice * (1 - discountPercent/100))

isCancel	
boolean
Отмена заказа:

true — заказ отменен
cancelDate	
string <date-time>
Дата и время отмены заказа. Если заказ не был отменен, то "0001-01-01T00:00:00".Если часовой пояс не указан, то берётся Московское время UTC+3.

sticker	
string
ID стикера

gNumber	
string <= 50 characters
ID корзины покупателя. Заказы одной транзакции будут иметь одинаковый gNumber

srid	
string
Уникальный ID заказа.
Примечание для использующих API Маркетплейс: srid равен rid в ответах методов сборочных заданий.



Параметры для сбора из Wildberries API
Таблица полей по эндпоинтам

Поле                   |  Эндпоинт            |  Ключ API         |  Тип данных
-----------------------+----------------------+-------------------+------------
Артикул продавца       |  /supplier/orders    |  supplierArticle  |  string    
Артикул товара (nmid)  |  /supplier/orders    |  nmId             |  integer   
Артикул продавца       |  /warehouse_remains  |  supplierArticle  |  string    
Артикул товара (nmid)  |  /warehouse_remains  |  nmId             |  integer   
Название склада        |  /warehouse_remains  |  warehouseName    |  string    
Остатки на складе      |  /warehouse_remains  |  quantity         |  integer   


Логика расчетов
Остатки:
По каждому складу: берется напрямую из quantity в /warehouse_remains для конкретной комбинации nmId + warehouseName

Всего по товару: суммируются все quantity для одного nmId со всех складов

Заказы:
Всего по товару: подсчитывается количество записей (строк) в /supplier/orders с одинаковым nmId

По складу: подсчитывается количество записей в /supplier/orders где совпадают nmId + warehouseName

Примечания
Группировка данных происходит по связке supplierArticle + nmId

Склады идентифицируются по warehouseName из обоих эндпоинтов

Для получения остатков сначала создается задача через /warehouse_remains, затем скачивается результат через /tasks/{task_id}/download