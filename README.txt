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
   - Camera ROI: Select region of interest on the camera
   - Shutter: Open/close camera shutter
   - Frequency: Select acquisition frequency (0.5-5 Hz)
   - EM Gain: Set electron multiplication gain (0-500)
   - Amp Gain: Set amplifier gain (1-3)
   - Exposure times:
     * Bioluminescence: Default 700ms
     * Fluorescence: Default 10ms

   Illumination:
   - Bioluminescence
   - Blue
   - Green
   - Select which modes to use during acquisition

   View Settings:
   - Dataplot ROI: Select region for plotting
   - Image Source: Switch between active illumination modes

   Save Settings:
   - Enable/disable saving
   - Select save directory
   - Images are saved as TIFF stacks, one per illumination mode
   - Filename format: {mode}_{YYYYMMDD_HHMMSS}.tiff

Operation
--------

1. Configure camera settings as needed
2. Select desired illumination modes
3. Enable saving if desired and select save directory
4. Click Start to begin acquisition
5. Use the Image Source dropdown to view different channels
6. Click Stop to end acquisition and save data (if enabled)

Logging
-------

The application creates detailed log files:
- Format: o2acq_{YYYYMMDD_HHMMSS}.log
- Contains all operations and error messages
- Located in the same directory as the application

Digital Output Configuration
--------------------------

The NI-DAQ digital outputs are configured as follows:
- Port 0, Line 0: Camera exposure trigger
- Port 0, Line 1: Bioluminescence trigger
- Port 0, Line 2: Blue illumination trigger
- Port 0, Line 3: Green illumination trigger

Troubleshooting
--------------

1. Camera not found:
   - Ensure Andor SDK2 is properly installed
   - Check USB connection
   - Verify camera power

2. DAQ errors:
   - Check NI-DAQmx installation
   - Verify device name (default: "Dev1")
   - Check device connections

3. Saving errors:
   - Verify write permissions in save directory
   - Ensure sufficient disk space

For additional issues, check the log file for detailed error messages. 