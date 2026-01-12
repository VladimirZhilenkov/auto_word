"""
Database configuration dialog for setting up local or remote database connections.
"""

from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox,
    QCheckBox, QFileDialog, QMessageBox, QTabWidget, QWidget,
    QProgressDialog
)
from PyQt5.QtGui import QFont

from ...database.config import DatabaseConfig, DatabaseType, get_config_manager
from ...database.connection import switch_database, get_current_config


class DatabaseConfigDialog(QDialog):
    """
    Dialog for configuring database connection.
    Supports SQLite, PostgreSQL, and MySQL.
    """
    
    connection_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Настройки базы данных")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.config_manager = get_config_manager()
        self.current_config = self.config_manager.load_config()
        
        self._setup_ui()
        self._load_current_config()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Настройки подключения к базе данных")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Database type selection
        type_group = QGroupBox("Тип базы данных")
        type_layout = QHBoxLayout(type_group)
        
        self.combo_db_type = QComboBox()
        self.combo_db_type.addItem("SQLite (локальная)", DatabaseType.SQLITE.value)
        self.combo_db_type.addItem("PostgreSQL (удалённая)", DatabaseType.POSTGRESQL.value)
        self.combo_db_type.addItem("MySQL/MariaDB (удалённая)", DatabaseType.MYSQL.value)
        self.combo_db_type.currentIndexChanged.connect(self._on_type_changed)
        
        type_layout.addWidget(QLabel("Тип:"))
        type_layout.addWidget(self.combo_db_type)
        type_layout.addStretch()
        
        layout.addWidget(type_group)
        
        # Tab widget for different settings
        self.tab_widget = QTabWidget()
        
        # SQLite tab
        self.sqlite_tab = self._create_sqlite_tab()
        self.tab_widget.addTab(self.sqlite_tab, "SQLite")
        
        # Remote database tab
        self.remote_tab = self._create_remote_tab()
        self.tab_widget.addTab(self.remote_tab, "Удалённая БД")
        
        layout.addWidget(self.tab_widget)
        
        # Connection status
        status_group = QGroupBox("Статус подключения")
        status_layout = QVBoxLayout(status_group)
        
        self.lbl_status = QLabel("Не проверено")
        self.lbl_status.setStyleSheet("color: gray;")
        status_layout.addWidget(self.lbl_status)
        
        layout.addWidget(status_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        btn_test = QPushButton("Проверить подключение")
        btn_test.clicked.connect(self._test_connection)
        button_layout.addWidget(btn_test)
        
        button_layout.addStretch()
        
        btn_save = QPushButton("Сохранить и подключить")
        btn_save.clicked.connect(self._save_and_connect)
        button_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
        
        # Info label
        info_label = QLabel(
            "Примечание: Для PostgreSQL требуется psycopg2, для MySQL - pymysql.\n"
            "Установите: pip install psycopg2-binary pymysql"
        )
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)
    
    def _create_sqlite_tab(self) -> QWidget:
        """Create SQLite configuration tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Database file path
        path_layout = QHBoxLayout()
        self.edit_sqlite_path = QLineEdit()
        self.edit_sqlite_path.setPlaceholderText("Путь к файлу базы данных...")
        
        btn_browse = QPushButton("Обзор...")
        btn_browse.clicked.connect(self._browse_sqlite_file)
        
        path_layout.addWidget(self.edit_sqlite_path)
        path_layout.addWidget(btn_browse)
        
        layout.addRow("Файл БД:", path_layout)
        
        # Info
        info = QLabel("SQLite - локальная файловая база данных.\nРекомендуется для личного использования.")
        info.setStyleSheet("color: gray;")
        layout.addRow(info)
        
        return widget
    
    def _create_remote_tab(self) -> QWidget:
        """Create remote database configuration tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Host
        self.edit_host = QLineEdit()
        self.edit_host.setPlaceholderText("localhost или IP-адрес сервера")
        layout.addRow("Хост:", self.edit_host)
        
        # Port
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(5432)
        layout.addRow("Порт:", self.spin_port)
        
        # Database name
        self.edit_database = QLineEdit()
        self.edit_database.setPlaceholderText("Имя базы данных")
        layout.addRow("База данных:", self.edit_database)
        
        # Username
        self.edit_username = QLineEdit()
        self.edit_username.setPlaceholderText("Имя пользователя")
        layout.addRow("Пользователь:", self.edit_username)
        
        # Password
        self.edit_password = QLineEdit()
        self.edit_password.setEchoMode(QLineEdit.Password)
        self.edit_password.setPlaceholderText("Пароль")
        layout.addRow("Пароль:", self.edit_password)
        
        # SSL
        self.chk_ssl = QCheckBox("Использовать SSL")
        layout.addRow(self.chk_ssl)
        
        # SSL CA Certificate
        ssl_layout = QHBoxLayout()
        self.edit_ssl_cert = QLineEdit()
        self.edit_ssl_cert.setPlaceholderText("Путь к CA сертификату (опционально)")
        self.edit_ssl_cert.setEnabled(False)
        
        btn_ssl_browse = QPushButton("...")
        btn_ssl_browse.setMaximumWidth(30)
        btn_ssl_browse.clicked.connect(self._browse_ssl_cert)
        
        ssl_layout.addWidget(self.edit_ssl_cert)
        ssl_layout.addWidget(btn_ssl_browse)
        
        layout.addRow("SSL сертификат:", ssl_layout)
        
        # Connection timeout
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(5, 300)
        self.spin_timeout.setValue(30)
        self.spin_timeout.setSuffix(" сек")
        layout.addRow("Таймаут:", self.spin_timeout)
        
        # Pool size
        self.spin_pool = QSpinBox()
        self.spin_pool.setRange(1, 20)
        self.spin_pool.setValue(5)
        layout.addRow("Пул соединений:", self.spin_pool)
        
        # Connect SSL checkbox to cert field
        self.chk_ssl.toggled.connect(self.edit_ssl_cert.setEnabled)
        
        return widget
    
    def _on_type_changed(self, index: int):
        """Handle database type change."""
        db_type = self.combo_db_type.currentData()
        
        if db_type == DatabaseType.SQLITE.value:
            self.tab_widget.setCurrentIndex(0)
            self.tab_widget.setTabEnabled(1, False)
        else:
            self.tab_widget.setCurrentIndex(1)
            self.tab_widget.setTabEnabled(1, True)
            
            # Set default port based on type
            if db_type == DatabaseType.POSTGRESQL.value:
                self.spin_port.setValue(5432)
            elif db_type == DatabaseType.MYSQL.value:
                self.spin_port.setValue(3306)
        
        self.lbl_status.setText("Не проверено")
        self.lbl_status.setStyleSheet("color: gray;")
    
    def _browse_sqlite_file(self):
        """Browse for SQLite database file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Выберите файл базы данных",
            str(Path.home()),
            "SQLite Database (*.db *.sqlite);;All Files (*.*)"
        )
        
        if file_path:
            self.edit_sqlite_path.setText(file_path)
    
    def _browse_ssl_cert(self):
        """Browse for SSL certificate file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите SSL сертификат",
            "",
            "Certificate Files (*.pem *.crt *.cer);;All Files (*.*)"
        )
        
        if file_path:
            self.edit_ssl_cert.setText(file_path)
    
    def _load_current_config(self):
        """Load current configuration into UI."""
        config = self.current_config
        
        # Set database type
        index = self.combo_db_type.findData(config.db_type)
        if index >= 0:
            self.combo_db_type.setCurrentIndex(index)
        
        # SQLite settings
        self.edit_sqlite_path.setText(config.sqlite_path)
        
        # Remote settings
        self.edit_host.setText(config.host)
        self.spin_port.setValue(config.port)
        self.edit_database.setText(config.database)
        self.edit_username.setText(config.username)
        self.edit_password.setText(config.password)
        self.chk_ssl.setChecked(config.ssl_enabled)
        self.edit_ssl_cert.setText(config.ssl_ca_cert)
        self.spin_timeout.setValue(config.connection_timeout)
        self.spin_pool.setValue(config.pool_size)
        
        # Trigger type change to set up UI
        self._on_type_changed(self.combo_db_type.currentIndex())
    
    def _get_config_from_ui(self) -> DatabaseConfig:
        """Build configuration from UI values."""
        return DatabaseConfig(
            db_type=self.combo_db_type.currentData(),
            sqlite_path=self.edit_sqlite_path.text(),
            host=self.edit_host.text(),
            port=self.spin_port.value(),
            database=self.edit_database.text(),
            username=self.edit_username.text(),
            password=self.edit_password.text(),
            ssl_enabled=self.chk_ssl.isChecked(),
            ssl_ca_cert=self.edit_ssl_cert.text(),
            connection_timeout=self.spin_timeout.value(),
            pool_size=self.spin_pool.value()
        )
    
    def _test_connection(self):
        """Test database connection."""
        config = self._get_config_from_ui()
        
        # Show progress
        progress = QProgressDialog("Проверка подключения...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        try:
            success, message = self.config_manager.test_connection(config)
            
            if success:
                self.lbl_status.setText(f"✓ {message}")
                self.lbl_status.setStyleSheet("color: green;")
                QMessageBox.information(self, "Успех", message)
            else:
                self.lbl_status.setText(f"✗ {message}")
                self.lbl_status.setStyleSheet("color: red;")
                QMessageBox.warning(self, "Ошибка", message)
        
        finally:
            progress.close()
    
    def _save_and_connect(self):
        """Save configuration and connect to database."""
        config = self._get_config_from_ui()
        
        # Validate
        valid, error = config.validate()
        if not valid:
            QMessageBox.warning(self, "Ошибка валидации", error)
            return
        
        # Confirm if switching databases
        current = get_current_config()
        if current and (current.db_type != config.db_type or 
                       current.sqlite_path != config.sqlite_path or
                       current.host != config.host or
                       current.database != config.database):
            
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                "Вы уверены, что хотите переключиться на другую базу данных?\n"
                "Приложение будет перезагружено для применения изменений.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
        
        # Show progress
        progress = QProgressDialog("Подключение к базе данных...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        try:
            success, message = switch_database(config)
            
            if success:
                self.lbl_status.setText(f"✓ Подключено")
                self.lbl_status.setStyleSheet("color: green;")
                QMessageBox.information(
                    self, 
                    "Успех", 
                    "База данных успешно подключена.\n"
                    "Настройки сохранены."
                )
                self.connection_changed.emit()
                self.accept()
            else:
                self.lbl_status.setText(f"✗ {message}")
                self.lbl_status.setStyleSheet("color: red;")
                QMessageBox.critical(self, "Ошибка", message)
        
        finally:
            progress.close()
