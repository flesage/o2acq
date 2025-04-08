import nidaqmx
from nidaqmx.constants import AcquisitionType
import numpy as np
import logging
from typing import List, Optional

class NIDAQController:
    """Controller for National Instruments DAQ device"""
    
    def __init__(self, logger: logging.Logger, device: str = "IOIFAST"):
        self.logger = logger
        self.device = device
        self.task: Optional[nidaqmx.Task] = None
        self.running = False
        self.current_pattern = None
        
    def start_task(self, frequency: float, modes: List[bool], biolum_exp: int, fluo_exp: int) -> bool:
        """Start NI-DAQ task with given parameters
        
        Args:
            frequency (float): Frequency in Hz per mode
            modes (list): List of booleans [biolum, blue, green]
            biolum_exp (int): Bioluminescence exposure time in ms
            fluo_exp (int): Fluorescence exposure time in ms
            
        Returns:
            bool: True if task started successfully, False otherwise
        """
        if self.running:
            self.logger.warning("Task already running. Stopping previous task.")
            self.stop_task()
            
        # Calculate total period based on number of active modes
        num_active_modes = sum(modes[:3])  # Count only biolum, blue, green
        # Only divide frequency if we have more than one mode
        mode_frequency = frequency if num_active_modes <= 1 else frequency / num_active_modes
        period = 1.0 / mode_frequency
        samples_per_period = int(1000 * period)  # 1000 Hz * period

        try:
            self.task = nidaqmx.Task()
            
            # Configure digital output channel (8-bit port)
            self.task.do_channels.add_do_chan(f"{self.device}/port0")
            
            # Create output pattern
            self.current_pattern = self._generate_pattern(
                modes, samples_per_period, biolum_exp, fluo_exp
            )

            # Configure timing
            self.task.timing.cfg_samp_clk_timing(
                rate=1000,  # 1kHz sampling rate
                sample_mode=AcquisitionType.CONTINUOUS,
                samps_per_chan=len(self.current_pattern)
            )

            # Write the pattern (will be repeated automatically due to continuous mode)
            self.task.write(self.current_pattern, auto_start=True)
            self.running = True
            
            actual_freq = mode_frequency if num_active_modes <= 1 else f"{mode_frequency:.2f} per mode"
            self.logger.info(f"Started DAQ task at {frequency}Hz (actual: {actual_freq}Hz)")
            self._log_pattern_info(modes, frequency, biolum_exp, fluo_exp)
            return True
            
        except nidaqmx.errors.Error as e:
            self.logger.error(f"Error starting DAQ task: {e}")
            self.stop_task()
            return False

    def _generate_pattern(self, modes: List[bool], samples_per_period: int, 
                         biolum_exp: int, fluo_exp: int) -> List[int]:
        """Generate the digital output pattern
        
        Args:
            modes: List of booleans [biolum, blue, green]
            samples_per_period: Number of samples per period
            biolum_exp: Bioluminescence exposure time in ms
            fluo_exp: Fluorescence exposure time in ms
            
        Returns:
            List of integers representing the digital output pattern
        """
        if not any(modes[:3]):  # Check first 3 modes
            return [0] * samples_per_period
            
        pattern = [0] * samples_per_period
        active_modes = [i for i, mode in enumerate(modes[:3]) if mode]
        
        # Calculate spacing between modes
        mode_spacing = samples_per_period // max(len(active_modes), 1)
        
        # Process each active mode
        for idx, mode_index in enumerate(active_modes):
            start_pos = idx * mode_spacing
            
            # Set mode-specific parameters
            if mode_index == 0:  # Bioluminescence
                exp_samples = biolum_exp
                bit_value = 0  # No illumination line needed
            else:  # Blue (1) or Green (2)
                exp_samples = fluo_exp
                bit_value = 1 << (mode_index + 1)  # Line 1 for blue, line 2 for green
            
            # Add mode-specific pattern
            for i in range(exp_samples):
                if (start_pos + i) < samples_per_period:
                    pattern[start_pos + i] |= (bit_value | (1 << 4))  # Mode bit and exposure trigger on line 4
            
            # For blue/green, keep illumination on for the fluorescence exposure time
            if mode_index > 0:  # Blue or Green
                for i in range(exp_samples):
                    if (start_pos + i) < samples_per_period:
                        pattern[start_pos + i] |= bit_value
        
        return pattern

    def stop_task(self) -> bool:
        """Stop and cleanup the NI-DAQ task
        
        Returns:
            bool: True if task stopped successfully, False otherwise
        """
        if self.task is not None:
            try:
                self.logger.info("Stopping DAQ task...")
                # Set all lines to low
                self.task.write([0])
                self.task.stop()
                self.task.close()
                self.logger.info("DAQ task stopped and cleaned up")
                return True
            except nidaqmx.errors.Error as e:
                self.logger.error(f"Error stopping task: {e}")
                return False
            finally:
                self.task = None
                self.running = False
                self.current_pattern = None
        return True

    def _log_pattern_info(self, modes: List[bool], frequency: float, 
                         biolum_exp: int, fluo_exp: int) -> None:
        """Log information about the current pattern configuration"""
        mode_names = ['Bioluminescence', 'Blue', 'Green']
        active_modes = [name for name, active in zip(mode_names, modes) if active]
        
        self.logger.debug(
            f"Pattern configuration:\n"
            f"  Frequency: {frequency}Hz\n"
            f"  Active modes: {', '.join(active_modes)}\n"
            f"  Biolum exposure: {biolum_exp}ms\n"
            f"  Fluo exposure: {fluo_exp}ms\n"
            f"  Pattern length: {len(self.current_pattern) if self.current_pattern else 0}"
        )

    def get_status(self) -> dict:
        """Get current status of the DAQ controller
        
        Returns:
            dict: Status information including running state and active configuration
        """
        return {
            'running': self.running,
            'has_task': self.task is not None,
            'pattern_length': len(self.current_pattern) if self.current_pattern else 0
        }

    def __del__(self):
        """Cleanup when object is deleted"""
        self.stop_task() 