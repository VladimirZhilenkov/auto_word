# Сборка для Windows

## Вариант 1: На компьютере с Windows

1. **Скопируйте проект** на компьютер с Windows

2. **Установите Python 3.10+** с https://python.org
   - При установке отметьте "Add Python to PATH"

3. **Запустите сборку:**
   ```
   build_windows.bat
   ```

4. **Готовый файл:** `dist\DocumentGenerator.exe`

---

## Вариант 2: Через GitHub Actions (автоматически)

1. Загрузите проект на GitHub

2. Создайте файл `.github/workflows/build.yml`:
```yaml
name: Build Windows
on: [push]
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pyinstaller build_windows.spec
      - uses: actions/upload-artifact@v4
        with:
          name: DocumentGenerator
          path: dist/DocumentGenerator.exe
```

3. После push в репозиторий, exe файл будет в артефактах сборки

---

## Вариант 3: Через Docker (кросс-компиляция)

```bash
# На macOS с Docker
docker run -v $(pwd):/src cdrx/pyinstaller-windows:python3 \
  "pip install -r requirements.txt && pyinstaller build_windows.spec"
```

---

## После сборки

Для работы программы нужны папки рядом с exe:
- `templates/` — папка с шаблонами Word
- `output/` — создастся автоматически

Структура:
```
DocumentGenerator/
├── DocumentGenerator.exe
├── templates/
│   └── ваши_шаблоны.docx
└── output/
```
