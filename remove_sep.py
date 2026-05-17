import re
from pathlib import Path

f = Path("VKR_complete.md")
text = f.read_text(encoding="utf-8")

# Убираем строки вида |---|---| — разделители заголовка таблицы
# Строка состоит только из |, -, : и пробелов
cleaned = re.sub(r"^\|[\s|:\-]+\|\s*$\n?", "", text, flags=re.MULTILINE)

f.write_text(cleaned, encoding="utf-8")
removed = text.count("\n") - cleaned.count("\n")
print(f"Готово. Удалено строк-разделителей: {removed}")
