#!/usr/bin/env python3
from pathlib import Path

# 👉 Укажи тут папки внутри репозитория, где нужно обработать .lst
TARGET_DIRS = [
    "domains/services",
    # "Subnets/IPv6",
    # "Services",
    # "Categories",
]

MAKE_BACKUP = True  # создать file.bak перед перезаписью

def process_lst_file(path: Path) -> int:
    """Добавляет 'DOMAIN-SUFFIX, ' ко всем строкам в .lst (кроме пустых и комментариев).
       Не добавляет повторно, если префикс уже есть. Возвращает число обработанных строк."""
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        src_lines = f.read().splitlines()

    out_lines = []
    changed = 0
    for raw in src_lines:
        line = raw.strip()
        if not line:                # пустая строка
            out_lines.append(raw)
            continue
        if line.startswith("#"):    # комментарий
            out_lines.append(raw)
            continue
        if line.startswith("DOMAIN-SUFFIX,"):
            out_lines.append(line)  # уже обработано – оставляем как есть (без лишних пробелов)
            continue

        out_lines.append(f"DOMAIN-SUFFIX,{line}")
        changed += 1

    if MAKE_BACKUP:
        path.with_suffix(path.suffix + ".bak").write_text("\n".join(src_lines), encoding="utf-8")

    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return changed

def main():
    total_files = 0
    total_lines = 0
    for d in TARGET_DIRS:
        base = Path(d)
        if not base.is_dir():
            print(f"⚠️ Папка не найдена: {d}")
            continue
        for file in base.rglob("*.lst"):
            changed = process_lst_file(file)
            print(f"✅ {file} — добавлено префиксов: {changed}")
            total_files += 1
            total_lines += changed

    print(f"\nГотово. Обработано файлов: {total_files}, добавлено префиксов: {total_lines}")

if __name__ == "__main__":
    main()