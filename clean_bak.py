#!/usr/bin/env python3
from pathlib import Path

# те же директории, что и в normalize_lists.py
DOMAIN_DIRS = [
    "domains/services",
    # "domains/categories",
]

IP_DIRS = [
    "domains/ip",
    # "Subnets/IPv4",
    # "Subnets/IPv6",
]

def clean_backups(dirs):
    total_removed = 0
    for d in dirs:
        base = Path(d)
        if not base.is_dir():
            print(f"⚠️ Папка не найдена: {d}")
            continue
        for file in base.rglob("*.bak"):
            try:
                file.unlink()
                print(f"🗑 Удалено: {file}")
                total_removed += 1
            except Exception as e:
                print(f"❌ Ошибка при удалении {file}: {e}")
    return total_removed

def main():
    total = 0
    total += clean_backups(DOMAIN_DIRS)
    total += clean_backups(IP_DIRS)
    print(f"\n✅ Всего удалено резервных файлов: {total}")

if __name__ == "__main__":
    main()
