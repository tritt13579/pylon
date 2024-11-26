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
        self.setWindowTitle("Camera Viewer Pro")
        self.setGeometry(100, 100, 800, 600)

        # Tạo widget chính
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # Các widget
        self.camera_list_widget = QListWidget()
        self.refresh_button = QPushButton("Làm mới danh sách Camera")
        self.start_button = QPushButton("Bắt đầu chụp")
        self.status_label = QLabel("Trạng thái: Chưa kết nối")
        
        # Label hiển thị hình ảnh
        self.image_label = QLabel("Hình ảnh Camera")
        self.image_label.setFixedSize(640, 480)
        self.image_label.setStyleSheet("border: 2px solid gray;")

        # Layout điều khiển
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.refresh_button)
        control_layout.addWidget(self.start_button)

        # Thêm các widget vào layout chính
        self.layout.addWidget(QLabel("Danh sách Camera:"))
        self.layout.addWidget(self.camera_list_widget)
        self.layout.addLayout(control_layout)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.image_label)

        # Kết nối sự kiện
        self.refresh_button.clicked.connect(self.refresh_camera_list)
        self.start_button.clicked.connect(self.start_camera)

        # Khởi tạo biến
        self.cameras = []
        self.selected_camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Làm mới danh sách camera
        self.refresh_camera_list()

    def refresh_camera_list(self):
        self.camera_list_widget.clear()
        try:
            tlFactory = pylon.TlFactory.GetInstance()
            self.cameras = tlFactory.EnumerateDevices()
            
            if not self.cameras:
                self.status_label.setText("Không tìm thấy camera nào.")
                return

            for cam in self.cameras:
                camera_info = f"{cam.GetModelName()} (SN: {cam.GetSerialNumber()})"
                self.camera_list_widget.addItem(camera_info)
            
            self.status_label.setText(f"Tìm thấy {len(self.cameras)} camera.")
        except Exception as e:
            self.status_label.setText(f"Lỗi: {str(e)}")
            print(traceback.format_exc())

    def start_camera(self):
        try:
            if not self.cameras:
                self.status_label.setText("Không có camera nào kết nối.")
                return

            selected_index = self.camera_list_widget.currentRow()
            if selected_index < 0:
                self.status_label.setText("Vui lòng chọn một camera.")
                return

            # Đóng camera cũ nếu đang mở
            if self.selected_camera:
                self.selected_camera.Close()

            # Khởi tạo camera mới
            tlFactory = pylon.TlFactory.GetInstance()
            self.selected_camera = pylon.InstantCamera(tlFactory.CreateDevice(self.cameras[selected_index]))
            self.selected_camera.Open()

            # Cấu hình camera với nhiều chế độ
            nodemap = self.selected_camera.GetNodeMap()
            
            # Thử các cấu hình khác nhau
            try:
                # Thử đặt pixel format
                if nodemap.Contains("PixelFormat"):
                    pixel_formats = ["Mono8", "RGB8", "BGR8"]
                    for fmt in pixel_formats:
                        try:
                            self.selected_camera.PixelFormat.SetValue(fmt)
                            break
                        except:
                            continue
            except:
                pass

            # Bắt đầu chụp
            self.selected_camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            
            # Bắt đầu timer
            self.timer.start(50)  # Giảm thời gian giữa các khung hình
            self.status_label.setText("Đã bắt đầu chụp.")
        
        except Exception as e:
            self.status_label.setText(f"Lỗi: {str(e)}")
            print(traceback.format_exc())

    def update_frame(self):
        try:
            if not self.selected_camera or not self.selected_camera.IsGrabbing():
                return

            # Lấy hình ảnh
            grab_result = self.selected_camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            
            if grab_result.GrabSucceeded():
                # Lấy mảng hình ảnh
                image = grab_result.GetArray()

                # Xử lý nhiều định dạng
                if len(image.shape) == 2:  # Ảnh xám
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
                elif len(image.shape) == 3:
                    if image.shape[2] == 3:
                        # BGR sang RGB
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    elif image.shape[2] == 4:
                        # BGRA sang RGB
                        image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)

                # Chuyển sang QImage
                height, width, channel = image.shape
                bytes_per_line = channel * width
                q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)

                # Hiển thị
                pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = pixmap.scaled(self.image_label.size(), aspectRatioMode=1)
                self.image_label.setPixmap(scaled_pixmap)
                
                self.status_label.setText("Đang hiển thị hình ảnh...")
            
            grab_result.Release()
        
        except Exception as e:
            self.status_label.setText(f"Lỗi hiển thị: {str(e)}")
            print(traceback.format_exc())

    def closeEvent(self, event):
        try:
            self.timer.stop()
            if self.selected_camera:
                if self.selected_camera.IsGrabbing():
                    self.selected_camera.StopGrabbing()
                if self.selected_camera.IsOpen():
                    self.selected_camera.Close()
        except Exception as e:
            print(f"Lỗi đóng: {e}")
        finally:
            super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = CameraApp()
    main_window.show()
    sys.exit(app.exec_())