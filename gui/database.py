import sqlite3
import datetime
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
                    subject_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    sex TEXT NOT NULL,
                    ethnicity TEXT NOT NULL,
                    handedness TEXT NOT NULL,
                    notes TEXT
                )
            """)
            conn.commit()

    def insert_subject(self, subject_id, name, age, sex, ethnicity, handedness, notes):
        """Inserts a new subject into the database."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO subjects (subject_id, name, age, sex, ethnicity, handedness, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (subject_id, name, age, sex, ethnicity, handedness, notes))
            conn.commit()
            return cursor.lastrowid

    def get_all_subjects(self):
        """Retrieves all subjects from the database."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, subject_id, name, age, sex, ethnicity, handedness, notes FROM subjects")
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

        self.input_age = QLineEdit()

        self.input_sex = QComboBox()
        self.input_sex.addItems(["Select...", "Male", "Female", "Intersex", "Prefer not to answer"])

        self.input_ethnicity = QComboBox()
        self.input_ethnicity.addItems([
            "Select...", "American Indian or Alaska Native", "Asian", 
            "Black or African American", "Hispanic or Latino", 
            "Native Hawaiian or Other Pacific Islander", "White", 
            "More than one race", "Unknown or Not Reported"
        ])

        self.input_handedness = QComboBox()
        self.input_handedness.addItems(["Select...", "Right-handed", "Left-handed", "Ambidextrous"])

        self.input_notes = QTextEdit()
        self.input_notes.setPlaceholderText("Clinical observations...")
        self.input_notes.setMaximumHeight(100)

        form_layout.addRow("Full Name:", self.input_name)
        form_layout.addRow("Age:", self.input_age)
        form_layout.addRow("Sex at Birth:", self.input_sex)
        form_layout.addRow("Race/Ethnicity:", self.input_ethnicity)
        form_layout.addRow("Handedness:", self.input_handedness)
        form_layout.addRow("Clinical Notes:", self.input_notes)

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
        age_text = self.input_age.text().strip()
        sex = self.input_sex.currentText()
        ethnicity = self.input_ethnicity.currentText()
        handedness = self.input_handedness.currentText()
        notes = self.input_notes.toPlainText().strip()

        # Strict Validation
        if not name:
            QMessageBox.warning(self, "Validation Error", "Name cannot be empty.")
            return
        
        try:
            age = int(age_text)
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Age must be a valid number.")
            return

        if age <= 0:
            QMessageBox.warning(self, "Validation Error", "Age must be greater than 0.")
            return
        if sex == "Select...":
            QMessageBox.warning(self, "Validation Error", "Please select a valid Sex.")
            return
        if ethnicity == "Select...":
            QMessageBox.warning(self, "Validation Error", "Please select a valid Ethnicity.")
            return
        if handedness == "Select...":
            QMessageBox.warning(self, "Validation Error", "Please select a valid Handedness.")
            return

        # Auto-generate Subject ID
        subject_id = f"SUB-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Database Insertion
        try:
            new_id = self.db_manager.insert_subject(subject_id, name, age, sex, ethnicity, handedness, notes)
            self.saved_data = (new_id, subject_id, name, age, sex, ethnicity, handedness, notes)
            print(f"Subject {subject_id} saved to database.")
            self.accept() # Closes dialog successfully
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save subject:\n{str(e)}")

    def load_subject_from_db(self):
        dlg = SubjectSelectionDialog(self)
        if dlg.exec():
            sub = dlg.selected_subject
            if sub:
                self.input_name.setText(sub[2])
                self.input_age.setText(str(sub[3]))
                self.input_sex.setCurrentText(sub[4])
                self.input_ethnicity.setCurrentText(sub[5])
                self.input_handedness.setCurrentText(sub[6])
                self.input_notes.setText(sub[7])
                
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
            # sub is tuple: (id, subject_id, name, age, sex, ethnicity, handedness, notes)
            item = QListWidgetItem(f"{sub[2]} (ID: {sub[1]})")
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