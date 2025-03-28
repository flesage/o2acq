from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pylablib.devices import Andor

class ImageAcquisitionService(QThread):
    """Service for handling image acquisition from the camera"""
    
    # Signals for communication with main thread
    image_acquired = pyqtSignal(str, object)  # (mode, image_data)
    acquisition_error = pyqtSignal(str)       # error message
    
    def __init__(self, camera: Andor.AndorSDK2Camera, logger: logging.Logger, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.logger = logger
        
        # Acquisition settings
        self.running = False
        self.active_modes: List[str] = []
        self.image_counter = 0
        self.frame_timeout = 1000  # Default 1 second timeout in ms
        
        # Data storage settings
        self.save_enabled = False
        self.saved_images: Dict[str, List[np.ndarray]] = {}
        
        # Performance monitoring
        self.last_frame_times: Dict[str, datetime] = {}
        self.frame_intervals: Dict[str, List[float]] = {}

    def set_active_modes(self, modes: List[str]) -> None:
        """Set the active acquisition modes
        
        Args:
            modes: List of mode names (e.g., ['Bioluminescence', 'Blue', 'Green'])
        """
        self.active_modes = modes
        self.saved_images = {mode: [] for mode in modes}
        self.logger.info(f"Active modes set to: {', '.join(modes)}")

    def set_save_enabled(self, enabled: bool) -> None:
        """Enable or disable saving of acquired images
        
        Args:
            enabled: True to enable saving, False to disable
        """
        self.save_enabled = enabled
        self.logger.info(f"Save enabled: {enabled}")

    def set_frame_timeout(self, frequency: float):
        """Set frame timeout based on acquisition frequency"""
        # Calculate period in milliseconds and add 50% margin
        period_ms = (1.0 / frequency) * 1000
        self.frame_timeout = int(period_ms * 1.5)
        self.logger.debug(f"Frame timeout set to {self.frame_timeout}ms for {frequency}Hz acquisition")

    def run(self) -> None:
        """Main acquisition loop"""
        self.running = True
        self.image_counter = 0
        self.frame_intervals = {mode: [] for mode in self.active_modes}
        self.last_frame_times = {mode: datetime.now() for mode in self.active_modes}
        
        self.logger.info("Starting acquisition loop")
        
        while self.running:
            try:
                # Wait for frame with calculated timeout
                if not self.camera.wait_for_frame(timeout=self.frame_timeout):
                    self.logger.warning(f"Timeout waiting for frame after {self.frame_timeout}ms")
                    continue
                
                # Read image data
                (image_data, image_info) = self.camera.read_newest_image(return_info=True)
                print(image_info)
                if image_data is None:
                    continue
                
                # Calculate current mode based on counter
                current_mode = self.active_modes[self.image_counter % len(self.active_modes)]
                
                # Calculate frame interval for this mode
                current_time = datetime.now()
                if current_mode in self.last_frame_times:
                    interval = (current_time - self.last_frame_times[current_mode]).total_seconds()
                    # Only store intervals for the same mode
                    self.frame_intervals[current_mode].append(interval)
                    # Keep only last 10 intervals per mode
                    if len(self.frame_intervals[current_mode]) > 10:
                        self.frame_intervals[current_mode] = self.frame_intervals[current_mode][-10:]
                
                self.last_frame_times[current_mode] = current_time
                
                # Emit the image for display
                self.image_acquired.emit(current_mode, image_data)
                
                # Store for saving if enabled
                if self.save_enabled:
                    self.saved_images[current_mode].append(image_data.copy())
                
                self.image_counter += 1
                
                # Log frame rate periodically
                if self.image_counter % (len(self.active_modes) * 10) == 0:  # Every 10 cycles
                    self._log_frame_rates()
                
            except Exception as e:
                error_msg = f"Error in acquisition loop: {str(e)}"
                self.logger.error(error_msg)
                self.acquisition_error.emit(error_msg)
                self.msleep(100)  # Add delay on error
                continue

    def _log_frame_rates(self):
        """Log the frame rates for each mode"""
        for mode in self.active_modes:
            if self.frame_intervals[mode]:
                avg_interval = np.mean(self.frame_intervals[mode])
                rate = 1.0 / avg_interval if avg_interval > 0 else 0
                self.logger.debug(f"{mode} frame rate: {rate:.2f} Hz")

    def stop(self) -> None:
        """Stop the acquisition loop"""
        self.logger.info("Stopping acquisition loop")
        self.running = False
        self.wait()  # Wait for thread to finish
        
        # Log acquisition statistics
        total_frames = self.image_counter
        stats = self.get_statistics()
        
        self.logger.info(
            f"Acquisition stopped:\n"
            f"  Total frames: {total_frames}\n"
            f"  Frames per mode: {', '.join(f'{mode}: {len(frames)}' for mode, frames in self.saved_images.items())}"
        )

    def get_statistics(self) -> dict:
        """Get current acquisition statistics"""
        stats = {
            'total_frames': self.image_counter,
            'frames_per_mode': {mode: len(frames) for mode, frames in self.saved_images.items()},
            'frame_rates': {}
        }
        
        # Calculate frame rate for each mode
        for mode in self.active_modes:
            if self.frame_intervals[mode]:
                avg_interval = np.mean(self.frame_intervals[mode])
                stats['frame_rates'][mode] = 1.0 / avg_interval if avg_interval > 0 else 0
            else:
                stats['frame_rates'][mode] = 0
                
        return stats

    def clear_saved_images(self) -> None:
        """Clear all saved images from memory"""
        self.saved_images = {mode: [] for mode in self.active_modes}
        self.logger.info("Cleared saved images from memory") 