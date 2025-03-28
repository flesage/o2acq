O2 Acquisition Interface

This application provides a graphical interface for controlling an Andor iXon camera with synchronized illumination control via NI-DAQ digital outputs.

Requirements
-----------

Hardware:
- Andor iXon camera (SDK2 compatible)
- National Instruments DAQ device (tested with USB-6XXX series)
- Windows PC (required for Andor SDK2)

Software:
- Python 3.7 or higher
- Andor SDK2 (must be installed separately)
- NI-DAQmx drivers (must be installed separately)

Installation
-----------

1. Install the Andor SDK2 and NI-DAQmx drivers if not already installed

2. Create and activate a Python virtual environment (recommended):
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install the required Python packages:
   pip install -r requirements.txt

Usage
-----

1. Launch the application:
   python o2acq.py

2. Interface Controls:

   Camera Settings:
   - Temperature: Current camera temperature and stabilization status
   - Temperature Override: Option to start acquisition without temperature stabilization
   - EM Gain: Set electron multiplication gain (0-300)
   - Amp Gain: Set amplifier gain (1-3)
   - Exposure times:
     * Bioluminescence: Default 700ms
     * Fluorescence: Default 10ms

   Acquisition Settings:
   - Frequency: Select acquisition frequency (0.5-30 Hz)
   - Mode Selection:
     * Bioluminescence
     * Blue
     * Green
   - At least one mode must be selected to start acquisition
   - Exposure times are automatically adjusted based on selected frequency

   Display Settings:
   - Display Mode: Switch between active acquisition modes
   - ROI: Select region of interest for intensity plotting
   - Real-time intensity plot for selected mode

   Save Settings:
   - Enable/disable saving
   - Select save directory
   - Images are saved as TIFF stacks, one per illumination mode
   - Filename format: {mode}_{YYYYMMDD_HHMMSS}.tiff

Operation
--------

1. Configure camera settings as needed
2. Select desired illumination modes (at least one required)
3. Enable saving if desired and select save directory
4. Wait for temperature stabilization (or use override if needed)
5. Click Start to begin acquisition
6. Use the Display Mode dropdown to view different channels
7. Click Stop to end acquisition and save data (if enabled)

Logging
-------

The application creates detailed log files:
- Format: o2acq_{YYYYMMDD_HHMMSS}.log
- Contains all operations and error messages
- Located in the same directory as the application

Digital Output Configuration
--------------------------

The NI-DAQ digital outputs are configured as follows:
- Port 0: 8-bit digital output port
- Bit 0: Bioluminescence mode (no illumination line needed)
- Bit 1: Blue illumination trigger
- Bit 2: Green illumination trigger
- Bit 4: Camera exposure trigger (always active during acquisition)

The pattern is generated based on the selected modes and exposure times:
- For bioluminescence: Only bit 4 (exposure trigger) is active
- For blue/green: Both the mode-specific bit (1 or 2) and bit 4 (exposure trigger) are active
- The pattern repeats at the selected acquisition frequency
- Exposure times are automatically adjusted to fit within the acquisition period

Troubleshooting
--------------

1. Temperature Issues:
   - Wait for temperature stabilization
   - Use temperature override if needed
   - Check camera cooling system

2. Acquisition Issues:
   - Ensure at least one mode is selected
   - Check exposure times don't exceed period (automatically adjusted)
   - Verify camera and DAQ connections

3. Saving Issues:
   - Ensure save directory is selected
   - Check disk space
   - Verify write permissions

Recent Changes
-------------

1. Image Acquisition:
   - Improved mode validation before starting acquisition
   - Added separate ROI tracking for each mode
   - Enhanced frame rate monitoring per mode
   - Added temperature override option

2. Display:
   - Added mode-specific display selection
   - Improved ROI intensity plotting per mode
   - Enhanced image display updates

3. Performance:
   - Optimized frame timeout based on acquisition frequency
   - Added frame rate monitoring and logging
   - Improved error handling and recovery

For additional issues, check the log file for detailed error messages. 