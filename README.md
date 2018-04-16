# djing
Попытка интернет биллинга. djing сокращение от **dj**ango-bill**ing**. Это web интерфейс управления абонентами
интернет-провайдера.
Сейчас идёт тестирвоание работы на Mikrotik, функционал пока минимальный, т.к. пишу в свободное время.
Работа планируется в реальных условиях и на реальных абонентах.
Использовано python 3, django 1.11, bootstrap 3, и другое в файле requirements.txt

P.S. Возможно понадобится **Python 3.5** и выше из-за указания статических типов. [typing — Support for type hints](https://docs.python.org/3/library/typing.html).
Вы можете использовать билиотеку [mypy](http://www.mypy-lang.org/) для старших версий python.

## Содержание
* [Установка](./docs/install.md)
* [Сервисы и API](./docs/services.md)
* [Разработка расширений](./docs/dev.md)
* [Сбор информации трафика по netflow](./docs/netflow.md)
* [Работа с представлениями](./docs/views.md)
* [Карта](./docs/map.md)
