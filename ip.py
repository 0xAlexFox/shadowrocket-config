#!/usr/bin/env python3
from pathlib import Path
import ipaddress

# 👉 Укажи тут папки внутри репозитория, где лежат .lst с IP/подсетями
TARGET_DIRS = [
    "domains/ip",
    # "Subnets/IPv6",
    # "Another/Dir",
]

MAKE_BACKUP = True  # создать file.bak перед перезаписью


def normalize_ip_or_cidr(line: str) -> str | None:
    """
    Превращает строку с IP/подсетью в каноничный вид для IP-CIDR.
    - bare IPv4  -> x.x.x.x/32
    - bare IPv6  -> xxxx::/128
    - IPv4/IPv6 CIDR остаётся как есть (нормализуется ipaddress-ом)
    Возвращает строку 'IP-CIDR,<cidr>,no-resolve' или None, если строка невалидная.
    """
    s = line.strip()

    # уже в формате IP-CIDR, нормализуем/добавляем no-resolve
    if s.upper().startswith("IP-CIDR,"):
        body = s.split(",", 1)[1].strip()  # всё после первой запятой
        # может быть "1.2.3.0/24" или "1.2.3.4,no-resolve" — выделим cidr часть
        parts = [p.strip() for p in body.split(",")]
        cidr_raw = parts[0] if parts else ""
        try:
            # если это сеть — нормализуем; если это IP без маски — добавим /32 или /128
            if "/" in cidr_raw:
                net = ipaddress.ip_network(cidr_raw, strict=False)
                cidr = str(net)
            else:
                ip = ipaddress.ip_address(cidr_raw)
                cidr = f"{ip}/32" if isinstance(ip, ipaddress.IPv4Address) else f"{ip}/128"
            return f"IP-CIDR,{cidr},no-resolve"
        except ValueError:
            return None

    # комментарии/пустые — игнор
    if not s or s.startswith("#"):
        return s  # вернём как есть (сохранится в файле)

    # попробуем как подсеть
    try:
        if "/" in s:
            net = ipaddress.ip_network(s, strict=False)
            return f"IP-CIDR,{net},no-resolve"
    except ValueError:
        pass

    # попробуем как голый IP
    try:
        ip = ipaddress.ip_address(s)
        cidr = f"{ip}/32" if isinstance(ip, ipaddress.IPv4Address) else f"{ip}/128"
        return f"IP-CIDR,{cidr},no-resolve"
    except ValueError:
        # невалидная строка — вернём None, чтобы пропустить
        return None


def process_lst_file(path: Path) -> tuple[int, int]:
    """
    Обрабатывает .lst: возвращает (изменённых_строк, всего_строк_оставлено).
    """
    src_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    out_lines: list[str] = []
    changed = 0
    kept = 0

    for raw in src_lines:
        res = normalize_ip_or_cidr(raw)
        if res is None:
            # пропускаем совсем невалидные строки (ни IP, ни CIDR, ни комментарии)
            continue
        if res == raw:
            out_lines.append(raw)
            kept += 1
        else:
            out_lines.append(res)
            changed += 1

    if MAKE_BACKUP:
        path.with_suffix(path.suffix + ".bak").write_text("\n".join(src_lines), encoding="utf-8")

    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return changed, kept


def main():
    total_files = 0
    total_changed = 0
    total_kept = 0

    for d in TARGET_DIRS:
        base = Path(d)
        if not base.is_dir():
            print(f"⚠️ Папка не найдена: {d}")
            continue
        for file in base.rglob("*.lst"):
            changed, kept = process_lst_file(file)
            print(f"✅ {file} — нормализовано: {changed}, оставлено без изменений: {kept}")
            total_files += 1
            total_changed += changed
            total_kept += kept

    print(f"\nГотово. Обработано файлов: {total_files}, нормализовано строк: {total_changed}, оставлено: {total_kept}")


if __name__ == "__main__":
    main()
