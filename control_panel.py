"""
Drone Tracking System - GUI Control Panel
Author: AI Drone Project
Description: Manuel kontrol paneli ve klavye kısayolları
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence


class ControlPanel(QWidget):
    """
    Drone kontrolü için widget paneli
    """

    # Signals (diğer modüllerle iletişim için)
    target_selected = pyqtSignal(int)  # Hedef ID
    lock_toggled = pyqtSignal(bool)  # Kilitleme durumu
    confidence_threshold_changed = pyqtSignal(float)  # Güvenilirlik eşiği
    emergency_stop_triggered = pyqtSignal()  # Acil durdurma
    depth_overlay_toggled = pyqtSignal(bool)  # Depth map gösterimi
    trajectory_toggled = pyqtSignal(bool)  # Trajectory gösterimi
    mode_changed = pyqtSignal(str)  # Manuel/Otonom mod
    tracking_reset = pyqtSignal()  # Tracking sıfırlama

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.init_shortcuts()

        # İç durum
        self.is_locked = False
        self.show_depth = False
        self.show_trajectory = True
        self.current_mode = "Autonomous"

    def init_ui(self):
        """GUI bileşenlerini oluştur"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 1. HEDEF SEÇİMİ
        layout.addWidget(QLabel("Target Selection:"))
        self.target_dropdown = QComboBox()
        self.target_dropdown.addItem("No Target")
        self.target_dropdown.currentIndexChanged.connect(self._on_target_selected)
        layout.addWidget(self.target_dropdown)

        # 2. KİLİTLEME BUTONU
        self.lock_button = QPushButton("🔓 Lock Target")
        self.lock_button.setCheckable(True)
        self.lock_button.clicked.connect(self._on_lock_toggle)
        self.lock_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #FFA500;
            }
        """)
        layout.addWidget(self.lock_button)

        # 3. GÜVENİLİRLİK EŞİĞİ
        layout.addWidget(QLabel("Confidence Threshold:"))

        threshold_layout = QHBoxLayout()
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setMinimum(30)  # 0.3
        self.confidence_slider.setMaximum(90)  # 0.9
        self.confidence_slider.setValue(50)    # 0.5 default
        self.confidence_slider.setTickPosition(QSlider.TicksBelow)
        self.confidence_slider.setTickInterval(10)
        self.confidence_slider.valueChanged.connect(self._on_confidence_changed)

        self.confidence_label = QLabel("0.50")
        self.confidence_label.setMinimumWidth(40)

        threshold_layout.addWidget(self.confidence_slider)
        threshold_layout.addWidget(self.confidence_label)
        layout.addLayout(threshold_layout)

        # 4. ACİL DURUM BUTONU
        self.emergency_button = QPushButton("⚠️ EMERGENCY STOP")
        self.emergency_button.clicked.connect(self._on_emergency_stop)
        self.emergency_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        layout.addWidget(self.emergency_button)

        # 5. GÖRÜNÜM AYARLARI
        layout.addWidget(QLabel("Display Options:"))

        self.depth_toggle = QCheckBox("Show Depth Map Overlay")
        self.depth_toggle.stateChanged.connect(self._on_depth_toggle)
        layout.addWidget(self.depth_toggle)

        self.trajectory_toggle = QCheckBox("Show Trajectory")
        self.trajectory_toggle.setChecked(True)
        self.trajectory_toggle.stateChanged.connect(self._on_trajectory_toggle)
        layout.addWidget(self.trajectory_toggle)

        # 6. MOD SEÇİMİ
        layout.addWidget(QLabel("Flight Mode:"))
        self.mode_checkbox = QCheckBox("Manual Mode")
        self.mode_checkbox.stateChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_checkbox)

        # 7. RESET BUTONU
        self.reset_button = QPushButton("🔄 Reset Tracking")
        self.reset_button.clicked.connect(self._on_reset_tracking)
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.reset_button)

        # 8. KLAVYE KISAYOL BİLGİSİ
        shortcuts_text = QLabel(
            "<b>Keyboard Shortcuts:</b><br>"
            "Space - Toggle Lock<br>"
            "Esc - Emergency Stop<br>"
            "D - Toggle Depth Map<br>"
            "T - Toggle Trajectory<br>"
            "R - Reset Tracking"
        )
        shortcuts_text.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(shortcuts_text)

        # Boş alan ekle
        layout.addStretch()

    def init_shortcuts(self):
        """Klavye kısayollarını ayarla"""
        from PyQt5.QtWidgets import QShortcut

        # Space: Toggle lock
        self.shortcut_lock = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.shortcut_lock.activated.connect(self._on_lock_toggle)

        # Esc: Emergency stop
        self.shortcut_emergency = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_emergency.activated.connect(self._on_emergency_stop)

        # D: Toggle depth overlay
        self.shortcut_depth = QShortcut(QKeySequence(Qt.Key_D), self)
        self.shortcut_depth.activated.connect(lambda: self.depth_toggle.setChecked(not self.depth_toggle.isChecked()))

        # T: Toggle trajectory
        self.shortcut_trajectory = QShortcut(QKeySequence(Qt.Key_T), self)
        self.shortcut_trajectory.activated.connect(lambda: self.trajectory_toggle.setChecked(not self.trajectory_toggle.isChecked()))

        # R: Reset tracking
        self.shortcut_reset = QShortcut(QKeySequence(Qt.Key_R), self)
        self.shortcut_reset.activated.connect(self._on_reset_tracking)

    # --- SLOT FUNCTIONS ---

    def _on_target_selected(self, index):
        """Hedef seçildiğinde"""
        if index > 0:  # 0 = "No Target"
            target_id = int(self.target_dropdown.currentText().split('#')[1])
            self.target_selected.emit(target_id)

    def _on_lock_toggle(self):
        """Kilitleme toggle"""
        self.is_locked = not self.is_locked

        if self.is_locked:
            self.lock_button.setText("🔒 Unlock Target")
        else:
            self.lock_button.setText("🔓 Lock Target")

        self.lock_button.setChecked(self.is_locked)
        self.lock_toggled.emit(self.is_locked)

    def _on_confidence_changed(self, value):
        """Güvenilirlik eşiği değiştiğinde"""
        threshold = value / 100.0
        self.confidence_label.setText(f"{threshold:.2f}")
        self.confidence_threshold_changed.emit(threshold)

    def _on_emergency_stop(self):
        """Acil durum butonu"""
        self.emergency_stop_triggered.emit()
        print("⚠️ EMERGENCY STOP TRIGGERED!")

    def _on_depth_toggle(self, state):
        """Depth map gösterimi"""
        self.show_depth = (state == Qt.Checked)
        self.depth_overlay_toggled.emit(self.show_depth)

    def _on_trajectory_toggle(self, state):
        """Trajectory gösterimi"""
        self.show_trajectory = (state == Qt.Checked)
        self.trajectory_toggled.emit(self.show_trajectory)

    def _on_mode_changed(self, state):
        """Manuel/Otonom mod değişimi"""
        if state == Qt.Checked:
            self.current_mode = "Manual"
        else:
            self.current_mode = "Autonomous"

        self.mode_changed.emit(self.current_mode)

    def _on_reset_tracking(self):
        """Tracking sıfırlama"""
        self.tracking_reset.emit()
        print("🔄 Tracking reset!")

    # --- PUBLIC METHODS ---

    def update_targets(self, target_ids):
        """
        Hedef listesini güncelle

        Args:
            target_ids (list): Aktif hedef ID'leri [12, 45, 67]
        """
        current_selection = self.target_dropdown.currentText()

        self.target_dropdown.clear()
        self.target_dropdown.addItem("No Target")

        for tid in target_ids:
            self.target_dropdown.addItem(f"Target #{tid}")

        # Önceki seçimi koru
        index = self.target_dropdown.findText(current_selection)
        if index >= 0:
            self.target_dropdown.setCurrentIndex(index)

    def set_lock_state(self, locked):
        """Kilitleme durumunu dışarıdan ayarla"""
        self.is_locked = locked
        self.lock_button.setChecked(locked)
        if locked:
            self.lock_button.setText("🔒 Unlock Target")
        else:
            self.lock_button.setText("🔓 Lock Target")

    def get_confidence_threshold(self):
        """Mevcut güvenilirlik eşiğini al"""
        return self.confidence_slider.value() / 100.0


# --- TEST KODU ---
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)

    # Test penceresi
    window = QMainWindow()
    window.setWindowTitle("Control Panel Test")

    # Control panel ekle
    panel = ControlPanel()
    window.setCentralWidget(panel)

    # Signal bağlantıları (test amaçlı)
    panel.target_selected.connect(lambda tid: print(f"Target selected: {tid}"))
    panel.lock_toggled.connect(lambda locked: print(f"Lock toggled: {locked}"))
    panel.confidence_threshold_changed.connect(lambda val: print(f"Confidence threshold: {val}"))
    panel.emergency_stop_triggered.connect(lambda: print("EMERGENCY STOP!"))
    panel.depth_overlay_toggled.connect(lambda show: print(f"Depth overlay: {show}"))
    panel.trajectory_toggled.connect(lambda show: print(f"Trajectory: {show}"))
    panel.mode_changed.connect(lambda mode: print(f"Mode changed: {mode}"))
    panel.tracking_reset.connect(lambda: print("Tracking reset!"))

    # Test hedefler ekle
    panel.update_targets([12, 34, 56, 78])

    window.show()
    sys.exit(app.exec_())
