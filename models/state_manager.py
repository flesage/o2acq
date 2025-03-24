from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

class AcquisitionState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"

@dataclass
class SystemState:
    acquisition_state: AcquisitionState = AcquisitionState.IDLE
    temperature_stabilized: bool = False
    active_modes: List[str] = None
    save_enabled: bool = False
    save_path: Optional[str] = None
    current_frequency: float = 1.0
    em_gain: int = 0
    amp_gain: int = 1
    biolum_exposure: int = 700  # ms
    fluo_exposure: int = 10     # ms
    timestamp: datetime = None

    def __post_init__(self):
        if self.active_modes is None:
            self.active_modes = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

class StateManager:
    def __init__(self):
        self.state = SystemState()
        self._observers = []

    def add_observer(self, observer):
        """Add an observer to be notified of state changes"""
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer):
        """Remove an observer"""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify_observers(self):
        """Notify all observers of state change"""
        for observer in self._observers:
            observer.update_ui_state(self.state)

    def update_state(self, **kwargs):
        """Update state with given parameters and notify observers"""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
            else:
                raise ValueError(f"Invalid state parameter: {key}")
        
        # Update timestamp
        self.state.timestamp = datetime.now()
        
        # Notify observers of state change
        self.notify_observers()

    def get_metadata(self):
        """Get current state as metadata dictionary"""
        return {
            'timestamp': self.state.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'acquisition_state': self.state.acquisition_state.value,
            'active_modes': ', '.join(self.state.active_modes),
            'frequency': f"{self.state.current_frequency}Hz",
            'em_gain': self.state.em_gain,
            'amp_gain': self.state.amp_gain,
            'biolum_exposure': f"{self.state.biolum_exposure}ms",
            'fluo_exposure': f"{self.state.fluo_exposure}ms"
        }