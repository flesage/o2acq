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

    def save_image_stacks(self, saved_images):
        """Save accumulated images as TIFF stacks"""
        if not self.save_path:
            self.logger.error("No save path set")
            return False

        if not saved_images:
            self.logger.error("No images provided to save")
            return False

        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for mode, images in saved_images.items():
                # Add more detailed logging
                self.logger.debug(f"Processing {mode}: {len(images) if images else 0} images")
                
                if not images or len(images) == 0:
                    self.logger.warning(f"No images to save for {mode}")
                    continue
                
                try:
                    image_stack = np.stack(images)
                    filename = f"{mode}_{timestamp}.tiff"
                    tiff_path = os.path.join(self.save_path, filename)
                    
                    # Log stack details
                    self.logger.debug(f"Image stack shape: {image_stack.shape}, dtype: {image_stack.dtype}")
                    
                    tifffile.imwrite(tiff_path, image_stack)
                    self.logger.info(f"Saved {len(images)} {mode} images to {tiff_path}")
                except Exception as e:
                    self.logger.error(f"Error saving {mode} images: {e}")
                    continue
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving image stacks: {e}")
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