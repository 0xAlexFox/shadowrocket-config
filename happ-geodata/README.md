# Happ Geodata

Этот каталог предназначен для компактного профиля Happ.

- `geosite.dat` и `geoip.dat` собираются из текущих правил репозитория.
- `sources/` содержит человекочитаемые исходники тегов, которые попадают в `.dat`.
- `metadata.json` фиксирует источник внешнего списка и количество правил по тегам.

Теги, которые использует компактный профиль:

- `geosite:shadowrocket-direct`
- `geoip:shadowrocket-direct`
- `geosite:shadowrocket-proxy`
- `geoip:shadowrocket-proxy`

Сборка:

```bash
python3 scripts/build_happ_geodata.py
```

После коммита и публикации в GitHub файл [happ-routing-compact.conf](/Users/alex/all_dev/devWeb/shadowrocket-config/happ-routing-compact.conf) сможет подтягивать эти `.dat` по `raw.githubusercontent.com`.
