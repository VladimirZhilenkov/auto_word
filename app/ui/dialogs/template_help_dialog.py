"""
Template Help Dialog - Instructions for creating Word templates.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTextBrowser, QPushButton, QLabel, QScrollArea, QFrame
)
from PyQt5.QtGui import QFont


class TemplateHelpDialog(QDialog):
    """Dialog with comprehensive template creation instructions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Инструкция по созданию шаблонов")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget for different sections
        tabs = QTabWidget()
        
        # Tab 1: Quick Start
        tabs.addTab(self._create_quickstart_tab(), "Быстрый старт")
        
        # Tab 2: Variables Reference
        tabs.addTab(self._create_variables_tab(), "Переменные")
        
        # Tab 3: Table Instructions
        tabs.addTab(self._create_table_tab(), "Таблицы")
        
        # Tab 4: Examples
        tabs.addTab(self._create_examples_tab(), "Примеры")
        
        layout.addWidget(tabs)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _create_quickstart_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml("""
        <style>
            body { font-family: -apple-system, sans-serif; font-size: 14px; line-height: 1.6; }
            h2 { color: #2196F3; border-bottom: 2px solid #2196F3; padding-bottom: 5px; }
            h3 { color: #1976D2; margin-top: 20px; }
            code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: Monaco, monospace; }
            .step { background: #E3F2FD; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #2196F3; }
            .warning { background: #FFF3E0; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #FF9800; }
            .success { background: #E8F5E9; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #4CAF50; }
        </style>
        
        <h2>📝 Быстрый старт: Создание шаблона</h2>
        
        <div class="step">
        <h3>Шаг 1: Создайте документ Word</h3>
        <p>Откройте Microsoft Word и создайте документ с нужным оформлением: шрифты, отступы, таблицы, колонтитулы.</p>
        </div>
        
        <div class="step">
        <h3>Шаг 2: Вставьте переменные</h3>
        <p>В местах, где должна быть <b>изменяющаяся информация</b>, напишите имя переменной в двойных фигурных скобках:</p>
        <p style="text-align: center; font-size: 16px;"><code>{{ имя_переменной }}</code></p>
        <p><b>Пример:</b> Вместо "Иванов Иван Иванович" напишите <code>{{ listener.full_name }}</code></p>
        </div>
        
        <div class="step">
        <h3>Шаг 3: Создайте таблицу слушателей</h3>
        <p>Создайте таблицу с заголовками. В <b>первой строке данных</b> (не в заголовке!) используйте переменные:</p>
        <table border="1" cellpadding="8" cellspacing="0" style="margin: 10px auto;">
            <tr style="background: #E3F2FD;">
                <td><b>№ п/п</b></td>
                <td><b>ФИО</b></td>
                <td><b>Должность</b></td>
                <td><b>Суд</b></td>
                <td><b>Регион</b></td>
            </tr>
            <tr>
                <td><code>{{ loop.index }}</code></td>
                <td><code>{{ listener.full_name }}</code></td>
                <td><code>{{ listener.position }}</code></td>
                <td><code>{{ listener.court_name }}</code></td>
                <td><code>{{ listener.region }}</code></td>
            </tr>
        </table>
        </div>
        
        <div class="step">
        <h3>Шаг 4: Сохраните в папку templates</h3>
        <p>Сохраните файл с расширением <code>.docx</code> в папку <b>templates</b> программы.</p>
        </div>
        
        <div class="step">
        <h3>Шаг 5: Активируйте цикл для таблицы</h3>
        <p>Напишите в чат: <i>"Добавь цикл в шаблон [имя_файла.docx]"</i></p>
        <p>Это необходимо, чтобы таблица автоматически расширялась на нужное количество строк.</p>
        </div>
        
        <div class="warning">
        <b>⚠️ Важно!</b> Печатайте переменную <b>сразу целиком</b>, не редактируя отдельные символы. 
        Word может разбить текст на части, и переменная не сработает.
        </div>
        
        <div class="success">
        <b>✅ Готово!</b> Теперь шаблон доступен в программе для генерации документов.
        </div>
        """)
        
        layout.addWidget(browser)
        return widget
    
    def _create_variables_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <style>
            body { font-family: -apple-system, sans-serif; font-size: 14px; }
            h2 { color: #2196F3; }
            h3 { color: #1976D2; margin-top: 25px; background: #E3F2FD; padding: 10px; border-radius: 5px; }
            table { border-collapse: collapse; width: 100%; margin: 10px 0; }
            th { background: #2196F3; color: white; padding: 10px; text-align: left; }
            td { padding: 8px; border-bottom: 1px solid #ddd; }
            tr:hover { background: #f5f5f5; }
            code { background: #ECEFF1; padding: 2px 6px; border-radius: 3px; font-family: Monaco, monospace; color: #D32F2F; }
        </style>
        
        <h2>📋 Справочник переменных</h2>
        
        <h3>📅 Данные приказа</h3>
        <table>
            <tr><th>Переменная</th><th>Описание</th><th>Пример</th></tr>
            <tr><td><code>{{ order_number }}</code></td><td>Номер приказа</td><td>111</td></tr>
            <tr><td><code>{{ order_day }}</code></td><td>День приказа</td><td>12</td></tr>
            <tr><td><code>{{ order_month }}</code></td><td>Месяц (текстом)</td><td>ноября</td></tr>
            <tr><td><code>{{ order_year }}</code></td><td>Год</td><td>2025</td></tr>
        </table>
        
        <h3>📜 Данные договора/контракта</h3>
        <table>
            <tr><th>Переменная</th><th>Описание</th><th>Пример</th></tr>
            <tr><td><code>{{ contract_type }}</code></td><td>Тип договора</td><td>государственным контрактом на оказание услуг по повышению квалификации</td></tr>
            <tr><td><code>{{ contract_number }}</code></td><td>Номер договора</td><td>б/н или № 123</td></tr>
            <tr><td><code>{{ contract_date }}</code></td><td>Дата договора</td><td>от 28 мая 2025 года</td></tr>
        </table>
        
        <h3>🎓 Данные программы обучения</h3>
        <table>
            <tr><th>Переменная</th><th>Описание</th><th>Пример</th></tr>
            <tr><td><code>{{ stream_name }}</code></td><td>Название потока</td><td>государственных гражданских служащих</td></tr>
            <tr><td><code>{{ program_name }}</code></td><td>Название программы</td><td>Организация работы администраторов районных судов</td></tr>
            <tr><td><code>{{ hours }}</code></td><td>Количество часов</td><td>16</td></tr>
            <tr><td><code>{{ education_form }}</code></td><td>Форма обучения</td><td>очной / заочной</td></tr>
            <tr><td><code>{{ education_format }}</code></td><td>Формат обучения</td><td>с применением электронного обучения, дистанционных образовательных технологий</td></tr>
            <tr><td><code>{{ start_date }}</code></td><td>Дата начала</td><td>20 января 2026 г.</td></tr>
            <tr><td><code>{{ end_date }}</code></td><td>Дата окончания</td><td>25 января 2026 г.</td></tr>
        </table>
        
        <h3>👥 Данные слушателя (в таблице со списком)</h3>
        <table>
            <tr><th>Переменная</th><th>Описание</th><th>Пример</th></tr>
            <tr><td><code>{{ loop.index }}</code></td><td>Порядковый номер</td><td>1, 2, 3...</td></tr>
            <tr><td><code>{{ listener.full_name }}</code></td><td>ФИО полностью</td><td>Иванов Иван Иванович</td></tr>
            <tr><td><code>{{ listener.position }}</code></td><td>Должность</td><td>Администратор суда</td></tr>
            <tr><td><code>{{ listener.court_name }}</code></td><td>Наименование суда</td><td>Ленинский районный суд г. Иркутска</td></tr>
            <tr><td><code>{{ listener.region }}</code></td><td>Субъект РФ</td><td>Иркутская область</td></tr>
        </table>
        
        <h3>👤 Данные слушателя (для индивидуальных документов)</h3>
        <table>
            <tr><th>Переменная</th><th>Описание</th><th>Пример</th></tr>
            <tr><td><code>{{ full_name }}</code></td><td>ФИО (именительный)</td><td>Иванов Иван Иванович</td></tr>
            <tr><td><code>{{ full_name_genitive }}</code></td><td>ФИО (родительный)</td><td>Иванова Ивана Ивановича</td></tr>
            <tr><td><code>{{ full_name_dative }}</code></td><td>ФИО (дательный)</td><td>Иванову Ивану Ивановичу</td></tr>
            <tr><td><code>{{ full_name_accusative }}</code></td><td>ФИО (винительный)</td><td>Иванова Ивана Ивановича</td></tr>
            <tr><td><code>{{ full_name_instrumental }}</code></td><td>ФИО (творительный)</td><td>Ивановым Иваном Ивановичем</td></tr>
            <tr><td><code>{{ initials }}</code></td><td>Инициалы после фамилии</td><td>Иванов И.И.</td></tr>
            <tr><td><code>{{ initials_before }}</code></td><td>Инициалы перед фамилией</td><td>И.И. Иванов</td></tr>
            <tr><td><code>{{ position }}</code></td><td>Должность</td><td>Администратор суда</td></tr>
            <tr><td><code>{{ workplace }}</code></td><td>Место работы</td><td>Ленинский районный суд</td></tr>
            <tr><td><code>{{ region }}</code></td><td>Регион</td><td>Иркутская область</td></tr>
        </table>
        
        <h3>📆 Служебные переменные</h3>
        <table>
            <tr><th>Переменная</th><th>Описание</th><th>Пример</th></tr>
            <tr><td><code>{{ current_date }}</code></td><td>Текущая дата</td><td>02.01.2026</td></tr>
            <tr><td><code>{{ current_year }}</code></td><td>Текущий год</td><td>2026</td></tr>
            <tr><td><code>{{ listeners_count }}</code></td><td>Количество слушателей</td><td>15</td></tr>
        </table>
        """)
        
        layout.addWidget(browser)
        return widget
    
    def _create_table_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <style>
            body { font-family: -apple-system, sans-serif; font-size: 14px; line-height: 1.6; }
            h2 { color: #2196F3; }
            h3 { color: #1976D2; margin-top: 20px; }
            code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: Monaco, monospace; }
            .box { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 8px; border: 1px solid #ddd; }
            .warning { background: #FFF3E0; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #FF9800; }
            .info { background: #E3F2FD; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #2196F3; }
            table { border-collapse: collapse; margin: 15px auto; }
            th, td { border: 1px solid #999; padding: 10px; }
            th { background: #E3F2FD; }
        </style>
        
        <h2>📊 Создание таблиц со списком слушателей</h2>
        
        <h3>Структура таблицы</h3>
        <p>Таблица должна состоять из:</p>
        <ol>
            <li><b>Строка заголовков</b> — обычный текст (№ п/п, ФИО, Должность и т.д.)</li>
            <li><b>Строка данных</b> — переменные в фигурных скобках</li>
        </ol>
        
        <table>
            <tr>
                <th>№ п/п</th>
                <th>Фамилия Имя Отчество</th>
                <th>Должность</th>
                <th>Наименование суда</th>
                <th>Субъект РФ</th>
            </tr>
            <tr>
                <td><code>{{ loop.index }}</code></td>
                <td><code>{{ listener.full_name }}</code></td>
                <td><code>{{ listener.position }}</code></td>
                <td><code>{{ listener.court_name }}</code></td>
                <td><code>{{ listener.region }}</code></td>
            </tr>
        </table>
        
        <div class="info">
        <b>ℹ️ Как это работает:</b><br>
        Программа автоматически дублирует строку с переменными для каждого слушателя.
        Если выбрано 10 слушателей — в таблице будет 10 строк.
        </div>
        
        <h3>Активация цикла</h3>
        <p>После создания шаблона необходимо <b>активировать цикл</b> для таблицы. 
        Это техническое действие, которое позволяет программе понять, какую строку нужно дублировать.</p>
        
        <div class="box">
        <b>Как активировать:</b><br>
        Напишите в чат: <i>"Добавь цикл в шаблон имя_файла.docx"</i>
        </div>
        
        <div class="warning">
        <b>⚠️ Внимание!</b><br>
        <ul>
            <li>Если вы редактируете шаблон в Word после активации цикла, цикл может удалиться</li>
            <li>В этом случае нужно снова попросить добавить цикл</li>
            <li>Ошибка <code>'loop' is undefined</code> означает, что цикл не активирован</li>
        </ul>
        </div>
        
        <h3>Несколько таблиц</h3>
        <p>Если в документе несколько таблиц со слушателями, цикл добавляется в первую найденную таблицу 
        с переменной <code>{{ loop.index }}</code>.</p>
        """)
        
        layout.addWidget(browser)
        return widget
    
    def _create_examples_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <style>
            body { font-family: -apple-system, sans-serif; font-size: 14px; line-height: 1.6; }
            h2 { color: #2196F3; }
            h3 { color: #1976D2; margin-top: 25px; }
            .example { background: #FAFAFA; padding: 15px; margin: 15px 0; border-radius: 8px; border: 1px solid #E0E0E0; }
            .example-title { font-weight: bold; color: #1976D2; margin-bottom: 10px; }
            code { background: #ECEFF1; padding: 2px 6px; border-radius: 3px; font-family: Monaco, monospace; }
            pre { background: #263238; color: #ECEFF1; padding: 15px; border-radius: 8px; overflow-x: auto; }
        </style>
        
        <h2>📄 Примеры шаблонов</h2>
        
        <h3>Пример 1: Приказ о зачислении</h3>
        <div class="example">
        <div class="example-title">Текст приказа:</div>
        <pre>
ПРИКАЗ

«{{ order_day }}» {{ order_month }} {{ order_year }} г.     № {{ order_number }}

О зачислении

В соответствии с {{ contract_type }} {{ contract_number }} {{ contract_date }} 
п р и к а з ы в а ю:

1. Зачислить в состав слушателей факультета повышения квалификации 
и переподготовки судей, государственных гражданских служащих судов 
и Судебного департамента (ФПК судей и госслужащих судов) потока 
{{ stream_name }} по дополнительной профессиональной программе: 
«{{ program_name }}» объемом {{ hours }} часов {{ education_form }} 
формы обучения {{ education_format }} согласно списку (приложение 1).

Первый заместитель директора                    Е.Ю. Рузавина
        </pre>
        </div>
        
        <h3>Пример 2: Приложение со списком</h3>
        <div class="example">
        <div class="example-title">Заголовок приложения:</div>
        <pre>
Приложение № 1
к приказу от {{ order_day }} {{ order_month }} {{ order_year }} г. № {{ order_number }}

Список слушателей факультета повышения квалификации и переподготовки 
судей, государственных гражданских служащих судов и Судебного 
департамента (ФПК судей и госслужащих судов), зачисленных на поток 
{{ stream_name }} по дополнительной профессиональной программе: 
«{{ program_name }}» ({{ hours }} часов) {{ education_form }} формы 
обучения {{ education_format }}
        </pre>
        </div>
        
        <h3>Пример 3: Индивидуальный документ</h3>
        <div class="example">
        <div class="example-title">Справка для одного слушателя:</div>
        <pre>
СПРАВКА

Дана {{ full_name_dative }} в том, что он(а) действительно 
проходил(а) обучение по дополнительной профессиональной программе 
«{{ program_name }}» в период с {{ start_date }} по {{ end_date }}.

Дата выдачи: {{ current_date }}
        </pre>
        </div>
        
        <h3>Типичные ошибки</h3>
        <div class="example" style="background: #FFEBEE; border-color: #FFCDD2;">
        <div class="example-title" style="color: #C62828;">❌ Неправильно:</div>
        <ul>
            <li><code>{{full_name}}</code> — нет пробелов внутри</li>
            <li><code>{ { full_name } }</code> — лишние пробелы</li>
            <li><code>{{ Full_Name }}</code> — неправильный регистр</li>
            <li><code>{{ listener.fullname }}</code> — нет подчёркивания</li>
        </ul>
        </div>
        
        <div class="example" style="background: #E8F5E9; border-color: #C8E6C9;">
        <div class="example-title" style="color: #2E7D32;">✅ Правильно:</div>
        <ul>
            <li><code>{{ full_name }}</code> — с пробелами внутри</li>
            <li><code>{{ listener.full_name }}</code> — для таблиц</li>
            <li><code>{{ loop.index }}</code> — для нумерации в таблице</li>
        </ul>
        </div>
        """)
        
        layout.addWidget(browser)
        return widget
