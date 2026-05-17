import re
t = open('VKR_complete.md', encoding='utf-8').read()
# убрать код-блоки
body = re.sub(r'```[\s\S]*?```', '', t)
for m in re.finditer(r'\*\*[^*]+\*\*', body):
    start = max(0, m.start()-60)
    print(repr(t[start:m.end()+40]))
