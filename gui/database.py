import sqlite3
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QComboBox, QDoubleSpinBox, 
                               QTextEdit, QPushButton, QMessageBox, QListWidget, 
                               QListWidgetItem)
from PySide6.QtCore import Qt

# --- DATABASE MANAGER ---
class DatabaseManager:
    def __init__(self, db_name="subjects.db"):
        self.db_name = db_name
        self.create_table()

    def create_table(self):
        """Ensures the subjects table exists."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    sex TEXT NOT NULL,
                    height REAL NOT NULL,
                    notes TEXT NOT NULL
                )
            """)
            conn.commit()

    def insert_subject(self, name, sex, height, notes):
        """Inserts a new subject into the database."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO subjects (name, sex, height, notes)
                VALUES (?, ?, ?, ?)
            """, (name, sex, height, notes))
            conn.commit()

    def get_all_subjects(self):
        """Retrieves all subjects from the database."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, sex, height, notes FROM subjects")
            return cursor.fetchall()

    def delete_subject(self, subject_id):
        """Deletes a subject from the database."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
            conn.commit()

# --- UI DIALOG ---
class SubjectDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Subject Data Entry")
        self.setFixedSize(400, 450)
        self.db_manager = DatabaseManager()
        
        self.saved_data = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Enter Subject Metadata")
        header.setObjectName("h1")
        main_layout.addWidget(header)

        # Form Layout
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("e.g., John Doe")

        self.input_sex = QComboBox()
        self.input_sex.addItems(["Select...", "Male", "Female", "Other"])

        # Height input configured for Inches
        self.input_height = QLineEdit()
        self.input_height.setPlaceholderText("e.g. 180.5")

        self.input_notes = QTextEdit()
        self.input_notes.setPlaceholderText("Pre-existing conditions, resting heart rate baseline, etc.")
        self.input_notes.setMaximumHeight(100)

        form_layout.addRow("Name:", self.input_name)
        form_layout.addRow("Sex:", self.input_sex)
        form_layout.addRow("Height (cm):", self.input_height)
        form_layout.addRow("Notes:", self.input_notes)

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondary")
        btn_cancel.clicked.connect(self.reject)
        
        btn_load = QPushButton("Load Subject")
        btn_load.setObjectName("secondary")
        btn_load.clicked.connect(self.load_subject_from_db)
        
        btn_save = QPushButton("Save Subject")
        btn_save.clicked.connect(self.validate_and_save)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_load)
        btn_layout.addWidget(btn_save)
        
        main_layout.addLayout(btn_layout)

    def validate_and_save(self):
        name = self.input_name.text().strip()
        sex = self.input_sex.currentText()
        height_str = self.input_height.text().strip()
        notes = self.input_notes.toPlainText().strip()

        # Strict Validation
        if not name:
            QMessageBox.warning(self, "Validation Error", "Name cannot be empty.")
            return
        if sex == "Select...":
            QMessageBox.warning(self, "Validation Error", "Please select a valid Sex.")
            return
        
        try:
            height_in = float(height_str)
            if height_in <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Height must be a valid number greater than 0.")
            return
        if not notes:
            QMessageBox.warning(self, "Validation Error", "Notes cannot be empty.")
            return

        # Convert inches to cm for standardized medical storage
        # lol its actually just in cm
        height_cm = height_in

        # Database Insertion
        try:
            self.db_manager.insert_subject(name, sex, height_cm, notes)
            self.saved_data = (name, sex, height_cm, notes)
            print("Subject saved to database.")
            self.accept() # Closes dialog successfully
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save subject:\n{str(e)}")

    def load_subject_from_db(self):
        dlg = SubjectSelectionDialog(self)
        if dlg.exec():
            sub = dlg.selected_subject
            if sub:
                self.input_name.setText(sub[1])
                self.input_sex.setCurrentText(sub[2])
                self.input_height.setText(str(sub[3]))
                self.input_notes.setText(sub[4])
                
                self.saved_data = sub
                self.accept()

class SubjectSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Subject")
        self.setFixedSize(400, 400)
        self.db_manager = DatabaseManager()
        self.selected_subject = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        header = QLabel("Select Subject from Database")
        header.setObjectName("h1")
        layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.validate_and_select)
        self.populate_list()
        layout.addWidget(self.list_widget)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondary")
        btn_cancel.clicked.connect(self.reject)
        
        btn_delete = QPushButton("Delete")
        btn_delete.setObjectName("secondary")
        btn_delete.clicked.connect(self.delete_selection)

        btn_select = QPushButton("Import")
        btn_select.setDefault(True)
        btn_select.clicked.connect(self.validate_and_select)
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_delete)
        btn_box.addWidget(btn_select)
        layout.addLayout(btn_box)

    def populate_list(self):
        self.list_widget.clear()
        subjects = self.db_manager.get_all_subjects()
        for sub in subjects:
            # sub is tuple: (id, name, sex, height, notes)
            item = QListWidgetItem(f"{sub[1]} (ID: {sub[0]})")
            item.setData(Qt.UserRole, sub)
            self.list_widget.addItem(item)

    def validate_and_select(self):
        current = self.list_widget.currentItem()
        if current:
            self.selected_subject = current.data(Qt.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a subject to import.")

    def delete_selection(self):
        current = self.list_widget.currentItem()
        if current:
            sub = current.data(Qt.UserRole)
            reply = QMessageBox.question(self, "Confirm Delete", 
                                         f"Are you sure you want to delete {sub[1]}?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.db_manager.delete_subject(sub[0])
                self.populate_list()