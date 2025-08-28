#!/usr/bin/env python3
from pathlib import Path
import ipaddress

# === НАСТРОЙКИ ===============================================================

# Папки с доменными списками (.lst), для которых нужно проставить "DOMAIN-SUFFIX,"
DOMAIN_DIRS = [
    "domains/services",
    # "domains/categories",
]

# Папки со списками IP/подсетей (.lst), которые нужно привести к "IP-CIDR,<cidr>,no-resolve"
IP_DIRS = [
    "domains/ip",
    # "Subnets/IPv4",
    # "Subnets/IPv6",
]

MAKE_BACKUP = True  # создавать *.bak перед перезаписью

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def process_domain_lst_file(path: Path) -> int:
    """
    Обрабатывает доменные .lst:
      - пропускает пустые строки и комментарии
      - не дублирует префикс, если уже есть
      - добавляет "DOMAIN-SUFFIX," к остальным строкам
    Возвращает количество строк, к которым был добавлен префикс.
    """
    src_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    out_lines = []
    changed = 0

    for raw in src_lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            out_lines.append(raw)
            continue
        if line.startswith("DOMAIN-SUFFIX,"):
            # нормализуем пробелы: пишем как есть из line (без хвостовых пробелов)
            out_lines.append(line)
            continue
        out_lines.append(f"DOMAIN-SUFFIX,{line}")
        changed += 1

    if MAKE_BACKUP:
        path.with_suffix(path.suffix + ".bak").write_text("\n".join(src_lines), encoding="utf-8")
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return changed


def normalize_ip_or_cidr(line: str):
    """
    Превращает строку с IP/подсетью в канон для IP-CIDR:
      - bare IPv4  -> x.x.x.x/32
      - bare IPv6  -> xxxx::/128
      - IPv4/IPv6 с маской — нормализует через ipaddress
      - уже в формате 'IP-CIDR,...' — гарантирует ',no-resolve'
    Возвращает:
      - готовую строку "IP-CIDR,<cidr>,no-resolve"
      - исходную строку (если это пустая/комментарий) — чтобы сохранить её
      - None (если строка невалидна и её нужно отбросить)
    """
    s = line.strip()

    # уже IP-CIDR
    if s.upper().startswith("IP-CIDR,"):
        body = s.split(",", 1)[1].strip()  # всё после "IP-CIDR,"
        parts = [p.strip() for p in body.split(",")]
        cidr_raw = parts[0] if parts else ""
        try:
            if "/" in cidr_raw:
                net = ipaddress.ip_network(cidr_raw, strict=False)
                cidr = str(net)
            else:
                ip = ipaddress.ip_address(cidr_raw)
                cidr = f"{ip}/32" if isinstance(ip, ipaddress.IPv4Address) else f"{ip}/128"
            return f"IP-CIDR,{cidr},no-resolve"
        except ValueError:
            return None

    # пустые/комменты — вернуть как есть
    if not s or s.startswith("#"):
        return line

    # подсеть CIDR?
    try:
        if "/" in s:
            net = ipaddress.ip_network(s, strict=False)
            return f"IP-CIDR,{net},no-resolve"
    except ValueError:
        pass

    # голый IP?
    try:
        ip = ipaddress.ip_address(s)
        cidr = f"{ip}/32" if isinstance(ip, ipaddress.IPv4Address) else f"{ip}/128"
        return f"IP-CIDR,{cidr},no-resolve"
    except ValueError:
        return None


def process_ip_lst_file(path: Path) -> tuple[int, int]:
    """
    Обрабатывает IP .lst:
      - нормализует строки к 'IP-CIDR,<cidr>,no-resolve'
      - сохраняет пустые и комментарии
      - отбрасывает невалидные строки
    Возвращает (нормализовано, оставлено_без_изменений).
    """
    src_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    out_lines = []
    changed = 0
    kept = 0

    for raw in src_lines:
        res = normalize_ip_or_cidr(raw)
        if res is None:
            # отброс невалидных
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


# ============================================================================
# ОСНОВНОЙ ЗАПУСК
# ============================================================================

def main():
    total_dom_files = total_dom_changed = 0
    for d in DOMAIN_DIRS:
        base = Path(d)
        if not base.is_dir():
            print(f"⚠️ Папка с доменами не найдена: {d}")
            continue
        for file in base.rglob("*.lst"):
            changed = process_domain_lst_file(file)
            print(f"🌐 {file} — добавлено префиксов: {changed}")
            total_dom_files += 1
            total_dom_changed += changed

    total_ip_files = total_ip_changed = total_ip_kept = 0
    for d in IP_DIRS:
        base = Path(d)
        if not base.is_dir():
            print(f"⚠️ Папка с IP не найдена: {d}")
            continue
        for file in base.rglob("*.lst"):
            changed, kept = process_ip_lst_file(file)
            print(f"🧩 {file} — нормализовано: {changed}, оставлено: {kept}")
            total_ip_files += 1
            total_ip_changed += changed
            total_ip_kept += kept

    print("\n=== ИТОГО ===")
    print(f"Доменные файлы: {total_dom_files}, добавлено префиксов: {total_dom_changed}")
    print(f"IP-файлы: {total_ip_files}, нормализовано строк: {total_ip_changed}, оставлено без изменений: {total_ip_kept}")

if __name__ == "__main__":
    main()
