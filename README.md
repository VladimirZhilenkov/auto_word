# Document Generator

Десктопное приложение для автоматической генерации документов Word на основе шаблонов и базы данных слушателей.

## Возможности

- 📥 Импорт данных из Excel (слушатели и программы обучения)
- 👥 Управление базой данных слушателей
- 📚 Управление программами обучения
- 📄 Генерация документов Word по шаблонам
- 🔤 Автоматическое склонение ФИО по падежам (pymorphy2)
- 🔒 Работает полностью офлайн (для защиты персональных данных)

## Требования

- Python 3.9+
- PyQt5
- SQLAlchemy 2.0+
- pandas
- pymorphy2
- docxtpl

## Установка

1. Клонируйте репозиторий:
```bash
cd /path/to/project
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Запуск

```bash
python main.py
```

## Структура проекта

```
document-generator/
├── main.py                 # Точка входа
├── requirements.txt        # Зависимости
├── app/
│   ├── database/           # Модели и подключение к БД
│   ├── services/           # Бизнес-логика
│   ├── ui/                 # Интерфейс PyQt5
│   └── utils/              # Утилиты
├── data/
│   └── database.db         # SQLite база данных
├── docx_files/             # Шаблоны Word
└── output/                 # Сгенерированные документы
```

## Шаблоны Word

Поместите файлы `.docx` в папку `docx_files/`. Используйте синтаксис Jinja2 для переменных:

### Переменные слушателя

| Переменная | Описание |
|------------|----------|
| `{{ full_name }}` | Иванов Иван Иванович |
| `{{ full_name_genitive }}` | Иванова Ивана Ивановича |
| `{{ full_name_dative }}` | Иванову Ивану Ивановичу |
| `{{ full_name_accusative }}` | Иванова Ивана Ивановича |
| `{{ full_name_instrumental }}` | Ивановым Иваном Ивановичем |
| `{{ full_name_prepositional }}` | Иванове Иване Ивановиче |
| `{{ initials }}` | Иванов И.И. |
| `{{ initials_before }}` | И.И. Иванов |
| `{{ position }}` | Должность |
| `{{ workplace }}` | Место работы |
| `{{ region }}` | Субъект РФ |
| `{{ order_number }}` | № п/п |

### Переменные программы

| Переменная | Описание |
|------------|----------|
| `{{ program_name }}` | Наименование программы |
| `{{ program_short_name }}` | Краткое наименование |
| `{{ training_basis }}` | Основание для обучения |
| `{{ training_period }}` | Период обучения |
| `{{ program_volume }}` | Объем программы |
| `{{ education_form }}` | Форма обучения |
| `{{ education_format }}` | Формат обучения |
| `{{ listener_category }}` | Категория слушателей |
| `{{ expulsion_date }}` | Дата отчисления |

### Служебные переменные

| Переменная | Описание |
|------------|----------|
| `{{ current_date }}` | Текущая дата (02.01.2026) |
| `{{ current_year }}` | Текущий год (2026) |

## Импорт данных

Приложение поддерживает импорт из Excel-файла "Для программки.xlsx" с двумя листами:

### Лист 1: Программы обучения

| Столбец | Поле |
|---------|------|
| Наименование программы | program_name |
| Краткое наименование | program_short_name |
| Основание для обучения | training_basis |
| Период обучения | training_period |
| Объем программы | program_volume |
| Форма обучения | education_form |
| Формат обучения | education_format |
| Категория слушателей | listener_category |
| Дата отчисления | expulsion_date |

### Лист 2: Слушатели

| Столбец | Поле |
|---------|------|
| Фамилия Имя Отчество | full_name (разбивается на last_name, first_name, middle_name) |
| Должность | position |
| Наименование суда/место работы | workplace |
| Субъект РФ | region |

## Сборка .exe

Для создания исполняемого файла:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "DocumentGenerator" main.py
```

## Лицензия

MIT License
