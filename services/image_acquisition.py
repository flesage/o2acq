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
        
        # Data storage settings
        self.save_enabled = False
        self.save_path: Optional[str] = None
        self.saved_images: Dict[str, List[np.ndarray]] = {}
        
        # Performance monitoring
        self.last_frame_time = None
        self.frame_times: List[float] = []

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

    def set_save_path(self, path: str) -> None:
        """Set the path for saving acquired images
        
        Args:
            path: Directory path for saving images
        """
        self.save_path = path
        self.logger.info(f"Save path set to: {path}")

    def run(self) -> None:
        """Main acquisition loop"""
        self.running = True
        self.image_counter = 0
        self.frame_times = []
        self.last_frame_time = datetime.now()
        
        self.logger.info("Starting acquisition loop")
        
        while self.running:
            try:
                # Check if we have active modes
                if not self.active_modes:
                    self.msleep(100)  # Avoid busy waiting
                    continue
                
                # Wait for frame with timeout
                if not self.camera.wait_for_frame(timeout=1000):  # 1 second timeout
                    continue
                
                # Read image data
                image_data = self.camera.read_newest_image()
                if image_data is None:
                    continue
                
                # Calculate current mode based on counter
                current_mode = self.active_modes[self.image_counter % len(self.active_modes)]
                
                # Calculate frame rate
                current_time = datetime.now()
                frame_time = (current_time - self.last_frame_time).total_seconds()
                self.frame_times.append(frame_time)
                self.last_frame_time = current_time
                
                # Keep only last 100 frame times for rate calculation
                if len(self.frame_times) > 100:
                    self.frame_times = self.frame_times[-100:]
                
                # Emit the image for display
                self.image_acquired.emit(current_mode, image_data)
                
                # Store for saving if enabled
                if self.save_enabled:
                    self.saved_images[current_mode].append(image_data.copy())
                
                self.image_counter += 1
                
                # Log frame rate periodically
                if self.image_counter % 100 == 0:
                    avg_rate = 1.0 / np.mean(self.frame_times) if self.frame_times else 0
                    self.logger.debug(f"Average frame rate: {avg_rate:.2f} fps")
                
            except Exception as e:
                error_msg = f"Error in acquisition loop: {str(e)}"
                self.logger.error(error_msg)
                self.acquisition_error.emit(error_msg)
                self.msleep(100)  # Add delay on error
                continue
            
            # Small sleep to prevent CPU overload
            self.msleep(1)

    def stop(self) -> None:
        """Stop the acquisition loop"""
        self.logger.info("Stopping acquisition loop")
        self.running = False
        self.wait()  # Wait for thread to finish
        
        # Log acquisition statistics
        total_frames = self.image_counter
        avg_rate = 1.0 / np.mean(self.frame_times) if self.frame_times else 0
        
        self.logger.info(
            f"Acquisition stopped:\n"
            f"  Total frames: {total_frames}\n"
            f"  Average frame rate: {avg_rate:.2f} fps\n"
            f"  Frames per mode: {', '.join(f'{mode}: {len(frames)}' for mode, frames in self.saved_images.items())}"
        )

    def get_statistics(self) -> dict:
        """Get current acquisition statistics
        
        Returns:
            dict: Statistics including frame count, rate, and mode counts
        """
        return {
            'total_frames': self.image_counter,
            'current_frame_rate': 1.0 / np.mean(self.frame_times[-10:]) if self.frame_times else 0,
            'average_frame_rate': 1.0 / np.mean(self.frame_times) if self.frame_times else 0,
            'frames_per_mode': {mode: len(frames) for mode, frames in self.saved_images.items()}
        }

    def clear_saved_images(self) -> None:
        """Clear all saved images from memory"""
        self.saved_images = {mode: [] for mode in self.active_modes}
        self.logger.info("Cleared saved images from memory") 