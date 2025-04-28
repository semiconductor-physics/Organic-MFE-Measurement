import logging
from log import setup_logger
setup_logger(debug_level=logging.INFO)
import sys
import os
import pandas as pd
from omc_processing import process_measurement, process_measurement_cryo
import yaml
from tkinter import StringVar, TOP, BooleanVar
from tkinterdnd2 import TkinterDnD, DND_ALL
import customtkinter as ctk
from threading import Thread
from multiprocessing import Pool
from functools import partial

class Tk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

class ProcessingGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = Tk()
        self.root.geometry("350x200")
        self.root.title("Process Data")
        
        self.progress_bar = None
        self.progress_label = None
        
        # Load config at startup
        with open('process_config.yaml', mode='r') as f:
            self.config = yaml.safe_load(f)
        
        self.setup_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # Register the main window for drag and drop
        self.root.drop_target_register(DND_ALL)
        self.root.dnd_bind("<<Drop>>", self._on_drop)
    
    def setup_gui(self):
        mode_frame = ctk.CTkFrame(self.root)
        mode_frame.pack(side=TOP, pady=5)
        self.is_cryo = BooleanVar(value=self.config.get('processing_mode', 'cryo') == 'cryo')
        ctk.CTkLabel(mode_frame, text="Processing Mode:").pack(side="left", padx=5)
        ctk.CTkRadioButton(mode_frame, text="Standard", variable=self.is_cryo, value=False,
                          command=self.save_mode).pack(side="left", padx=5)
        ctk.CTkRadioButton(mode_frame, text="Cryo", variable=self.is_cryo, value=True,
                          command=self.save_mode).pack(side="left", padx=5)
        
        # Add instruction label
        pathLabel = ctk.CTkLabel(self.root, text="Drag and drop folder anywhere in this window")
        pathLabel.pack(side=TOP)
        
        # Add progress frame
        progress_frame = ctk.CTkFrame(self.root)
        progress_frame.pack(side=TOP, fill="x", padx=10, pady=5)
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=5, pady=5)
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(progress_frame, text="")
        self.progress_label.pack(pady=2)
        
        settings_button = ctk.CTkButton(self.root, text="Settings", command=self.open_settings)
        settings_button.pack(side=TOP, pady=10)
    
    def save_mode(self):
        self.config['processing_mode'] = 'cryo' if self.is_cryo.get() else 'standard'
        with open('process_config.yaml', 'w') as f:
            yaml.dump(self.config, f)
    
    def on_closing(self):
        self.save_mode()
        self.root.destroy()

    def _on_drop(self, event):
        with open('process_config.yaml', mode='r') as f:
            self.config = yaml.safe_load(f)
        Thread(target=self.process_measurement_wrapper, args=(event, self.config)).start()
    
    def process_measurement_wrapper(self, event, config):
        path: str = event.data
        path = path.strip('{}')
        measurement_dirs = [f'{path}\\{subdir}' for subdir in os.listdir(path) if os.path.isdir(f'{path}/{subdir}')]
        total = len(measurement_dirs)
        
        def update_progress(completed):
            progress = completed / total
            self.progress_bar.set(progress)
            self.progress_label.configure(text=f"Processing: {completed}/{total} measurements")
            self.root.update()
        
        process_func = process_measurement_cryo if self.is_cryo.get() else process_measurement
        completed = 0
        
        update_progress(0)
        with Pool() as pool:
            for _ in pool.imap_unordered(partial(process_func, config=config), measurement_dirs):
                completed += 1
                self.root.after(0, update_progress, completed)
        
        self.progress_bar.set(1)
        self.progress_label.configure(text="Processing complete!")
        print("Done")
    
    def open_settings(self):
        with open('process_config.yaml', mode='r') as f:
            config = yaml.safe_load(f)
        settings_dialog = SettingsDialog(self.root, config)
        settings_dialog.grab_set()
    
    def run(self):
        self.root.mainloop()

class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.title("Settings")
        self.geometry("900x860")
        
        # Filter settings
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.pack(fill="x", padx=10, pady=(10, 20))  # Increased padding
        ctk.CTkLabel(self.filter_frame, text="Filter Settings", font=("Helvetica", 12, "bold")).pack(pady=5)
        
        oled_frame = ctk.CTkFrame(self.filter_frame)
        oled_frame.pack(side="left", expand=True, fill="x", padx=5)
        photo_frame = ctk.CTkFrame(self.filter_frame)
        photo_frame.pack(side="right", expand=True, fill="x", padx=5)
        
        # OLED settings
        ctk.CTkLabel(oled_frame, text="OLED Settings").pack()
        oled_settings_frame = ctk.CTkFrame(oled_frame)
        oled_settings_frame.pack(fill="x", padx=2)
        
        ctk.CTkLabel(oled_settings_frame, text="Order:").pack(side="left", padx=2)
        self.oled_n = ctk.CTkEntry(oled_settings_frame, width=80)
        self.oled_n.pack(side="left", padx=2)
        self.oled_n.insert(0, str(config['ramp']['oled']['filter']['N']))
        
        ctk.CTkLabel(oled_settings_frame, text="Cutoff:").pack(side="left", padx=2)
        self.oled_wn = ctk.CTkEntry(oled_settings_frame, width=80)
        self.oled_wn.pack(side="left", padx=2)
        self.oled_wn.insert(0, str(config['ramp']['oled']['filter']['Wn'][0]))
        
        # Photo settings
        ctk.CTkLabel(photo_frame, text="Photo Settings").pack()
        photo_settings_frame = ctk.CTkFrame(photo_frame)
        photo_settings_frame.pack(fill="x", padx=2)
        
        ctk.CTkLabel(photo_settings_frame, text="Order:").pack(side="left", padx=2)
        self.photo_n = ctk.CTkEntry(photo_settings_frame, width=80)
        self.photo_n.pack(side="left", padx=2)
        self.photo_n.insert(0, str(config['ramp']['photo']['filter']['N']))
        
        ctk.CTkLabel(photo_settings_frame, text="Cutoff:").pack(side="left", padx=2)
        self.photo_wn = ctk.CTkEntry(photo_settings_frame, width=80)
        self.photo_wn.pack(side="left", padx=2)
        self.photo_wn.insert(0, str(config['ramp']['photo']['filter']['Wn'][0]))

        # Effects selection
        self.effects_frame = ctk.CTkFrame(self)
        self.effects_frame.pack(fill="x", padx=10, pady=(0, 20))  # Increased bottom padding
        ctk.CTkLabel(self.effects_frame, text="Effects to Fit", font=("Helvetica", 12, "bold")).pack(pady=5)
        
        effects_checkbox_frame = ctk.CTkFrame(self.effects_frame)
        effects_checkbox_frame.pack(fill="x", padx=5, pady=5)
        
        self.effects = ['omc', 'mel', 'mageff']
        self.effect_vars = {}
        for effect in self.effects:
            var = BooleanVar(value=effect in config['ramp']['fitting']['effects_to_fit'])
            self.effect_vars[effect] = var
            ctk.CTkCheckBox(effects_checkbox_frame, text=effect, variable=var).pack(side="left", padx=10)

        # Models selection
        self.models_frame = ctk.CTkFrame(self)
        self.models_frame.pack(fill="x", padx=10, pady=(0, 20))  # Increased bottom padding
        
        cole_models = ['cole', 'double_cole']
        lorentzian_models = ['lorentzian', 'non_lorentzian', 
                            'double_lorentzian', 'double_non_lorentzian', 
                            'lorentzian_non_lorentzian']
        
        self.model_vars = {}
        self.fit_scores = ['aic', 'bic', 'r2', 'rmse', 'mae', 'cp', 'adjusted_r2']
        self.score_vars = {}
        
        for effect in self.effects:
            effect_frame = ctk.CTkFrame(self.models_frame)
            effect_frame.pack(fill="x", padx=5, pady=(15, 15))  # Increased spacing between effects
            ctk.CTkLabel(effect_frame, text=f"{effect} models", font=("Helvetica", 12, "bold")).pack(pady=5)
            
            self.model_vars[effect] = {
                'group1': {},
                'group2': {}
            }
            
            # Cole models frame
            cole_frame = ctk.CTkFrame(effect_frame)
            cole_frame.pack(fill="x", padx=5, pady=(5, 10))  # Added spacing between model groups
            ctk.CTkLabel(cole_frame, text="Cole models:").pack(side="left", padx=5)
            
            for model in cole_models:
                var = BooleanVar(value=model in (config['ramp']['fitting'][effect]['models'][0] 
                                               if len(config['ramp']['fitting'][effect]['models']) > 0 else []))
                self.model_vars[effect]['group1'][model] = var
                ctk.CTkCheckBox(cole_frame, text=model, variable=var).pack(side="left", padx=5)
            
            lorentzian_frame = ctk.CTkFrame(effect_frame)
            lorentzian_frame.pack(fill="x", padx=5, pady=(0, 10))  # Added spacing before fit score
            ctk.CTkLabel(lorentzian_frame, text="Lorentzian models:").pack(side="left", padx=5)
            
            for model in lorentzian_models:
                var = BooleanVar(value=model in (config['ramp']['fitting'][effect]['models'][1] 
                                               if len(config['ramp']['fitting'][effect]['models']) > 1 else []))
                self.model_vars[effect]['group2'][model] = var
                ctk.CTkCheckBox(lorentzian_frame, text=model, variable=var).pack(side="left", padx=5)

            # Fit score selection
            score_frame = ctk.CTkFrame(effect_frame)
            score_frame.pack(fill="x", padx=5, pady=(0, 5))
            ctk.CTkLabel(score_frame, text="Fit score:").pack(side="left", padx=5)
            self.score_vars[effect] = ctk.CTkOptionMenu(score_frame, 
                                                       values=self.fit_scores,
                                                       variable=StringVar(value=config['ramp']['fitting'][effect]['fit_score']))
            self.score_vars[effect].pack(side="left", padx=2)

        # Save button
        self.save_button = ctk.CTkButton(self, text="Save", command=self.save_settings)
        self.save_button.pack(pady=20)  # Increased padding

    def save_settings(self):
        # Update filter settings
        self.config['ramp']['oled']['filter']['N'] = int(self.oled_n.get())
        self.config['ramp']['oled']['filter']['Wn'] = [float(self.oled_wn.get())]
        self.config['ramp']['photo']['filter']['N'] = int(self.photo_n.get())
        self.config['ramp']['photo']['filter']['Wn'] = [float(self.photo_wn.get())]

        # Update effects to fit
        self.config['ramp']['fitting']['effects_to_fit'] = [
            effect for effect, var in self.effect_vars.items() if var.get()
        ]

        # Update models
        for effect in self.effects:
            self.config['ramp']['fitting'][effect]['models'] = [
                [model for model, var in self.model_vars[effect]['group1'].items() if var.get()],
                [model for model, var in self.model_vars[effect]['group2'].items() if var.get()]
            ]
            self.config['ramp']['fitting'][effect]['fit_score'] = self.score_vars[effect].get()

        # Save to file
        with open('process_config.yaml', 'w') as f:
            yaml.dump(self.config, f)
        
        self.destroy()

if __name__ == '__main__':
    app = ProcessingGUI()
    app.run()
