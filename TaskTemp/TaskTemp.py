import os
import platform
import subprocess
import tempfile
import logging

from krita import Krita, DockWidgetFactory, DockWidgetFactoryBase, DockWidget
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QDialog, QCheckBox, QDialogButtonBox, QSlider
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont


# Configure logging
def setup_logging():
    log_directory = os.path.join(tempfile.gettempdir(), 'krita_TaskTemp')
    os.makedirs(log_directory, exist_ok=True)
    log_file_path = os.path.join(log_directory, 'krita_TaskTemp.log')

    logging.basicConfig(filename=log_file_path, level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

logger = setup_logging()


class TaskTempDocker(DockWidget):
    def __init__(self):
        super(TaskTempDocker, self).__init__()
        self.setWindowTitle("TaskTemp")
        self.widget = QWidget(self)
        self.main_layout = QHBoxLayout(self.widget)

        self.init_ui()
        self.init_settings()

        self.system_info_thread = SystemInfoThread()
        self.system_info_thread.system_info_signal.connect(self.update_system_info)
        self.system_info_thread.start()

    def init_ui(self):
        """Initialize the UI components."""
        # GPU section
        self.gpu_layout = QVBoxLayout()
        self.gpu_label = QLabel("Initializing GPU Info...", self.widget)
        self.gpu_layout.addWidget(self.gpu_label)

        # CPU and RAM section
        self.cpu_ram_layout = QVBoxLayout()
        self.cpu_label = QLabel("Initializing CPU Info...", self.widget)
        self.ram_label = QLabel("Initializing RAM Info...", self.widget)
        self.cpu_ram_layout.addWidget(self.cpu_label)
        self.cpu_ram_layout.addWidget(self.ram_label)

        # Add layouts to the main layout
        self.main_layout.addLayout(self.gpu_layout)
        self.main_layout.addLayout(self.cpu_ram_layout)

        # Create the settings button
        self.settings_button = QPushButton("⚙", self.widget)
        self.settings_button.setFixedSize(24, 24)
        self.settings_button.setStyleSheet("QPushButton { border: none; }")
        self.settings_button.clicked.connect(self.open_settings)

        # Add the settings button to the main layout
        self.main_layout.addWidget(self.settings_button, alignment=Qt.AlignTop | Qt.AlignRight)

        self.widget.setLayout(self.main_layout)
        self.setWidget(self.widget)

        # Set up a QTimer to update the labels periodically
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_label)
        self.timer.start(1000)  # Update every second

    def init_settings(self):
        """Initialize the settings."""
        self.settings_dialog = None
        self.font_size = 10  # Default font size
        self.bold_values = False  # Default bold setting

        # Initialize display settings
        self.show_cpu = True
        self.show_ram = True
        self.show_gpu_usage = True
        self.show_gpu_temp = True
        self.show_gpu_clock_speed = True
        self.show_gpu_memory_usage = True

        # Initialize system information variables
        self.total_cpu_usage = 0.0
        self.ram_usage = 0.0
        self.gpu_usage = 0
        self.gpu_temp = 0
        self.gpu_clock_speed = 0
        self.gpu_memory_usage = 0

    def update_label(self):
        """Update the label with current system information."""
        try:
            cpu_info = f"CPU Usage: {self.format_value(f'{self.total_cpu_usage:.2f}')}%"
            ram_info = f"RAM Usage: {self.format_value(f'{self.ram_usage:.2f}')} MB"
            gpu_info = ""
            if self.show_gpu_usage:
                gpu_info += f"GPU Usage: {self.format_value(f'{self.gpu_usage}')}%<br>"
            if self.show_gpu_temp:
                gpu_info += f"GPU Temp: {self.format_value(f'{self.gpu_temp}')}C<br>"
            if self.show_gpu_clock_speed:
                gpu_info += f"GPU Clock Speed: {self.format_value(f'{self.gpu_clock_speed}')} MHz<br>"
            if self.show_gpu_memory_usage:
                gpu_info += f"GPU Memory Usage: {self.format_value(f'{self.gpu_memory_usage}')} MB"

            self.cpu_label.setText(cpu_info)
            self.ram_label.setText(ram_info)
            self.gpu_label.setText(gpu_info)

            # Update font size
            font = QFont()
            font.setPointSize(self.font_size)
            self.cpu_label.setFont(font)
            self.ram_label.setFont(font)
            self.gpu_label.setFont(font)
        except Exception as e:
            self.cpu_label.setText(f"Error: {e}")
            self.ram_label.setText(f"Error: {e}")
            self.gpu_label.setText(f"Error: {e}")

    def format_value(self, value):
        """Format the value with bold if required."""
        return f"<b>{value}</b>" if self.bold_values else value

    def update_system_info(self, total_cpu_usage, ram_usage, gpu_usage, gpu_temp, gpu_clock_speed, gpu_memory_usage):
        """Update the system information variables."""
        self.total_cpu_usage = total_cpu_usage
        self.ram_usage = ram_usage
        self.gpu_usage = gpu_usage
        self.gpu_temp = gpu_temp
        self.gpu_clock_speed = gpu_clock_speed
        self.gpu_memory_usage = gpu_memory_usage

    def open_settings(self):
        """Open the settings dialog."""
        if not self.settings_dialog:
            self.settings_dialog = SettingsDialog(self)
            self.settings_dialog.settings_changed.connect(self.apply_settings)
            self.settings_dialog.font_size_changed.connect(self.set_font_size)
            self.settings_dialog.bold_values_changed.connect(self.set_bold_values)
        try:
            self.settings_dialog.show()
        except Exception as e:
            logger.error(f"Error opening settings dialog: {e}")

    def apply_settings(self, show_cpu, show_ram, show_gpu_usage, show_gpu_temp, show_gpu_clock_speed, show_gpu_memory_usage):
        """Apply the settings."""
        self.show_cpu = show_cpu
        self.show_ram = show_ram
        self.show_gpu_usage = show_gpu_usage
        self.show_gpu_temp = show_gpu_temp
        self.show_gpu_clock_speed = show_gpu_clock_speed
        self.show_gpu_memory_usage = show_gpu_memory_usage
        self.update_label()

    def set_font_size(self, font_size):
        """Set the font size for the labels."""
        self.font_size = font_size
        self.update_label()

    def set_bold_values(self, bold_values):
        """Set whether the values should be bold."""
        self.bold_values = bold_values
        self.update_label()

    def canvasChanged(self, *args, **kwargs):
        """Handle the canvas change event."""
        logger.info("Canvas has been changed.")


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(bool, bool, bool, bool, bool, bool)
    font_size_changed = pyqtSignal(int)
    bold_values_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("TaskTemp Settings")

        self.layout = QVBoxLayout(self)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components."""
        self.checkbox_cpu = QCheckBox("Show CPU Usage", self)
        self.checkbox_ram = QCheckBox("Show RAM Usage", self)
        self.checkbox_gpu_usage = QCheckBox("Show GPU Usage", self)
        self.checkbox_gpu_temp = QCheckBox("Show GPU Temp", self)
        self.checkbox_gpu_clock_speed = QCheckBox("Show GPU Clock Speed", self)
        self.checkbox_gpu_memory_usage = QCheckBox("Show GPU Memory Usage", self)

        self.checkbox_cpu.setChecked(True)
        self.checkbox_ram.setChecked(True)
        self.checkbox_gpu_usage.setChecked(True)
        self.checkbox_gpu_temp.setChecked(True)
        self.checkbox_gpu_clock_speed.setChecked(True)
        self.checkbox_gpu_memory_usage.setChecked(True)

        self.layout.addWidget(self.checkbox_cpu)
        self.layout.addWidget(self.checkbox_ram)
        self.layout.addWidget(self.checkbox_gpu_usage)
        self.layout.addWidget(self.checkbox_gpu_temp)
        self.layout.addWidget(self.checkbox_gpu_clock_speed)
        self.layout.addWidget(self.checkbox_gpu_memory_usage)

        self.font_size_slider = QSlider(Qt.Horizontal, self)
        self.font_size_slider.setMinimum(6)
        self.font_size_slider.setMaximum(24)
        self.font_size_slider.setValue(10)
        self.font_size_slider.setTickPosition(QSlider.TicksBelow)
        self.font_size_slider.setTickInterval(1)
        self.font_size_slider.valueChanged.connect(self.font_size_slider_changed)

        self.bold_values_checkbox = QCheckBox("Bold Values", self)
        self.bold_values_checkbox.stateChanged.connect(self.bold_values_checkbox_changed)

        self.layout.addWidget(QLabel("Font Size:", self))
        self.layout.addWidget(self.font_size_slider)
        self.layout.addWidget(self.bold_values_checkbox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)

    def accept(self):
        """Accept the settings changes and emit signals."""
        super(SettingsDialog, self).accept()
        self.settings_changed.emit(
            self.checkbox_cpu.isChecked(),
            self.checkbox_ram.isChecked(),
            self.checkbox_gpu_usage.isChecked(),
            self.checkbox_gpu_temp.isChecked(),
            self.checkbox_gpu_clock_speed.isChecked(),
            self.checkbox_gpu_memory_usage.isChecked()
        )
        self.font_size_changed.emit(self.font_size_slider.value())
        self.bold_values_changed.emit(self.bold_values_checkbox.isChecked())

    def font_size_slider_changed(self):
        """Emit font size changed signal."""
        self.font_size_changed.emit(self.font_size_slider.value())

    def bold_values_checkbox_changed(self):
        """Emit bold values changed signal."""
        self.bold_values_changed.emit(self.bold_values_checkbox.isChecked())


class SystemInfoThread(QThread):
    system_info_signal = pyqtSignal(float, float, int, int, int, int)

    def run(self):
        """Run the system information gathering thread."""
        while True:
            total_cpu_usage = self.get_total_cpu_usage()
            ram_usage = self.get_ram_usage()
            gpu_usage, gpu_temp, gpu_clock_speed, gpu_memory_usage = self.get_gpu_info()
            self.system_info_signal.emit(total_cpu_usage, ram_usage, gpu_usage, gpu_temp, gpu_clock_speed, gpu_memory_usage)
            self.msleep(1000)  # Sleep for 1 second

    def get_total_cpu_usage(self):
        """Get total CPU usage."""
        if platform.system() == "Windows":
            return self.get_total_cpu_usage_windows()
        else:
            return self.get_total_cpu_usage_unix()

    def get_total_cpu_usage_windows(self):
        """Get total CPU usage on Windows."""
        try:
            result = subprocess.run(
                ['wmic', 'cpu', 'get', 'loadpercentage'],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output = result.stdout.strip().split('\n')
            if len(output) > 1:
                for line in output:
                    if line.strip().isdigit():
                        return float(line.strip())
            logger.warning(f"Unexpected output from wmic: {output}")
            return 0.0
        except Exception as e:
            logger.error(f"Error getting total CPU usage: {e}")
            return 0.0

    def get_total_cpu_usage_unix(self):
        """Get total CPU usage on Unix-based systems."""
        try:
            result = subprocess.run(
                ['top', '-bn1'],
                capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if "Cpu(s)" in line:
                    return float(line.split()[1])
        except Exception as e:
            logger.error(f"Error getting total CPU usage: {e}")
        return 0.0

    def get_ram_usage(self):
        """Get RAM usage."""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['wmic', 'OS', 'get', 'TotalVisibleMemorySize,FreePhysicalMemory', '/VALUE'],
                    capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                output = result.stdout.strip().split('\n')
                total_memory = None
                free_memory = None
                for line in output:
                    if "TotalVisibleMemorySize" in line:
                        total_memory = int(line.split('=')[1].strip())
                    elif "FreePhysicalMemory" in line:
                        free_memory = int(line.split('=')[1].strip())
                if total_memory is not None and free_memory is not None:
                    used_memory = (total_memory - free_memory) / 1024  # Convert to MB
                    return used_memory
                logger.warning(f"Unexpected output from wmic: {output}")
            else:
                result = subprocess.run(
                    ['free', '-m'],
                    capture_output=True, text=True)
                output = result.stdout.strip().split('\n')
                if len(output) > 1:
                    memory_info = output[1].split()
                    return float(memory_info[2])  # Used memory in MB
        except Exception as e:
            logger.error(f"Error getting RAM usage: {e}")
        return 0.0

    def get_gpu_info(self):
        """Get GPU information."""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu,clocks.gr,memory.used', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output = result.stdout.strip()
            if output:
                usage, temp, clock_speed, memory_usage = map(int, output.split(', '))
                return usage, temp, clock_speed, memory_usage
            else:
                logger.warning("No output from nvidia-smi")
                return 0, 0, 0, 0
        except Exception as e:
            logger.error(f"Error getting GPU info: {e}")
            return 0, 0, 0, 0


# Register the Docker
print("Registering Docker")
dock_widget_factory = DockWidgetFactory("TaskTemp_docker",
                                        DockWidgetFactoryBase.DockRight,
                                        TaskTempDocker)
Krita.instance().addDockWidgetFactory(dock_widget_factory)
print("Docker registered")
