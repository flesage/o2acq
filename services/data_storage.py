import os
from datetime import datetime
import tifffile
import numpy as np
import logging

class DataStorageService:
    def __init__(self, logger):
        self.logger = logger
        self.save_path = None

    def set_save_path(self, path):
        """Set the directory path for saving data"""
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception as e:
                self.logger.error(f"Error creating directory: {e}")
                return False
                
        self.save_path = path
        self.logger.info(f"Save path set to: {path}")
        return True

    def save_image_stacks(self, saved_images, frame_indices):
        """Save accumulated images as TIFF stacks and frame indices as NPY files
        
        Args:
            saved_images: Dictionary of image lists per mode
            frame_indices: Dictionary of frame index lists per mode
        """
        if not self.save_path:
            self.logger.error("No save path set")
            return False

        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for mode in saved_images:
                if saved_images[mode]:
                    # Save image stack
                    image_stack = np.stack(saved_images[mode])
                    tiff_path = os.path.join(self.save_path, f"{mode}_{timestamp}.tiff")
                    tifffile.imwrite(tiff_path, image_stack)
                    
                    # Save frame indices
                    if mode in frame_indices and frame_indices[mode]:
                        indices_array = np.array(frame_indices[mode])
                        npy_path = os.path.join(self.save_path, f"{mode}_{timestamp}_frames.npy")
                        np.save(npy_path, indices_array)
                        
                    self.logger.info(f"Saved {len(saved_images[mode])} {mode} images to {tiff_path}")
                    self.logger.info(f"Saved frame indices to {npy_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
            return False

    def save_metadata(self, metadata, filename):
        """Save acquisition metadata"""
        if not self.save_path:
            self.logger.error("No save path set")
            return False
            
        try:
            filepath = os.path.join(self.save_path, filename)
            with open(filepath, 'w') as f:
                for key, value in metadata.items():
                    f.write(f"{key}: {value}\n")
            self.logger.info(f"Saved metadata to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving metadata: {e}")
            return False 