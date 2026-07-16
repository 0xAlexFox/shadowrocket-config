# Incy routing profile

Статический профиль маршрутизации Incy, собранный из правил этого репозитория.

## Файлы

- `routing.json` — профиль Incy.
- `geosite.dat` — компактные доменные правила.
- `geoip.dat` — компактные IP-правила.
- `*.sha256` — контрольные суммы, позволяющие Incy не загружать неизменившиеся geodata-файлы повторно.

Используемые теги:

- `geosite:shadowrocket-direct`
- `geoip:shadowrocket-direct`
- `geosite:shadowrocket-proxy`
- `geoip:shadowrocket-proxy`

## Импорт

После публикации файлов в ветке `master` открыть на iPhone:

```text
incy://routing/onadd/https://raw.githubusercontent.com/0xAlexFox/shadowrocket-config/refs/heads/master/incy/routing.json
```

Схема `routing`, в отличие от `autorouting`, выполняет однократный импорт и не привязывает профиль к источнику автоматических обновлений.

## Ручное обновление

При изменении исходных правил:

1. Пересобрать geodata командой `python3 scripts/build_happ_geodata.py`.
2. Заменить `incy/geosite.dat` и `incy/geoip.dat` свежими файлами из `happ-geodata/`.
3. Обновить соответствующие файлы `.sha256`.
4. Установить в `routing.json` поле `LastUpdated` в текущее Unix-время. Новое значение должно быть больше предыдущего.
5. Опубликовать изменения на GitHub и снова открыть ссылку импорта выше.

Профиль имеет постоянное имя, поэтому при большем `LastUpdated` Incy обновит существующую запись вместо создания дубликата.
