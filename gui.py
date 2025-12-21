"""
CAD Analyzer GUI - CustomTkinter interface
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from pathlib import Path
import csv
import json
from analyzer import CADAnalyzer, AnalysisResult
from typing import List

# Drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    print("Note: tkinterdnd2 not installed. Drag-and-drop disabled.")


class CADAnalyzerApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        if DND_AVAILABLE:
            self.root = TkinterDnD.Tk()
        else:
            self.root = ctk.CTk()
        
        self.root.title("CAD Analyzer")
        self.root.geometry("950x720")
        self.root.minsize(900, 680)
        
        self.files: List[str] = []
        self.results: List[AnalysisResult] = []
        self.is_imperial = ctk.BooleanVar(value=False)
        self.selected_material = ctk.StringVar(value="PLA")
        self.infill_percent = ctk.IntVar(value=20)
        self.layer_height = ctk.DoubleVar(value=0.2)
        self.print_speed = ctk.IntVar(value=50)
        self.wall_count = ctk.IntVar(value=3)
        
        self._create_ui()
        
    def _create_ui(self):
        """Create main UI layout"""
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        title_label = ctk.CTkLabel(
            self.main_frame, 
            text="CAD ANALYZER",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        subtitle = ctk.CTkLabel(
            self.main_frame,
            text="Analyze STL files - Get dimensions, volume, and mass estimates",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle.pack(pady=(0, 15))
        
        self._create_settings_frame()
        self._create_drop_zone()
        self._create_file_list()
        
        self.analyze_btn = ctk.CTkButton(
            self.main_frame,
            text="ANALYZE",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            command=self._analyze_files
        )
        self.analyze_btn.pack(fill="x", padx=20, pady=10)
        
        self._create_export_buttons()
        self._create_results_table()
        
    def _create_settings_frame(self):
        """Create settings panel"""
        settings_frame = ctk.CTkFrame(self.main_frame)
        settings_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        units_label = ctk.CTkLabel(settings_frame, text="Units:", font=ctk.CTkFont(weight="bold"))
        units_label.pack(side="left", padx=(15, 10))
        
        metric_radio = ctk.CTkRadioButton(
            settings_frame, 
            text="Metric (mm)", 
            variable=self.is_imperial, 
            value=False,
            command=self._refresh_results
        )
        metric_radio.pack(side="left", padx=5)
        
        imperial_radio = ctk.CTkRadioButton(
            settings_frame, 
            text="Imperial (in)", 
            variable=self.is_imperial, 
            value=True,
            command=self._refresh_results
        )
        imperial_radio.pack(side="left", padx=5)
        
        spacer = ctk.CTkLabel(settings_frame, text="")
        spacer.pack(side="left", expand=True)
        
        material_label = ctk.CTkLabel(settings_frame, text="Material:", font=ctk.CTkFont(weight="bold"))
        material_label.pack(side="left", padx=(15, 10))
        
        materials = list(CADAnalyzer.MATERIALS.keys())
        material_dropdown = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.selected_material,
            values=materials,
            command=lambda x: self._refresh_results()
        )
        material_dropdown.pack(side="left", padx=(0, 15))
        
        infill_frame = ctk.CTkFrame(self.main_frame)
        infill_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        infill_label = ctk.CTkLabel(infill_frame, text="Infill:", font=ctk.CTkFont(weight="bold"))
        infill_label.pack(side="left", padx=(15, 10))
        
        self.infill_slider = ctk.CTkSlider(
            infill_frame,
            from_=0,
            to=100,
            number_of_steps=20,
            variable=self.infill_percent,
            command=self._on_infill_change,
            width=200
        )
        self.infill_slider.pack(side="left", padx=5)
        
        self.infill_value_label = ctk.CTkLabel(
            infill_frame, 
            text="20%",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=50
        )
        self.infill_value_label.pack(side="left", padx=5)
        
        presets_label = ctk.CTkLabel(infill_frame, text="Presets:", text_color="gray")
        presets_label.pack(side="left", padx=(20, 5))
        
        for preset_name, preset_val in [("Light", 10), ("Standard", 20), ("Strong", 50), ("Solid", 100)]:
            btn = ctk.CTkButton(
                infill_frame,
                text=preset_name,
                width=60,
                height=25,
                fg_color="transparent",
                border_width=1,
                command=lambda v=preset_val: self._set_infill(v)
            )
            btn.pack(side="left", padx=2)
        
        print_settings_frame = ctk.CTkFrame(self.main_frame)
        print_settings_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(print_settings_frame, text="Print Settings:", 
                     font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(15, 10))
        
        ctk.CTkLabel(print_settings_frame, text="Layer:").pack(side="left", padx=(5, 2))
        layer_menu = ctk.CTkOptionMenu(
            print_settings_frame,
            variable=self.layer_height,
            values=["0.1", "0.15", "0.2", "0.28", "0.3"],
            width=70,
            command=lambda x: self._on_settings_change()
        )
        layer_menu.pack(side="left", padx=2)
        ctk.CTkLabel(print_settings_frame, text="mm").pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(print_settings_frame, text="Speed:").pack(side="left", padx=(5, 2))
        speed_menu = ctk.CTkOptionMenu(
            print_settings_frame,
            variable=self.print_speed,
            values=["30", "40", "50", "60", "80", "100"],
            width=70,
            command=lambda x: self._on_settings_change()
        )
        speed_menu.pack(side="left", padx=2)
        ctk.CTkLabel(print_settings_frame, text="mm/s").pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(print_settings_frame, text="Walls:").pack(side="left", padx=(5, 2))
        wall_menu = ctk.CTkOptionMenu(
            print_settings_frame,
            variable=self.wall_count,
            values=["2", "3", "4", "5"],
            width=60,
            command=lambda x: self._on_settings_change()
        )
        wall_menu.pack(side="left", padx=2)
    
    def _on_settings_change(self):
        """Update when print settings change, with safety checks"""
        try:
            # Validate numeric inputs from dropdowns/vars
            self.layer_height.set(float(self.layer_height.get()))
            self.print_speed.set(int(self.print_speed.get()))
            self.wall_count.set(int(self.wall_count.get()))
        except (ValueError, tk.TclError) as e:
            # Fallback to defaults if something goes wrong with the UI variables
            print(f"Settings validation error: {e}")
        
        self._refresh_results()
    
    def _on_infill_change(self, value):
        """Update infill display"""
        self.infill_value_label.configure(text=f"{int(value)}%")
        self._refresh_results()
    
    def _set_infill(self, value):
        """Set infill preset"""
        self.infill_percent.set(value)
        self.infill_value_label.configure(text=f"{value}%")
        self._refresh_results()
        
    def _create_drop_zone(self):
        """Create drag-and-drop zone"""
        self.drop_frame = ctk.CTkFrame(self.main_frame, height=70, fg_color="#1a1a2e")
        self.drop_frame.pack(fill="x", padx=20, pady=10)
        self.drop_frame.pack_propagate(False)
        
        drop_label = ctk.CTkLabel(
            self.drop_frame,
            text="📁  Drag & Drop STL files here  -or-  Click to Browse",
            font=ctk.CTkFont(size=14)
        )
        drop_label.pack(expand=True)
        
        self.drop_frame.bind("<Button-1>", lambda e: self._browse_files())
        drop_label.bind("<Button-1>", lambda e: self._browse_files())
        
        if DND_AVAILABLE:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self._on_drop)
            
    def _create_file_list(self):
        """Create file list display"""
        list_frame = ctk.CTkFrame(self.main_frame)
        list_frame.pack(fill="x", padx=20, pady=5)
        
        list_header = ctk.CTkFrame(list_frame, fg_color="transparent")
        list_header.pack(fill="x")
        
        ctk.CTkLabel(list_header, text="Files Loaded:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        clear_btn = ctk.CTkButton(
            list_header, 
            text="Clear All", 
            width=80, 
            height=25,
            fg_color="transparent",
            border_width=1,
            command=self._clear_files
        )
        clear_btn.pack(side="right")
        
        self.file_listbox = ctk.CTkTextbox(list_frame, height=120)
        self.file_listbox.pack(fill="x", pady=5)
        self.file_listbox.configure(state="disabled")
        
    def _create_results_table(self):
        """Create results table"""
        results_label = ctk.CTkLabel(
            self.main_frame, 
            text="RESULTS", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        results_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        table_frame = ctk.CTkFrame(self.main_frame)
        table_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        header_frame = ctk.CTkFrame(table_frame, fg_color="#2b2b40", height=30)
        header_frame.pack(fill="x")
        
        headers = ["File", "L", "W", "H", "Volume", "Est. Mass", "Est. Time"]
        widths = [160, 70, 70, 70, 100, 80, 80]
        
        for header, width in zip(headers, widths):
            lbl = ctk.CTkLabel(
                header_frame, 
                text=header, 
                width=width,
                font=ctk.CTkFont(weight="bold")
            )
            lbl.pack(side="left", padx=2, pady=5)
        
        self.results_scroll = ctk.CTkScrollableFrame(table_frame)
        self.results_scroll.pack(fill="both", expand=True)
        
    def _create_export_buttons(self):
        """Create export buttons"""
        export_frame = ctk.CTkFrame(self.main_frame, height=50)
        export_frame.pack(fill="x", side="bottom", padx=20, pady=20)
        
        inner_frame = ctk.CTkFrame(export_frame, fg_color="transparent")
        inner_frame.pack(expand=True, pady=10)
        
        ctk.CTkButton(
            inner_frame,
            text="Export CSV",
            width=130,
            height=35,
            command=self._export_csv
        ).pack(side="left", padx=8)
        
        ctk.CTkButton(
            inner_frame,
            text="Export JSON",
            width=130,
            height=35,
            command=self._export_json
        ).pack(side="left", padx=8)
        
        ctk.CTkButton(
            inner_frame,
            text="Copy to Clipboard",
            width=150,
            height=35,
            command=self._copy_clipboard
        ).pack(side="left", padx=8)
        
    def _browse_files(self):
        """Open file browser"""
        filetypes = [("STL files", "*.stl"), ("All files", "*.*")]
        files = filedialog.askopenfilenames(title="Select STL files", filetypes=filetypes)
        
        if files:
            for f in files:
                if f not in self.files:
                    self.files.append(f)
            self._update_file_list()
            
    def _on_drop(self, event):
        """Handle drag-and-drop"""
        files_str = event.data
        
        if '{' in files_str:
            import re
            files = re.findall(r'\{([^}]+)\}|(\S+)', files_str)
            files = [f[0] or f[1] for f in files]
        else:
            files = files_str.split()
        
        for f in files:
            if f.lower().endswith('.stl') and f not in self.files:
                self.files.append(f)
        
        self._update_file_list()
        
    def _update_file_list(self):
        """Update file list"""
        self.file_listbox.configure(state="normal")
        self.file_listbox.delete("1.0", "end")
        
        for f in self.files:
            filename = Path(f).name
            self.file_listbox.insert("end", f"  {filename}\n")
        
        self.file_listbox.configure(state="disabled")
        
    def _clear_files(self):
        """Clear all files"""
        self.files.clear()
        self.results.clear()
        self._update_file_list()
        self._clear_results_table()
        
    def _analyze_files(self):
        """Run analysis"""
        if not self.files:
            messagebox.showwarning("No Files", "Please add STL files to analyze.")
            return
        
        self.results = CADAnalyzer.analyze_multiple(self.files)
        
        if not self.results:
            messagebox.showerror("Error", "Failed to analyze files. Check file format.")
            return
        
        self._display_results()
        
    def _calculate_print_mass(self, result, density: float, infill_pct: int,
                               wall_count: int = 3, top_bottom_layers: int = 4,
                               layer_height: float = 0.2, wall_width: float = 0.4) -> float:
        """
        Estimate actual 3D print mass by modeling shell and infill separately.
        
        This is much more accurate than volume * density because it accounts for
        the fact that 3D prints are mostly hollow.
        """
        # If 100% infill, use simple volume calculation
        if infill_pct >= 100:
            return result.get_mass(density)
        
        volume_mm3 = result.volume
        surface_area_mm2 = result.surface_area
        
        # 1. Shell Volume (the outer walls)
        # We approximate the shell by multiplying surface area by wall thickness
        wall_thickness = wall_count * wall_width
        shell_volume = surface_area_mm2 * wall_thickness
        
        # 2. Top/Bottom Volume (solid horizontal layers)
        # We estimate the horizontal 'footprint' as roughly 1/6th of total surface area
        # (This is a heuristic for box-like objects)
        estimated_footprint = (surface_area_mm2 / 6)
        top_bottom_volume = estimated_footprint * layer_height * top_bottom_layers * 2
        
        # Combine shell and solid layers, capped at the total volume
        solid_shell_volume = min(shell_volume + top_bottom_volume, volume_mm3 * 0.95)
        
        # 3. Infill Volume (the sparse internal structure)
        infill_volume = max(0, volume_mm3 - solid_shell_volume)
        
        # Calculate mass for each component
        shell_mass = (solid_shell_volume / 1000) * density
        infill_mass = (infill_volume / 1000) * density * (infill_pct / 100)
        
        return shell_mass + infill_mass
    
    def _estimate_print_time(self, result, infill_pct: int,
                             layer_height: float = 0.2,
                             print_speed: float = 50,
                             travel_speed: float = 150) -> float:
        """
        Estimate print time in minutes using extrusion rate physics.
        
        Heuristic includes:
        - Volume extrusion time (primary factor)
        - Layer change overhead
        - Non-printing travel time approximation
        """
        volume_mm3 = result.volume
        height_mm = result.height
        
        # Adjust volume based on infill (0% infill doesn't mean 0 volume, need walls)
        effective_volume = volume_mm3 * (0.3 + 0.7 * (infill_pct / 100))
        
        # Basic extrusion rate formula: Area of nozzle path * speed
        nozzle_width = 0.4
        extrusion_rate = layer_height * nozzle_width * print_speed
        extrusion_time_sec = effective_volume / extrusion_rate
        
        # Overhead for Z-axis moves between layers
        num_layers = height_mm / layer_height
        layer_change_time_sec = num_layers * 1.5 # 1.5s per layer change
        
        # Overhead for travel (non-extruding moves)
        travel_time_sec = extrusion_time_sec * 0.25 # Assume 25% of time is travel
        
        total_minutes = (extrusion_time_sec + layer_change_time_sec + travel_time_sec) / 60
        return total_minutes
    
    def _display_results(self):
        """Display analysis results in the scrollable table"""
        self._clear_results_table()
        
        imperial = self.is_imperial.get()
        material = self.selected_material.get()
        density = CADAnalyzer.MATERIALS.get(material, 1.24)
        infill = self.infill_percent.get()
        
        # Safely retrieve print settings
        try:
            layer_h = float(self.layer_height.get())
            speed = int(self.print_speed.get())
            walls = int(self.wall_count.get())
        except (ValueError, tk.TclError):
            layer_h, speed, walls = 0.2, 50, 3
        
        # Column widths matching the header
        widths = [160, 70, 70, 70, 100, 80, 80]
        
        for result in self.results:
            row_frame = ctk.CTkFrame(self.results_scroll, fg_color="transparent")
            row_frame.pack(fill="x", pady=1)
            
            # Unit formatting logic
            if imperial:
                l_str = f'{result.length * 0.0393701:.2f}"'
                w_str = f'{result.width * 0.0393701:.2f}"'
                h_str = f'{result.height * 0.0393701:.2f}"'
                vol_str = f'{result.volume * 0.0000610237:.3f} in³'
            else:
                l_str = f'{result.length:.1f}mm'
                w_str = f'{result.width:.1f}mm'
                h_str = f'{result.height:.1f}mm'
                vol_str = f'{result.volume:,.0f} mm³' # Added comma for readability
            
            # Calculate estimated print stats
            print_mass = self._calculate_print_mass(
                result, density, infill,
                wall_count=walls, layer_height=layer_h
            )
            mass_str = f'{print_mass:.1f}g'
            
            print_time = self._estimate_print_time(
                result, infill,
                layer_height=layer_h, print_speed=speed
            )
            
            # Format time into h/m
            if print_time < 60:
                time_str = f'{print_time:.0f} min'
            else:
                hours = int(print_time // 60)
                mins = int(print_time % 60)
                time_str = f'{hours}h {mins}m'
            
            values = [result.filename, l_str, w_str, h_str, vol_str, mass_str, time_str]
            
            for i, (val, width) in enumerate(zip(values, widths)):
                # Truncate long filenames to prevent UI overflow
                display_val = val
                if i == 0 and len(val) > 20:
                    display_val = val[:18] + "..."
                
                lbl = ctk.CTkLabel(row_frame, text=display_val, width=width, anchor="w")
                lbl.pack(side="left", padx=2)
                
    def _clear_results_table(self):
        """Clear results table"""
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
            
    def _refresh_results(self):
        """Refresh results display"""
        if self.results:
            self._display_results()
            
    def _export_csv(self):
        """Export to CSV"""
        if not self.results:
            messagebox.showwarning("No Results", "Run analysis first.")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save CSV"
        )
        
        if not filepath:
            return
        
        imperial = self.is_imperial.get()
        material = self.selected_material.get()
        density = CADAnalyzer.MATERIALS.get(material, 1.24)
        infill = self.infill_percent.get()
        
        try:
            layer_h = float(self.layer_height.get())
            speed = int(self.print_speed.get())
            walls = int(self.wall_count.get())
        except:
            layer_h, speed, walls = 0.2, 50, 3
        
        unit = "in" if imperial else "mm"
        vol_unit = "in³" if imperial else "mm³"
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "File", 
                f"L ({unit})", 
                f"W ({unit})", 
                f"H ({unit})", 
                f"Volume ({vol_unit})",
                f"Est. Mass (g) [{material} @ {infill}%]",
                "Est. Time (min)"
            ])
            
            for result in self.results:
                data = result.to_dict(imperial=imperial)
                print_mass = self._calculate_print_mass(result, density, infill, wall_count=walls, layer_height=layer_h)
                print_time = self._estimate_print_time(result, infill, layer_height=layer_h, print_speed=speed)
                writer.writerow([
                    result.filename,
                    f"{data['length']:.2f}",
                    f"{data['width']:.2f}",
                    f"{data['height']:.2f}",
                    f"{data['volume']:.3f}",
                    f"{print_mass:.2f}",
                    f"{print_time:.1f}"
                ])
        
        messagebox.showinfo("Exported", f"Saved to {filepath}")
        
    def _export_json(self):
        """Export to JSON"""
        if not self.results:
            messagebox.showwarning("No Results", "Run analysis first.")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save JSON"
        )
        
        if not filepath:
            return
        
        imperial = self.is_imperial.get()
        material = self.selected_material.get()
        density = CADAnalyzer.MATERIALS.get(material, 1.24)
        infill = self.infill_percent.get()
        
        # Get print settings
        try:
            layer_h = float(self.layer_height.get())
            speed = int(self.print_speed.get())
            walls = int(self.wall_count.get())
        except:
            layer_h, speed, walls = 0.2, 50, 3
        
        export_data = {
            "settings": {
                "units": "imperial" if imperial else "metric",
                "material": material,
                "density_g_cm3": density,
                "infill_percent": infill,
                "layer_height_mm": layer_h,
                "print_speed_mm_s": speed,
                "wall_count": walls
            },
            "results": []
        }
        
        for result in self.results:
            data = result.to_dict(imperial=imperial)
            data['solid_mass_g'] = result.get_mass(density)
            data['print_mass_g'] = self._calculate_print_mass(result, density, infill, wall_count=walls, layer_height=layer_h)
            data['est_print_time_min'] = self._estimate_print_time(result, infill, layer_height=layer_h, print_speed=speed)
            export_data["results"].append(data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        messagebox.showinfo("Exported", f"Saved to {filepath}")
        
    def _copy_clipboard(self):
        """Copy results to clipboard"""
        if not self.results:
            messagebox.showwarning("No Results", "Run analysis first.")
            return
        
        imperial = self.is_imperial.get()
        material = self.selected_material.get()
        density = CADAnalyzer.MATERIALS.get(material, 1.24)
        infill = self.infill_percent.get()
        
        try:
            layer_h = float(self.layer_height.get())
            speed = int(self.print_speed.get())
            walls = int(self.wall_count.get())
        except:
            layer_h, speed, walls = 0.2, 50, 3
        
        unit = "in" if imperial else "mm"
        
        lines = [f"File\tL ({unit})\tW ({unit})\tH ({unit})\tVolume\tEst. Mass (g)\tEst. Time"]
        
        for result in self.results:
            data = result.to_dict(imperial=imperial)
            print_mass = self._calculate_print_mass(result, density, infill, wall_count=walls, layer_height=layer_h)
            print_time = self._estimate_print_time(result, infill, layer_height=layer_h, print_speed=speed)
            line = f"{result.filename}\t{data['length']:.2f}\t{data['width']:.2f}\t{data['height']:.2f}\t{data['volume']:.2f}\t{print_mass:.2f}\t{print_time:.1f} min"
            lines.append(line)
        
        text = "\n".join(lines)
        
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        
        messagebox.showinfo("Copied", "Results copied to clipboard!\nPaste into Excel or Word.")
        
    def run(self):
        """Start app"""
        self.root.mainloop()


if __name__ == "__main__":
    app = CADAnalyzerApp()
    app.run()

