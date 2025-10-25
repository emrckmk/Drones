# Drone Tracking System - GUI Kullanım Kılavuzu

## Dosya Yapısı

```
Drones/
├── control_panel.py    # Kontrol paneli widget'ı (tek başına kullanılabilir)
├── gui_example.py      # Tam entegrasyon örneği
└── GUI_README.md       # Bu dosya
```

## Kurulum

### Gereksinimler

```bash
pip install PyQt5
```

## Kullanım

### 1. Control Panel'i Tek Başına Test Etme

```bash
python3 control_panel.py
```

Bu komut sadece kontrol panelini açar ve tüm özellikleri test etmenizi sağlar.

### 2. Tam GUI Örneğini Çalıştırma

```bash
python3 gui_example.py
```

Bu komut video feed ve kontrol panelini içeren tam GUI'yi açar.

## Özellikler

### Widget'lar

| Widget | Açıklama | Kullanım |
|--------|----------|----------|
| **Target Dropdown** | Algılanan hedefler listesi | Dropdown'dan hedef seçin |
| **Lock Button** | Seçili hedefi kilitle/kilidi aç | Butona tıklayın veya Space tuşu |
| **Confidence Slider** | Güvenilirlik eşiği (0.3-0.9) | Slider'ı kaydırın |
| **Emergency Stop** | Tüm operasyonları durdur | Butona tıklayın veya Esc tuşu |
| **Depth Map Toggle** | Derinlik haritası gösterimi | Checkbox'ı işaretleyin veya D tuşu |
| **Trajectory Toggle** | Hedef yörüngesi gösterimi | Checkbox'ı işaretleyin veya T tuşu |
| **Mode Checkbox** | Manuel/Otonom mod geçişi | Checkbox'ı işaretleyin |
| **Reset Button** | Tracking sistemini sıfırla | Butona tıklayın veya R tuşu |

### Klavye Kısayolları

| Tuş | İşlev |
|-----|-------|
| **Space** | Hedef kilitleme aç/kapa |
| **Esc** | Acil durum durdurma |
| **D** | Depth map gösterimini aç/kapa |
| **T** | Trajectory gösterimini aç/kapa |
| **R** | Tracking sistemini sıfırla |

## Ana Programınıza Entegrasyon

### Adım 1: Import Edin

```python
from control_panel import ControlPanel
```

### Adım 2: Panel Oluşturun

```python
class YourMainGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # Control panel ekle
        self.control_panel = ControlPanel()

        # Layout'a ekle
        layout.addWidget(self.control_panel)
```

### Adım 3: Signal'ları Bağlayın

```python
# Hedef seçimi
self.control_panel.target_selected.connect(self.on_target_selected)

# Kilitleme
self.control_panel.lock_toggled.connect(self.on_lock_toggled)

# Güvenilirlik eşiği
self.control_panel.confidence_threshold_changed.connect(self.on_confidence_changed)

# Acil durum
self.control_panel.emergency_stop_triggered.connect(self.on_emergency_stop)

# Görünüm ayarları
self.control_panel.depth_overlay_toggled.connect(self.on_depth_toggle)
self.control_panel.trajectory_toggled.connect(self.on_trajectory_toggle)

# Mod değişimi
self.control_panel.mode_changed.connect(self.on_mode_changed)

# Reset
self.control_panel.tracking_reset.connect(self.on_tracking_reset)
```

### Adım 4: Handler Fonksiyonları Yazın

```python
def on_target_selected(self, target_id):
    """Hedef seçildiğinde"""
    self.flight_controller.set_target(target_id)
    print(f"Target {target_id} selected")

def on_lock_toggled(self, locked):
    """Kilitleme değiştiğinde"""
    self.flight_controller.set_lock(locked)

def on_confidence_changed(self, threshold):
    """Güvenilirlik eşiği değiştiğinde"""
    self.confidence_scorer.set_threshold(threshold)

def on_emergency_stop(self):
    """Acil durum"""
    self.drone.emergency_stop()
    self.flight_controller.halt()
```

### Adım 5: Hedef Listesini Güncelleyin

```python
# Her frame'de algılanan hedefleri güncelle
detected_target_ids = [12, 34, 56, 78]
self.control_panel.update_targets(detected_target_ids)
```

## Gerçek Sistem Entegrasyonu Örneği

```python
# main.py
import cv2
from control_panel import ControlPanel
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QTimer

class DroneTrackingSystem(QMainWindow):
    def __init__(self):
        super().__init__()

        # Modüller
        self.detector = ObjectDetector()
        self.tracker = MultiObjectTracker()
        self.flight_controller = FlightController()

        # GUI
        self.control_panel = ControlPanel()
        self.control_panel.emergency_stop_triggered.connect(self.emergency_stop)
        self.control_panel.lock_toggled.connect(self.set_target_lock)

        # Ana loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.timer.start(33)  # ~30 FPS

    def process_frame(self):
        # Frame al
        frame = self.camera.get_frame()

        # Algıla ve takip et
        detections = self.detector.detect(frame)
        tracks = self.tracker.update(detections)

        # GUI'yi güncelle
        target_ids = [t['id'] for t in tracks]
        self.control_panel.update_targets(target_ids)

        # Kontrol komutları
        velocity = self.flight_controller.compute_velocity(tracks)
        self.drone.send_velocity(velocity)

    def emergency_stop(self):
        """Acil durum protokolü"""
        self.drone.stop()
        self.flight_controller.halt()
        print("EMERGENCY STOP ACTIVATED")

    def set_target_lock(self, locked):
        """Hedef kilitleme"""
        self.flight_controller.set_lock(locked)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    system = DroneTrackingSystem()
    system.show()
    app.exec_()
```

## Özelleştirme

### Renkleri Değiştirme

`control_panel.py` içinde stylesheet'leri düzenleyin:

```python
self.lock_button.setStyleSheet("""
    QPushButton {
        background-color: #YOUR_COLOR;
        ...
    }
""")
```

### Yeni Widget Ekleme

```python
# control_panel.py içinde init_ui() fonksiyonuna ekleyin
self.your_widget = QWidget()
layout.addWidget(self.your_widget)
```

### Yeni Kısayol Ekleme

```python
# init_shortcuts() fonksiyonuna ekleyin
self.shortcut_new = QShortcut(QKeySequence(Qt.Key_N), self)
self.shortcut_new.activated.connect(self.your_function)
```

## Sorun Giderme

### PyQt5 Import Hatası

```bash
pip install --upgrade PyQt5
```

### Klavye Kısayolları Çalışmıyor

GUI penceresinin focus'ta olduğundan emin olun.

### Signal Çalışmıyor

Signal bağlantılarını `connect()` ile yaptığınızdan emin olun:

```python
self.control_panel.emergency_stop_triggered.connect(self.handler)
```

## Test Çıktısı

Başarılı çalıştırıldığında şu çıktıyı göreceksiniz:

```
============================================================
AI Drone Tracking System - GUI Test
============================================================
Keyboard Shortcuts:
  Space - Toggle target lock
  Esc   - Emergency stop
  D     - Toggle depth map
  T     - Toggle trajectory
  R     - Reset tracking
============================================================
📡 Detected targets: [12, 45, 67]
✓ Target #12 selected
🔒 Target LOCKED
📊 Confidence threshold set to: 0.65
```

## Lisans

MIT License - AI Drone Tracking System

## Destek

Sorunlarınız için issue açın veya dokümantasyonu inceleyin.
