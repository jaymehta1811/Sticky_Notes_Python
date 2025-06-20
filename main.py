import os
import json
import uuid
from PySide6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QPushButton,
                               QVBoxLayout, QWidget, QListWidget, QHBoxLayout,
                               QLineEdit, QFileDialog, QMessageBox, QLabel)
from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QAction

# --- Setup & Planning ---
# Define base directory and subdirectories
BASE_DIR = "StickyNotesApp"
NOTES_DIR = os.path.join(BASE_DIR, "notes")
THEMES_DIR = os.path.join(BASE_DIR, "themes")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# Ensure directories exist
os.makedirs(NOTES_DIR, exist_ok=True)
os.makedirs(THEMES_DIR, exist_ok=True)

# Define theme file paths
DARK_THEME_PATH = os.path.join(THEMES_DIR, "dark.qss")
LIGHT_THEME_PATH = os.path.join(THEMES_DIR, "light.qss")

# Create theme files only if they don't exist
if not os.path.exists(DARK_THEME_PATH):
    with open(DARK_THEME_PATH, "w") as f:
        f.write(dark_qss_content)
    print(f"Created {DARK_THEME_PATH}")

if not os.path.exists(LIGHT_THEME_PATH):
    with open(LIGHT_THEME_PATH, "w") as f:
        f.write(light_qss_content)
    print(f"Created {LIGHT_THEME_PATH}")

class StickyNotesApp(QMainWindow):
    # Modified __init__ to accept the QApplication instance
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance # Store the QApplication instance here
        self.setWindowTitle("Sticky Notes App")
        self.setGeometry(100, 100, 1000, 700) # Increased window size

        self.notes_data = {} # Stores {note_id: {"title": "...", "content": "..."}}
        self.current_note_id = None

        self.setup_ui()
        self.load_all_notes()
        self.load_theme_preference() # Now self.app will be available here

        # Auto-save timer
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.save_current_note_timed)

    def setup_ui(self):
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_h_layout = QHBoxLayout(central_widget)

        # --- Left Panel: Note List and Controls ---
        left_v_layout = QVBoxLayout()

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search notes...")
        self.search_input.textChanged.connect(self.filter_notes)
        left_v_layout.addWidget(self.search_input)

        # Note list
        self.note_list_widget = QListWidget()
        self.note_list_widget.setMinimumWidth(250) # Set a minimum width for the list
        self.note_list_widget.itemSelectionChanged.connect(self.display_selected_note)
        left_v_layout.addWidget(self.note_list_widget)

        # Buttons for left panel
        button_h_layout = QHBoxLayout()
        self.new_note_button = QPushButton("New Note")
        self.new_note_button.clicked.connect(self.create_new_note)
        button_h_layout.addWidget(self.new_note_button)

        self.delete_note_button = QPushButton("Delete Note")
        self.delete_note_button.clicked.connect(self.delete_selected_note)
        button_h_layout.addWidget(self.delete_note_button)

        self.rename_note_button = QPushButton("Rename Note")
        self.rename_note_button.clicked.connect(self.rename_selected_note)
        button_h_layout.addWidget(self.rename_note_button)

        left_v_layout.addLayout(button_h_layout)

        # Theme toggle
        self.theme_toggle_button = QPushButton("Toggle Theme")
        self.theme_toggle_button.clicked.connect(self.toggle_theme)
        left_v_layout.addWidget(self.theme_toggle_button)

        main_h_layout.addLayout(left_v_layout)

        # --- Right Panel: Note Content ---
        right_v_layout = QVBoxLayout()

        self.note_title_edit = QLineEdit()
        self.note_title_edit.setPlaceholderText("Note Title")
        self.note_title_edit.textChanged.connect(self.update_note_title)
        right_v_layout.addWidget(self.note_title_edit)

        self.note_content_edit = QTextEdit()
        self.note_content_edit.setPlaceholderText("Write your note here...")
        self.note_content_edit.textChanged.connect(self.start_auto_save_timer)
        right_v_layout.addWidget(self.note_content_edit)

        main_h_layout.addLayout(right_v_layout)

    def load_all_notes(self):
        self.notes_data = {}
        self.note_list_widget.clear()
        if not os.path.exists(NOTES_DIR):
            os.makedirs(NOTES_DIR)

        note_files = [f for f in os.listdir(NOTES_DIR) if f.endswith(".json")]
        note_files.sort(key=lambda f: os.path.getmtime(os.path.join(NOTES_DIR, f)), reverse=True) # Sort by modification time

        for filename in note_files:
            note_id = filename.split(".")[0]
            try:
                with open(os.path.join(NOTES_DIR, filename), "r") as f:
                    note = json.load(f)
                    self.notes_data[note_id] = note
                    self.note_list_widget.addItem(note.get("title", "Untitled Note"))
                    # Store note_id with the item for easy retrieval
                    item = self.note_list_widget.item(self.note_list_widget.count() - 1)
                    item.setData(Qt.UserRole, note_id)
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {filename}")
            except FileNotFoundError:
                print(f"File not found: {filename}")

        if self.note_list_widget.count() > 0:
            self.note_list_widget.setCurrentRow(0) # Select the first note

    def save_note_to_file(self, note_id, title, content):
        file_path = os.path.join(NOTES_DIR, f"{note_id}.json")
        try:
            with open(file_path, "w") as f:
                json.dump({"title": title, "content": content}, f, indent=4)
            print(f"Note '{title}' ({note_id}) saved.")
        except IOError as e:
            print(f"Error saving note '{title}': {e}")
            QMessageBox.critical(self, "Save Error", f"Could not save note: {e}")

    def create_new_note(self):
        if self.current_note_id: # Save current note before creating a new one
            self.save_current_note_timed()

        new_note_id = str(uuid.uuid4())
        new_note_title = "New Note"
        self.notes_data[new_note_id] = {"title": new_note_title, "content": ""}

        # Add to list widget and select it
        self.note_list_widget.insertItem(0, new_note_title) # Add to top
        new_item = self.note_list_widget.item(0)
        new_item.setData(Qt.UserRole, new_note_id)
        self.note_list_widget.setCurrentItem(new_item)

        self.current_note_id = new_note_id
        self.note_title_edit.setText(new_note_title)
        self.note_content_edit.clear()
        self.note_content_edit.setFocus()
        self.save_note_to_file(new_note_id, new_note_title, "") # Initial save

    def display_selected_note(self):
        selected_items = self.note_list_widget.selectedItems()
        if not selected_items:
            # Clear text fields if no note is selected
            self.note_title_edit.clear()
            self.note_content_edit.clear()
            self.current_note_id = None
            return

        # Save previous note before displaying new one
        if self.current_note_id:
            self.save_current_note_timed()

        selected_item = selected_items[0]
        note_id = selected_item.data(Qt.UserRole)
        self.current_note_id = note_id

        note = self.notes_data.get(note_id)
        if note:
            # Disconnect to prevent triggering auto-save when setting text
            self.note_title_edit.blockSignals(True)
            self.note_content_edit.blockSignals(True)

            self.note_title_edit.setText(note.get("title", "Untitled Note"))
            self.note_content_edit.setText(note.get("content", ""))

            # Reconnect signals
            self.note_title_edit.blockSignals(False)
            self.note_content_edit.blockSignals(False)
        else:
            print(f"Note with ID {note_id} not found in notes_data.")
            # Clear fields if note not found
            self.note_title_edit.clear()
            self.note_content_edit.clear()

    def update_note_title(self):
        if self.current_note_id:
            new_title = self.note_title_edit.text()
            self.notes_data[self.current_note_id]["title"] = new_title

            # Update the list widget item's text
            selected_items = self.note_list_widget.selectedItems()
            if selected_items:
                selected_item = selected_items[0]
                selected_item.setText(new_title)

            self.start_auto_save_timer() # Trigger auto-save for title change

    def start_auto_save_timer(self):
        # Restart the timer whenever text changes
        self.auto_save_timer.stop()
        self.auto_save_timer.start(1000) # 1-second delay

    def save_current_note_timed(self):
        if self.current_note_id and self.current_note_id in self.notes_data:
            title = self.note_title_edit.text()
            content = self.note_content_edit.toPlainText()
            self.save_note_to_file(self.current_note_id, title, content)
            # Update the in-memory data for consistency
            self.notes_data[self.current_note_id]["title"] = title
            self.notes_data[self.current_note_id]["content"] = content

    def delete_selected_note(self):
        selected_items = self.note_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Note Selected", "Please select a note to delete.")
            return

        reply = QMessageBox.question(self, "Confirm Delete",
                                     "Are you sure you want to delete this note?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            selected_item = selected_items[0]
            note_id_to_delete = selected_item.data(Qt.UserRole)

            # Remove from list widget
            row = self.note_list_widget.row(selected_item)
            self.note_list_widget.takeItem(row)

            # Remove from in-memory data
            if note_id_to_delete in self.notes_data:
                del self.notes_data[note_id_to_delete]

            # Delete the file
            file_path = os.path.join(NOTES_DIR, f"{note_id_to_delete}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Note file {file_path} deleted.")

            # Clear content if the deleted note was the current one
            if self.current_note_id == note_id_to_delete:
                self.note_title_edit.clear()
                self.note_content_edit.clear()
                self.current_note_id = None

            # Select the next available note or clear if none
            if self.note_list_widget.count() > 0:
                self.note_list_widget.setCurrentRow(0)
            else:
                self.note_title_edit.clear()
                self.note_content_edit.clear()
                self.current_note_id = None

    def rename_selected_note(self):
        selected_items = self.note_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Note Selected", "Please select a note to rename.")
            return

        selected_item = selected_items[0]
        note_id = selected_item.data(Qt.UserRole)
        current_title = selected_item.text()

        # Use QLineEdit for simple input dialog
        # Qt doesn't have a direct input dialog for QLineEdit in QMessageBox.
        # A custom dialog would be ideal, but for simplicity, we'll mimic behavior
        # by directly editing the title QLineEdit if it's the current note.
        if self.current_note_id == note_id:
            # Focus on the title edit for renaming
            self.note_title_edit.setFocus()
            self.note_title_edit.selectAll()
        else:
            QMessageBox.information(self, "Rename Note", "Please select the note in the list and edit its title directly in the title bar.")

    def filter_notes(self):
        search_text = self.search_input.text().lower()
        self.note_list_widget.clear()

        # Sort notes by most recent first for search results
        sorted_notes = sorted(self.notes_data.items(),
                              key=lambda item: os.path.getmtime(os.path.join(NOTES_DIR, f"{item[0]}.json")),
                              reverse=True)

        for note_id, note in sorted_notes:
            title = note.get("title", "Untitled Note").lower()
            content = note.get("content", "").lower()
            if search_text in title or search_text in content:
                item = self.note_list_widget.addItem(note.get("title", "Untitled Note"))
                item = self.note_list_widget.item(self.note_list_widget.count() - 1)
                item.setData(Qt.UserRole, note_id)
        if self.note_list_widget.count() > 0:
            self.note_list_widget.setCurrentRow(0) # Select the first result

    def toggle_theme(self):
        settings = QSettings("StickyNotesApp", "Preferences")
        current_theme = settings.value("theme", "light")
        new_theme = "dark" if current_theme == "light" else "light"
        self.apply_theme(new_theme)
        settings.setValue("theme", new_theme)

    def apply_theme(self, theme_name):
        qss_path = DARK_THEME_PATH if theme_name == "dark" else LIGHT_THEME_PATH
        try:
            with open(qss_path, "r") as f:
                self.app.setStyleSheet(f.read())
            print(f"Applied {theme_name} theme.")
        except FileNotFoundError:
            print(f"Theme file not found: {qss_path}")
        except Exception as e:
            print(f"Error applying theme: {e}")

    def load_theme_preference(self):
        settings = QSettings("StickyNotesApp", "Preferences")
        preferred_theme = settings.value("theme", "light") # Default to light
        self.apply_theme(preferred_theme)


if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("StickyNotesApp") # For QSettings
    window = StickyNotesApp(app) # Pass the app instance to the constructor
    window.show()
    app.exec()
