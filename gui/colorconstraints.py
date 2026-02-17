# --- DESIGN SYSTEM CONSTANTS (DREXEL UNIVERSITY) ---
COLOR_PRIMARY = "#07294D"   # Drexel Blue
COLOR_ACCENT  = "#FFC600"   # Drexel Gold
COLOR_BG_LIGHT= "#F5F5F5"   # Light Gray
COLOR_BG_WHITE= "#FFFFFF"   # Pure White
COLOR_TEXT    = "#333333"   # Dark Gray / Black
COLOR_RECORD  = "#D9534F"   # Red for recording state
COLOR_EDA     = "#07294D"   # Primary Blue for EDA/Phasic
COLOR_HR      = "#D9534F"   # Red for Heart Rate
COLOR_TONIC   = "#FFC600"   # Gold for Tonic

FONT_UI       = "Segoe UI"
FONT_MONO     = "Consolas"

class ResearchStyleSheet:
    @staticmethod
    def get_stylesheet():
        return f"""
        QMainWindow {{ background-color: {COLOR_BG_LIGHT}; }}
        QWidget {{ font-family: "{FONT_UI}"; font-size: 10pt; color: {COLOR_TEXT}; }}
        
        /* HEADER & MENU */
        QMenuBar {{ 
            background-color: {COLOR_PRIMARY}; 
            color: white; 
            border-bottom: 2px solid {COLOR_ACCENT}; 
        }}
        QMenuBar::item {{ background: transparent; color: white; padding: 8px 15px; }}
        QMenuBar::item:selected {{ background: #0A3D70; }}
        
        QMenu {{
            background-color: {COLOR_BG_WHITE};
            color: {COLOR_TEXT};
            border: 1px solid #CCCCCC;
        }}
        QMenu::item {{
            padding: 6px 20px;
        }}
        QMenu::item:selected {{
            background-color: {COLOR_PRIMARY};
            color: white;
        }}
        
        /* RIBBON */
        QTabWidget::pane {{ border: 1px solid #DDDDDD; background: {COLOR_BG_WHITE}; border-radius: 8px; }}
        QTabBar::tab {{
            background: {COLOR_BG_LIGHT};
            border: 1px solid #DDDDDD;
            padding: 8px 20px;
            margin-right: 4px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }}
        QTabBar::tab:selected {{
            background: {COLOR_BG_WHITE};
            border-bottom-color: {COLOR_BG_WHITE};
            font-weight: bold;
            color: {COLOR_PRIMARY};
            border-top: 3px solid {COLOR_ACCENT};
        }}
        
        /* BUTTONS */
        QPushButton {{ 
            background-color: {COLOR_PRIMARY}; 
            color: white; 
            border-radius: 8px; 
            padding: 8px; 
            border: none;
            font-weight: bold;
        }}
        QPushButton:disabled {{ background-color: #CCCCCC; color: #888888; }}
        QPushButton:hover {{ background-color: #0A3D70; }}
        
        /* Secondary Button Style */
        QPushButton#secondary {{ 
            background-color: #E0E0E0; 
            color: {COLOR_TEXT}; 
            border: 1px solid #CCC; 
        }}
        QPushButton#secondary:hover {{ background-color: #D0D0D0; }}

        /* Accent Button (Insert Event) */
        QPushButton#accent {{ 
            background-color: {COLOR_PRIMARY}; 
            color: {COLOR_ACCENT}; 
            border: 1px solid #E5B000;
        }}
        QPushButton#accent:hover {{ background-color: #FFD700; }}
        
        /* INPUTS */
        QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit {{ 
            border: 1px solid #CCC; 
            border-radius: 8px; 
            padding: 5px; 
            background-color: {COLOR_BG_WHITE}; 
            color: {COLOR_TEXT};
        }}

        QComboBox QAbstractItemView {{
            background-color: {COLOR_BG_WHITE};
            color: {COLOR_TEXT};
            selection-background-color: {COLOR_PRIMARY};
            selection-color: white;
            border: 1px solid #CCC;
        }}

        QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
            border: 2px solid {COLOR_ACCENT};
        }}
        
        /* GROUP BOXES */
        QGroupBox {{ 
            font-weight: bold; 
            border: 1px solid #CCC; 
            margin-top: 25px; 
            background: {COLOR_BG_WHITE}; 
            border-radius: 8px; 
        }}
        QGroupBox::title {{ 
            subcontrol-origin: margin; 
            subcontrol-position: top left; 
            padding: 0 5px; 
            color: {COLOR_PRIMARY}; 
        }}
        
        /* LISTS */
        QListWidget {{ 
            border: 1px solid #CCC; 
            background: {COLOR_BG_WHITE}; 
            border-radius: 8px; 
            outline: none;
        }}
        QListWidget::item:selected {{
            background: {COLOR_PRIMARY};
            color: white;
            border-radius: 4px;
        }}
        
        /* MODALS (Strict Light Mode) */
        QDialog {{ background-color: {COLOR_BG_WHITE}; }}
        QLabel#h1 {{ color: {COLOR_PRIMARY}; font-size: 14pt; font-weight: bold; }}
        
        QFrame#event_bar {{
            background: {COLOR_BG_LIGHT};
            border: 1px solid #CCC;
            border-radius: 8px;
        }}
        """