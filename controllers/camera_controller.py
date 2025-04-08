from pylablib.devices import Andor
import logging

class CameraController:
    def __init__(self, logger, temperature=-60):
        self.logger = logger
        self.camera = None
        self.target_temperature = temperature
        self.initialize_camera()

    def initialize_camera(self):
        """Initialize and configure the Andor camera"""
        try:
            self.camera = Andor.AndorSDK2Camera(temperature=self.target_temperature, fan_mode="full")
            self.camera.set_temperature(self.target_temperature)
            self.camera.set_cooler(True)
            self.camera.set_trigger_mode("ext_exp")
            
            # Get and log available amplifier modes
            amp_modes = self.camera.get_all_amp_modes()
            self.logger.info(f"Available amplifier modes: {amp_modes}")
            self.logger.info("Camera initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing camera: {e}")
            self.camera = None

    def start_acquisition(self, em_gain, amp_gain, exposure_time):
        """Start camera acquisition with specified settings
        
        Args:
            em_gain: EM gain value
            amp_gain: Amplifier gain value
            exposure_time: Exposure time in seconds
        """
        try:
            self.logger.info(f"Set EM gain to {em_gain}")
            self.camera.set_EMCCD_gain(em_gain)
            
            self.logger.info(f"Set amplifier gain to {amp_gain}")
            self.camera.set_amp_mode(amp_gain)
            
            self.logger.info("Set trigger mode to external")
            self.camera.set_trigger_mode("ext_exp")
            
            self.logger.info(f"Set exposure time to {exposure_time:.3f}s")
            self.camera.set_exposure(exposure_time)
                        
            self.logger.info("Opened shutter")
            self.camera.setup_shutter("open")
            
            self.camera.start_acquisition()
            self.logger.info("Started camera acquisition")
            return True
        except Exception as e:
            self.logger.error(f"Error starting acquisition: {e}")
            return False

    def stop_acquisition(self):
        """Stop camera acquisition"""
        try:
            self.camera.stop_acquisition()
            self.camera.setup_shutter(mode="closed")
            self.logger.info("Camera stopped and shutter closed")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping acquisition: {e}")
            return False

    def get_temperature_status(self):
        """Get current temperature status"""
        try:
            return self.camera.get_temperature_status()
        except Exception as e:
            self.logger.error(f"Error getting temperature status: {e}")
            return "error"

    def get_temperature(self):
        """Get current temperature"""
        try:
            return self.camera.get_temperature()
        except Exception as e:
            self.logger.error(f"Error getting temperature: {e}")
            return None

    def close(self):
        """Clean up camera resources"""
        if self.camera is not None:
            try:
                self.camera.close()
                self.logger.info("Camera closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing camera: {e}") 