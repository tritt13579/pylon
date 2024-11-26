import sys
import traceback
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QListWidget, QWidget, QHBoxLayout, QMessageBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QTimer
from pypylon import pylon
import numpy as np
import cv2

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
        try:
            # Sử dụng TlFactory để liệt kê các thiết bị
            tlFactory = pylon.TlFactory.GetInstance()
            self.cameras = tlFactory.EnumerateDevices()
            
            if not self.cameras:
                self.camera_list_widget.addItem("No cameras found.")
                return

            for cam in self.cameras:
                # Hiển thị thông tin chi tiết hơn
                camera_info = f"{cam.GetModelName()} (SN: {cam.GetSerialNumber()}) - {cam.GetDeviceClass()}"
                self.camera_list_widget.addItem(camera_info)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh camera list: {str(e)}")
            print(traceback.format_exc())

    def start_camera(self):
        """Bắt đầu hiển thị hình ảnh từ camera được chọn."""
        try:
            if not self.cameras:
                QMessageBox.warning(self, "Warning", "No cameras connected.")
                return

            # Lấy camera được chọn
            selected_index = self.camera_list_widget.currentRow()
            if selected_index < 0 or selected_index >= len(self.cameras):
                QMessageBox.warning(self, "Warning", "Please select a camera.")
                return

            # Khởi tạo camera
            tlFactory = pylon.TlFactory.GetInstance()
            self.selected_camera = pylon.InstantCamera(tlFactory.CreateDevice(self.cameras[selected_index]))
            
            # Mở camera với nhiều cấu hình
            self.selected_camera.Open()
            
            # Cấu hình một số thông số cơ bản nếu có thể
            if self.selected_camera.GetNodeMap().Contains("Width"):
                self.selected_camera.Width.SetValue(self.selected_camera.Width.GetMax())
            if self.selected_camera.GetNodeMap().Contains("Height"):
                self.selected_camera.Height.SetValue(self.selected_camera.Height.GetMax())

            # Bắt đầu chụp ảnh
            self.selected_camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

            # Bắt đầu timer để cập nhật hình ảnh
            self.timer.start(30)  # 30ms giữa các khung hình

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start camera: {str(e)}")
            print(traceback.format_exc())

    def update_frame(self):
        """Cập nhật hình ảnh từ camera với xử lý nâng cao."""
        try:
            if not self.selected_camera or not self.selected_camera.IsGrabbing():
                return

            # Lấy kết quả chụp với timeout
            grab_result = self.selected_camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

            if grab_result.GrabSucceeded():
                # Chuyển đổi ảnh một cách linh hoạt
                image = grab_result.GetArray()

                # Xử lý các định dạng màu khác nhau
                if len(image.shape) == 3:
                    # Nếu là ảnh màu
                    if image.shape[2] == 3:
                        # Chuyển từ BGR sang RGB nếu cần
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    elif image.shape[2] == 1:
                        # Nếu là ảnh xám
                        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
                elif len(image.shape) == 2:
                    # Chuyển ảnh xám sang RGB
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

                # Thay đổi kích thước nếu cần
                height, width, channel = image.shape
                bytes_per_line = channel * width

                # Tạo QImage
                q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)

                # Hiển thị hình ảnh
                pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = pixmap.scaled(self.image_label.size(), aspectRatioMode=1)  # Giữ tỷ lệ khung hình
                self.image_label.setPixmap(scaled_pixmap)

            # Giải phóng tài nguyên
            grab_result.Release()

        except Exception as e:
            print(f"Error updating frame: {e}")
            print(traceback.format_exc())

    def closeEvent(self, event):
        """Đóng ứng dụng và giải phóng tài nguyên."""
        try:
            self.timer.stop()
            if self.selected_camera:
                if self.selected_camera.IsGrabbing():
                    self.selected_camera.StopGrabbing()
                if self.selected_camera.IsOpen():
                    self.selected_camera.Close()
        except Exception as e:
            print(f"Error during close: {e}")
        finally:
            super().closeEvent(event)

# Chạy ứng dụng
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = CameraApp()
    main_window.show()
    sys.exit(app.exec_())