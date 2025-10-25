"""
Drone Tracking System - Ana GUI Örneği
Control Panel'in ana programa entegrasyonu
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import QTimer
from control_panel import ControlPanel


class DroneTrackingGUI(QMainWindow):
    """
    Ana GUI penceresi - Control Panel entegrasyonu örneği
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Drone Tracking System v1.0")
        self.setGeometry(100, 100, 1200, 800)

        # Ana widget ve layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Sol taraf: Video görüntüsü (placeholder)
        self.video_label = QLabel("Camera Feed\n(640x480)")
        self.video_label.setFixedSize(800, 600)
        self.video_label.setStyleSheet("background-color: black; color: white; font-size: 24px;")
        self.video_label.setAlignment(0x84)  # Center alignment
        main_layout.addWidget(self.video_label)

        # Sağ taraf: Control Panel
        self.control_panel = ControlPanel()
        main_layout.addWidget(self.control_panel)

        # Signal bağlantıları
        self.connect_signals()

        # Simüle edilmiş hedefler (test için)
        self.simulated_targets = [12, 34, 56]
        self.control_panel.update_targets(self.simulated_targets)

        # Timer ile hedef listesi güncelleme simülasyonu
        self.timer = QTimer()
        self.timer.timeout.connect(self.simulate_target_update)
        self.timer.start(5000)  # Her 5 saniyede bir

    def connect_signals(self):
        """Control panel signal'larını bağla"""

        self.control_panel.target_selected.connect(self.on_target_selected)
        self.control_panel.lock_toggled.connect(self.on_lock_toggled)
        self.control_panel.confidence_threshold_changed.connect(self.on_confidence_changed)
        self.control_panel.emergency_stop_triggered.connect(self.on_emergency_stop)
        self.control_panel.depth_overlay_toggled.connect(self.on_depth_toggle)
        self.control_panel.trajectory_toggled.connect(self.on_trajectory_toggle)
        self.control_panel.mode_changed.connect(self.on_mode_changed)
        self.control_panel.tracking_reset.connect(self.on_tracking_reset)

    # --- SIGNAL HANDLERS ---

    def on_target_selected(self, target_id):
        """Hedef seçildiğinde"""
        print(f"✓ Target #{target_id} selected")
        self.video_label.setText(f"Tracking Target #{target_id}")
        # Burada gerçek sistemde:
        # self.flight_controller.set_target(target_id)

    def on_lock_toggled(self, locked):
        """Kilitleme değiştiğinde"""
        status = "LOCKED" if locked else "UNLOCKED"
        print(f"🔒 Target {status}")
        # Burada gerçek sistemde:
        # self.flight_controller.set_lock(locked)

    def on_confidence_changed(self, threshold):
        """Güvenilirlik eşiği değiştiğinde"""
        print(f"📊 Confidence threshold set to: {threshold:.2f}")
        # Burada gerçek sistemde:
        # self.confidence_scorer.set_threshold(threshold)

    def on_emergency_stop(self):
        """Acil durum butonu basıldığında"""
        print("⚠️ EMERGENCY STOP - All systems halted!")
        self.video_label.setText("⚠️ EMERGENCY STOP")
        self.video_label.setStyleSheet("background-color: red; color: white; font-size: 36px;")
        # Burada gerçek sistemde:
        # self.flight_controller.emergency_stop()
        # self.drone.land_immediately()

    def on_depth_toggle(self, show_depth):
        """Depth map gösterimi değiştiğinde"""
        status = "ON" if show_depth else "OFF"
        print(f"🗺️ Depth map overlay: {status}")
        # Burada gerçek sistemde:
        # self.visualization.show_depth_overlay = show_depth

    def on_trajectory_toggle(self, show_trajectory):
        """Trajectory gösterimi değiştiğinde"""
        status = "ON" if show_trajectory else "OFF"
        print(f"📈 Trajectory display: {status}")
        # Burada gerçek sistemde:
        # self.visualization.show_trajectory = show_trajectory

    def on_mode_changed(self, mode):
        """Mod değiştiğinde"""
        print(f"🎮 Flight mode changed to: {mode}")
        # Burada gerçek sistemde:
        # if mode == "Manual":
        #     self.flight_controller.set_mode(FlightMode.MANUAL)
        # else:
        #     self.flight_controller.set_mode(FlightMode.AUTONOMOUS)

    def on_tracking_reset(self):
        """Tracking sıfırlandığında"""
        print("🔄 Tracking system reset")
        self.video_label.setText("Camera Feed\n(Tracking Reset)")
        self.video_label.setStyleSheet("background-color: black; color: white; font-size: 24px;")
        # Burada gerçek sistemde:
        # self.tracker.reset()
        # self.confidence_scorer.clear_history()

    def simulate_target_update(self):
        """Hedef listesini simüle et (test için)"""
        import random

        # Rastgele hedef listesi oluştur
        num_targets = random.randint(0, 5)
        new_targets = [random.randint(10, 99) for _ in range(num_targets)]

        print(f"📡 Detected targets: {new_targets}")
        self.control_panel.update_targets(new_targets)


def main():
    """Ana fonksiyon"""
    app = QApplication(sys.argv)

    # Ana pencereyi oluştur
    window = DroneTrackingGUI()
    window.show()

    print("=" * 60)
    print("AI Drone Tracking System - GUI Test")
    print("=" * 60)
    print("Keyboard Shortcuts:")
    print("  Space - Toggle target lock")
    print("  Esc   - Emergency stop")
    print("  D     - Toggle depth map")
    print("  T     - Toggle trajectory")
    print("  R     - Reset tracking")
    print("=" * 60)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
