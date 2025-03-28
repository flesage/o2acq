import sys
import logging
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QComboBox, QLabel, 
                           QFileDialog, QCheckBox, QGroupBox, QLineEdit,
                           QSlider, QSizePolicy, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
import pyqtgraph as pg
import numpy as np
from typing import List

from controllers.camera_controller import CameraController
from controllers.nidaq_controller import NIDAQController
from services.image_acquisition import ImageAcquisitionService
from services.data_storage import DataStorageService
from models.state_manager import StateManager, AcquisitionState

def setup_logging():
    """Initialize logging system"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"o2acq_{timestamp}.log"
    
    # Create logger
    logger = logging.getLogger("O2Acq")
    logger.setLevel(logging.DEBUG)
    
    # Create handlers
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Add formatter to handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info("Logging system initialized")
    return logger

class MainWindow(QMainWindow):
    def __init__(self, logger):
        super().__init__()
        self.setWindowTitle("O2Acq")
        self.setGeometry(100, 100, 1200, 800)

        # Store logger
        self.logger = logger
        self.logger.info("Initializing MainWindow")

        # Initialize controllers and services
        try:
            self.camera_controller = CameraController(self.logger)
            if self.camera_controller.camera is None:
                raise Exception("Failed to initialize camera")
                
            self.daq_controller = NIDAQController(self.logger)
            self.data_storage = DataStorageService(self.logger)
            
            # Initialize state manager with default values
            self.state_manager = StateManager()
            self.state_manager.update_state(
                acquisition_state=AcquisitionState.IDLE,
                active_modes=["Bioluminescence"],  # Set bioluminescence as default active mode
                current_frequency=1.0,  # Default to 1 Hz
                em_gain=0,
                amp_gain=1,
                biolum_exposure=700,
                fluo_exposure=10,
                temperature_stabilized=False
            )
            
            # Initialize ROI data with separate lists for each mode
            self.roi_data = {
                "Bioluminescence": [],
                "Blue": [],
                "Green": []
            }
            self.roi_plot = None
            
            # Temperature labels
            self.temp_value_label = None
            self.temp_status_label = None
            
            # Initialize image storage for each mode
            self.current_images = {
                "Bioluminescence": None,
                "Blue": None,
                "Green": None
            }
            
            # Setup UI
            self.setup_ui()
            
            # Connect state manager
            self.state_manager.add_observer(self)
            
            # Start temperature monitoring
            self.setup_temperature_monitoring()
            
            self.logger.info("MainWindow initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing MainWindow: {e}")
            QMessageBox.critical(None, "Initialization Error",
                               f"Failed to initialize application: {str(e)}\n"
                               "The application will now close.")
            sys.exit(1)

    def setup_ui(self):
        """Setup the user interface"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Left side: Image display and plot
        left_layout = self.setup_left_panel()
        layout.addLayout(left_layout)
        
        # Right side: Control panel
        control_panel = self.setup_control_panel()
        layout.addWidget(control_panel)

    def setup_left_panel(self):
        """Setup the left panel with image display and ROI plot"""
        layout = QVBoxLayout()
        
        # Create a widget to contain the image view for better size control
        image_container = QWidget()
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add display mode selection
        display_layout = QHBoxLayout()
        display_layout.addWidget(QLabel("Display Mode:"))
        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItems(["Bioluminescence", "Blue", "Green"])
        self.display_mode_combo.currentTextChanged.connect(self.on_display_mode_changed)
        display_layout.addWidget(self.display_mode_combo)
        display_layout.addStretch()
        image_layout.addLayout(display_layout)
        
        # Image display
        self.image_view = pg.ImageView()
        image_layout.addWidget(self.image_view)
        
        # Set size policy for the image container
        image_container.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        
        # Add ROI
        self.setup_roi()
        
        # Plot widget for ROI data
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Average Intensity')
        self.plot_widget.setLabel('bottom', 'Frame')
        self.roi_plot = self.plot_widget.plot(pen='r')
        
        # Set size policies
        self.plot_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        
        # Add widgets to layout with stretch factors
        layout.addWidget(image_container, stretch=2)
        layout.addWidget(self.plot_widget, stretch=1)
        
        return layout

    def setup_roi(self):
        """Setup Region of Interest on the image"""
        # Create ROI
        self.roi = pg.RectROI([20, 20], [20, 20], pen='r')
        self.image_view.addItem(self.roi)
        
        # Connect ROI change signal
        self.roi.sigRegionChanged.connect(self.update_roi)

    def update_roi(self):
        """Update ROI data when ROI changes"""
        if self.image_view.image is None:
            return
            
        # Get current mode
        current_mode = self.display_mode_combo.currentText()
        if not current_mode:
            return
            
        # Get ROI data
        roi_data = self.roi.getArrayRegion(self.image_view.image, self.image_view.imageItem)
        
        if roi_data is not None:
            # Calculate mean intensity in ROI
            mean_intensity = np.mean(roi_data)
            self.roi_data[current_mode].append(mean_intensity)
            
            # Update plot for current mode
            self.roi_plot.setData(self.roi_data[current_mode])

    def setup_control_panel(self):
        """Setup the right control panel"""
        control_widget = QWidget()
        layout = QVBoxLayout(control_widget)
        
        # Camera settings group
        camera_group = QGroupBox("Camera Settings")
        camera_layout = QVBoxLayout()
        
        # Temperature display with current value and status
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature:"))
        self.temp_value_label = QLabel("--°C")  # Initialize temperature value label
        self.temp_status_label = QLabel("Not stabilized")  # Initialize status label
        self.temp_status_label.setStyleSheet("QLabel { color: red; }")
        temp_layout.addWidget(self.temp_value_label)
        temp_layout.addWidget(self.temp_status_label)
        temp_layout.addStretch()
        camera_layout.addLayout(temp_layout)

        # Add override checkbox
        self.temp_override_check = QCheckBox("Allow start without temperature stabilization")
        self.temp_override_check.setChecked(False)
        self.temp_override_check.stateChanged.connect(self.update_start_button_state)
        camera_layout.addWidget(self.temp_override_check)
        
        # EM gain
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("EM Gain:"))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(0, 300)
        self.gain_slider.setValue(0)
        self.gain_value_label = QLabel("0")
        gain_layout.addWidget(self.gain_slider)
        gain_layout.addWidget(self.gain_value_label)
        camera_layout.addLayout(gain_layout)
        
        # Connect gain slider to value update
        self.gain_slider.valueChanged.connect(
            lambda v: self.gain_value_label.setText(str(v))
        )
        
        # Amplifier gain
        amp_layout = QHBoxLayout()
        amp_layout.addWidget(QLabel("Amp Gain:"))
        self.amp_combo = QComboBox()
        self.amp_combo.addItems(['1', '2', '3'])
        amp_layout.addWidget(self.amp_combo)
        camera_layout.addLayout(amp_layout)
        
        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)
        
        # Acquisition settings group
        acq_group = QGroupBox("Acquisition Settings")
        acq_layout = QVBoxLayout()
        
        # Mode selection
        self.biolum_check = QCheckBox("Bioluminescence")
        self.biolum_check.setChecked(True)  # Set checked by default
        self.blue_check = QCheckBox("Blue")
        self.green_check = QCheckBox("Green")
        acq_layout.addWidget(self.biolum_check)
        acq_layout.addWidget(self.blue_check)
        acq_layout.addWidget(self.green_check)
        
        # Connect mode checkboxes to start button update
        self.biolum_check.stateChanged.connect(self.update_start_button_state)
        self.blue_check.stateChanged.connect(self.update_start_button_state)
        self.green_check.stateChanged.connect(self.update_start_button_state)
        
        # Exposure times with validation
        biolum_exp_layout = QHBoxLayout()
        biolum_exp_layout.addWidget(QLabel("Biolum Exp (ms):"))
        self.biolum_exposure = QLineEdit("700")
        self.biolum_exposure.textChanged.connect(lambda: self.validate_exposure_time(self.biolum_exposure))
        biolum_exp_layout.addWidget(self.biolum_exposure)
        acq_layout.addLayout(biolum_exp_layout)
        
        fluo_exp_layout = QHBoxLayout()
        fluo_exp_layout.addWidget(QLabel("Fluo Exp (ms):"))
        self.fluo_exposure = QLineEdit("10")
        self.fluo_exposure.textChanged.connect(lambda: self.validate_exposure_time(self.fluo_exposure))
        fluo_exp_layout.addWidget(self.fluo_exposure)
        acq_layout.addLayout(fluo_exp_layout)
        
        # Frequency selection
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Frequency:"))
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(['0.5 Hz', '1 Hz', '2 Hz', '30 Hz'])
        self.freq_combo.currentTextChanged.connect(self.on_frequency_changed)
        freq_layout.addWidget(self.freq_combo)
        acq_layout.addLayout(freq_layout)
        
        acq_group.setLayout(acq_layout)
        layout.addWidget(acq_group)
        
        # Save settings group
        save_group = QGroupBox("Save Settings")
        save_layout = QVBoxLayout()
        
        self.save_toggle = QCheckBox("Enable Saving")
        save_layout.addWidget(self.save_toggle)
        
        self.save_dir_label = QLabel("Save directory:\nNo directory selected")
        save_layout.addWidget(self.save_dir_label)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_save_directory)
        save_layout.addWidget(self.browse_button)
        
        save_group.setLayout(save_layout)
        layout.addWidget(save_group)
        
        # Start/Stop buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_acquisition)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_acquisition)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)
        
        return control_widget

    def setup_temperature_monitoring(self):
        """Setup temperature monitoring timer"""
        if not hasattr(self, 'camera_controller') or self.camera_controller.camera is None:
            self.logger.error("Cannot setup temperature monitoring: Camera not initialized")
            return
            
        # Create and start timer
        self.temp_timer = QTimer(self)
        self.temp_timer.timeout.connect(self.update_temperature)
        self.temp_timer.start(1000)  # Update every second
        
        # Force initial update
        QTimer.singleShot(100, self.update_temperature)  # Delay first update slightly
        self.logger.info("Temperature monitoring started")

    def update_temperature(self):
        """Update temperature status"""
        try:
            if not hasattr(self, 'camera_controller') or self.camera_controller.camera is None:
                self.logger.error("Cannot update temperature: Camera not initialized")
                return
                
            temp = self.camera_controller.get_temperature()
            status = self.camera_controller.get_temperature_status()
            
            if temp is not None:
                # Update temperature value
                self.temp_value_label.setText(f"{temp:.1f}°C")
                
                # Update status with color
                status_color = "green" if status == "stabilized" else "red"
                self.temp_status_label.setText(f"({status})")
                self.temp_status_label.setStyleSheet(f"QLabel {{ color: {status_color}; }}")
                
                # Force update
                self.temp_value_label.repaint()
                self.temp_status_label.repaint()
                
                # Update state
                self.state_manager.update_state(
                    temperature_stabilized=(status == "stabilized")
                )
                
                # Update start button state
                self.update_start_button_state()
                
        except Exception as e:
            self.logger.error(f"Error updating temperature: {e}")

    def validate_acquisition_ready(self) -> bool:
        """Check if system is ready for acquisition"""
        # Check temperature stabilization (unless override is checked)
        if not self.state_manager.state.temperature_stabilized and not self.temp_override_check.isChecked():
            self.logger.warning("Cannot start: Temperature not stabilized")
            return False
            
        # Check if at least one mode is selected
        modes = self.get_active_modes()
        if not modes:
            self.logger.warning("Cannot start: No acquisition mode selected")
            return False
            
        return True

    def update_start_button_state(self):
        """Update start button enabled state based on system readiness"""
        ready = self.validate_acquisition_ready()
        self.start_button.setEnabled(ready)
        
        if not ready:
            tooltip = []
            if not self.state_manager.state.temperature_stabilized and not self.temp_override_check.isChecked():
                tooltip.append("Temperature not stabilized")
            if not self.get_active_modes():
                tooltip.append("No acquisition mode selected")
            
            self.start_button.setToolTip("\n".join(tooltip))
        else:
            self.start_button.setToolTip("")

    def update_ui_state(self, state):
        """Update UI based on state changes"""
        try:
            # Update temperature display
            if hasattr(state, 'temperature_stabilized'):
                if state.temperature_stabilized:
                    self.temp_status_label.setText("(stabilized)")
                    self.temp_status_label.setStyleSheet("QLabel { color: green; }")
                else:
                    self.temp_status_label.setText("(not stabilized)")
                    self.temp_status_label.setStyleSheet("QLabel { color: red; }")
            
            # Update acquisition controls
            if state.acquisition_state == AcquisitionState.RUNNING:
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
            else:
                self.update_start_button_state()
                self.stop_button.setEnabled(False)
                
        except Exception as e:
            self.logger.error(f"Error updating UI state: {e}")

    def get_active_modes(self) -> list:
        """Get list of active acquisition modes"""
        modes = []
        if self.biolum_check.isChecked():
            modes.append("Bioluminescence")
        if self.blue_check.isChecked():
            modes.append("Blue")
        if self.green_check.isChecked():
            modes.append("Green")
        return modes

    def browse_save_directory(self):
        """Open directory browser for save location"""
        directory = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if directory:
            self.save_dir_label.setText(f"Save directory:\n{directory}")
            self.data_storage.set_save_path(directory)

    def closeEvent(self, event):
        """Handle application shutdown"""
        try:
            if hasattr(self, 'temp_timer'):
                self.temp_timer.stop()
                
            if hasattr(self, 'acq_service'):
                self.acq_service.stop()
                
            if hasattr(self, 'camera_controller') and self.camera_controller.camera is not None:
                # Ensure shutter is closed
                self.logger.info("Closing camera shutter...")
                self.camera_controller.camera.setup_shutter("closed")
                # Close camera
                self.camera_controller.close()
                
            self.logger.info("Application closed")
            event.accept()
        except Exception as e:
            self.logger.error(f"Error during application shutdown: {e}")
            event.accept()

    def start_acquisition(self):
        """Start the acquisition process"""
        if not self.validate_acquisition_ready():
            return
            
        try:
            # Get active modes first
            active_modes = self.get_active_modes()
            if not active_modes:
                self.logger.warning("Cannot start: No acquisition mode selected")
                return
                
            # Clear ROI data for active modes
            self.roi_data = {mode: [] for mode in active_modes}
            self.roi_plot.setData([])  # Clear plot

            # Clear current images
            self.current_images = {mode: None for mode in active_modes}
            
            # Update display mode options to only show active modes
            self.display_mode_combo.clear()
            self.display_mode_combo.addItems(active_modes)
            self.display_mode_combo.setCurrentIndex(0)  # Select first active mode
            
            # Clear current display
            self.image_view.clear()

            # Update state
            frequency = float(self.freq_combo.currentText().split()[0])
            self.state_manager.update_state(
                acquisition_state=AcquisitionState.RUNNING,
                active_modes=active_modes,
                current_frequency=frequency
            )

            # Configure camera 
            em_gain = self.gain_slider.value()
            amp_gain = int(self.amp_combo.currentText())
            exposure_time = int(self.biolum_exposure.text())/1000.0
                         
            if not self.camera_controller.start_acquisition(em_gain, amp_gain, exposure_time):
                raise Exception("Failed to start camera acquisition")

            # Start NI-DAQ
            freq = self.state_manager.state.current_frequency
            modes = [
                "Bioluminescence" in active_modes,
                "Blue" in active_modes,
                "Green" in active_modes,
                True  # Line 4 always active for exposure triggers
            ]
            biolum_exp = int(self.biolum_exposure.text())
            fluo_exp = int(self.fluo_exposure.text())
            
            if not self.daq_controller.start_task(freq, modes, biolum_exp, fluo_exp):
                raise Exception("Failed to start DAQ task")

            # Start image acquisition service
            self.acq_service = ImageAcquisitionService(
                self.camera_controller.camera,
                self.logger
            )
            self.acq_service.set_frame_timeout(freq)  # Set appropriate timeout
            self.acq_service.image_acquired.connect(self.handle_new_image)
            self.acq_service.acquisition_error.connect(self.handle_acquisition_error)
            self.acq_service.set_active_modes(active_modes)
            self.acq_service.set_save_enabled(self.save_toggle.isChecked())
            self.acq_service.start()
            
            # Update UI
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
        except Exception as e:
            self.logger.error(f"Error starting acquisition: {e}")
            self.stop_acquisition()

    def stop_acquisition(self):
        """Stop the acquisition process"""
        try:
            # Stop acquisition service
            if hasattr(self, 'acq_service'):
                self.acq_service.stop()
                
                # Add debug logging for saved images
                if hasattr(self.acq_service, 'saved_images'):
                    for mode, images in self.acq_service.saved_images.items():
                        self.logger.debug(f"Mode {mode}: {len(images) if images else 0} images collected")
                
                # Save data if enabled
                if (self.save_toggle.isChecked() and 
                    hasattr(self.acq_service, 'saved_images') and 
                    any(len(imgs) > 0 for imgs in self.acq_service.saved_images.values())):
                    
                    self.logger.info("Saving acquired images...")
                    if not self.data_storage.save_path:
                        self.logger.error("Cannot save: No save directory selected")
                    else:
                        success = self.data_storage.save_image_stacks(self.acq_service.saved_images)
                        if not success:
                            self.logger.error("Failed to save image stacks")
                else:
                    self.logger.warning("No images to save or saving disabled")
                
                delattr(self, 'acq_service')
                
            # Stop NI-DAQ
            self.daq_controller.stop_task()
            
            # Stop camera and close shutter
            self.camera_controller.stop_acquisition()
            self.logger.info("Closing camera shutter...")
            self.camera_controller.camera.setup_shutter("closed")
            
            # Update state
            self.state_manager.update_state(
                acquisition_state=AcquisitionState.IDLE
            )
            
            # Update UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
            # Clear current images and display
            self.current_images = {
                "Bioluminescence": None,
                "Blue": None,
                "Green": None
            }
            self.image_view.clear()
            
            # Reset display mode options to all possible modes
            self.display_mode_combo.clear()
            self.display_mode_combo.addItems(["Bioluminescence", "Blue", "Green"])
            
            # Clear ROI data
            self.roi_data = {
                "Bioluminescence": [],
                "Blue": [],
                "Green": []
            }
            self.roi_plot.setData([])  # Clear plot
            
        except Exception as e:
            self.logger.error(f"Error stopping acquisition: {e}")

    def handle_new_image(self, mode: str, image_data: np.ndarray):
        """Handle newly acquired image"""
        try:
            # Store the new image for this mode
            self.current_images[mode] = image_data.copy()
            
            # Force update display if this is the selected mode
            selected_mode = self.display_mode_combo.currentText()
            if mode == selected_mode:
                self.update_display(mode)
                
        except Exception as e:
            self.logger.error(f"Error handling new image: {e}")

    def handle_acquisition_error(self, error_msg):
        """Handle errors from acquisition service"""
        self.logger.error(f"Acquisition error: {error_msg}")
        QMessageBox.critical(self, "Acquisition Error",
                           f"Error during acquisition: {error_msg}")
        self.stop_acquisition()

    def resizeEvent(self, event):
        """Handle window resize event to maintain image aspect ratio"""
        super().resizeEvent(event)
        
        # Update image view to maintain square aspect ratio
        if hasattr(self, 'image_view'):
            view_box = self.image_view.getView()
            view_box.setAspectLocked(True, 1.0)  # Lock aspect ratio to 1:1

    def update_display_modes(self, active_modes: List[str]):
        """Update the display mode combo box with active modes"""
        current = self.display_mode_combo.currentText()
        self.display_mode_combo.clear()
        self.display_mode_combo.addItems(active_modes)
        
        # Try to restore previous selection if still available
        index = self.display_mode_combo.findText(current)
        if index >= 0:
            self.display_mode_combo.setCurrentIndex(index)

    def on_display_mode_changed(self, mode: str):
        """Handle display mode selection change"""
        try:
            self.update_display(mode)
            # Update plot for new mode
            if mode in self.roi_data:
                self.roi_plot.setData(self.roi_data[mode])
        except Exception as e:
            self.logger.error(f"Error changing display mode: {e}")

    def update_display(self, mode: str):
        """Update display with current image for specified mode"""
        try:
            if mode in self.current_images and self.current_images[mode] is not None:
                self.image_view.setImage(self.current_images[mode], autoLevels=True)
                self.update_roi()
        except Exception as e:
            self.logger.error(f"Error updating display: {e}")

    def on_frequency_changed(self, freq_text: str):
        """Adjust exposure times when frequency changes to ensure they don't exceed the period"""
        try:
            # Get frequency in Hz
            frequency = float(freq_text.split()[0])
            period_ms = int((1.0 / frequency) * 1000)  # Convert period to milliseconds
            
            # Add 10% margin for safety
            max_exposure = int(period_ms * 0.9)
            
            # Get current exposure times
            biolum_exp = int(self.biolum_exposure.text())
            fluo_exp = int(self.fluo_exposure.text())
            
            # Adjust if needed
            if biolum_exp > max_exposure:
                self.biolum_exposure.setText(str(max_exposure))
                self.logger.info(f"Adjusted bioluminescence exposure to {max_exposure}ms to fit {frequency}Hz")
                
            if fluo_exp > max_exposure:
                self.fluo_exposure.setText(str(max_exposure))
                self.logger.info(f"Adjusted fluorescence exposure to {max_exposure}ms to fit {frequency}Hz")
                
            # For 30 Hz, ensure exposures don't go below 1ms
            if frequency == 30:
                min_exposure = 1
                if fluo_exp < min_exposure:
                    self.fluo_exposure.setText(str(min_exposure))
                if biolum_exp < min_exposure:
                    self.biolum_exposure.setText(str(min_exposure))
                
        except Exception as e:
            self.logger.error(f"Error adjusting exposure times: {e}")

    def validate_exposure_time(self, exposure_input: QLineEdit):
        """Validate and adjust exposure time input"""
        try:
            # Get current frequency
            frequency = float(self.freq_combo.currentText().split()[0])
            period_ms = int((1.0 / frequency) * 1000)
            max_exposure = int(period_ms * 0.9)  # 90% of period
            
            # Get current value
            try:
                current_value = int(exposure_input.text())
            except ValueError:
                exposure_input.setText("0")
                return
                
            # Adjust if too large
            if current_value > max_exposure:
                exposure_input.setText(str(max_exposure))
                self.logger.info(f"Adjusted exposure time to {max_exposure}ms to fit {frequency}Hz")
                
        except Exception as e:
            self.logger.error(f"Error validating exposure time: {e}")

def main():
    app = QApplication(sys.argv)
    try:
        # Setup logging first
        logger = setup_logging()
        
        # Create main window with logger
        window = MainWindow(logger)
        window.show()
        
        logger.info("Application started")
        return app.exec_()
    except Exception as e:
        # If we have a logger, use it, otherwise print to stderr
        if 'logger' in locals():
            logger.error(f"Application failed to start: {e}")
        else:
            print(f"Application failed to start: {e}", file=sys.stderr)
            
        QMessageBox.critical(None, "Fatal Error",
                           f"Application failed to start: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
