import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QListWidget, QWidget, QHBoxLayout
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QTimer
from pypylon import pylon
import numpy as np

class CameraApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Khởi tạo giao diện
        self.setWindowTitle("Camera Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # Danh sách các camera
        self.camera_list_widget = QListWidget()
        self.refresh_button = QPushButton("Refresh Camera List")
        self.start_button = QPushButton("Start Camera")
        self.image_label = QLabel("Camera Output")
        self.image_label.setFixedSize(640, 480)

        # Giao diện điều khiển
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.refresh_button)
        control_layout.addWidget(self.start_button)

        # Thêm vào layout chính
        self.layout.addWidget(QLabel("Connected Cameras:"))
        self.layout.addWidget(self.camera_list_widget)
        self.layout.addLayout(control_layout)
        self.layout.addWidget(self.image_label)

        # Kết nối các nút với hàm
        self.refresh_button.clicked.connect(self.refresh_camera_list)
        self.start_button.clicked.connect(self.start_camera)

        # Biến camera
        self.cameras = []
        self.selected_camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Lấy danh sách camera khi khởi động
        self.refresh_camera_list()

    def refresh_camera_list(self):
        """Làm mới danh sách camera được kết nối."""
        self.camera_list_widget.clear()
        self.cameras = pylon.TlFactory.GetInstance().EnumerateDevices()
        for cam in self.cameras:
            self.camera_list_widget.addItem(f"{cam.GetModelName()} ({cam.GetSerialNumber()})")
        if not self.cameras:
            self.camera_list_widget.addItem("No cameras found.")

    def start_camera(self):
        """Bắt đầu hiển thị hình ảnh từ camera được chọn."""
        if not self.cameras:
            self.image_label.setText("No camera connected.")
            return

        # Lấy camera được chọn
        selected_index = self.camera_list_widget.currentRow()
        if selected_index < 0 or selected_index >= len(self.cameras):
            self.image_label.setText("Please select a camera.")
            return

        # Khởi tạo camera
        self.selected_camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(self.cameras[selected_index]))
        self.selected_camera.Open()
        self.selected_camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        # Bắt đầu hiển thị hình ảnh
        self.timer.start(30)

    def update_frame(self):
        """Cập nhật hình ảnh từ camera."""
        if self.selected_camera and self.selected_camera.IsGrabbing():
            grab_result = self.selected_camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

            if grab_result.GrabSucceeded():
                # Chuyển ảnh sang định dạng OpenCV
                image = grab_result.Array
                height, width, channels = image.shape if len(image.shape) == 3 else (*image.shape, 1)
                bytes_per_line = channels * width

                # Chuyển sang định dạng QImage
                q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)

                # Hiển thị hình ảnh
                pixmap = QPixmap.fromImage(q_image)
                self.image_label.setPixmap(pixmap)

            grab_result.Release()

    def closeEvent(self, event):
        """Đóng ứng dụng và giải phóng tài nguyên."""
        self.timer.stop()
        if self.selected_camera:
            self.selected_camera.StopGrabbing()
            self.selected_camera.Close()
        super().closeEvent(event)

# Chạy ứng dụng
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = CameraApp()
    main_window.show()
    sys.exit(app.exec_())
