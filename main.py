import os
import sys
import threading
import tempfile
import shutil
import math
import traceback
import tkinter as tk
import subprocess 
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk, ImageOps

# --- HEIC SUPPORT IMPORT ---
from pillow_heif import register_heif_opener
register_heif_opener() 

# --- ANTI-FLICKER PATCH (WINDOWS) ---
if sys.platform.startswith("win"):
    _original_Popen = subprocess.Popen
    class Popen(_original_Popen):
        def __init__(self, *args, **kwargs):
            if "creationflags" not in kwargs:
                kwargs["creationflags"] = 0x08000000 
            super().__init__(*args, **kwargs)
    subprocess.Popen = Popen

# --- DEPENDENCY CHECK: TKINTERDND2 ---
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAIL = True
except ImportError:
    DND_AVAIL = False
    print("Warning: tkinterdnd2 not found. Drag and drop will be disabled.")

from pdf2image import convert_from_path
import img2pdf

# --- CONFIGURATION ---
ctk.set_appearance_mode("Light") 
ctk.set_default_color_theme("blue")

# --- THEME COLORS (OFFICIAL US FLAG PALETTE) ---
COLOR_MAIN_BG = "#F8F9FA"       # Off-White Background
COLOR_HEADER_BG = "#002868"     # Old Glory Blue (Deep Navy)
COLOR_CARD_BG = "#FFFFFF"       # Pure White Cards
COLOR_ACCENT = "#BF0A30"        # Old Glory Red
COLOR_BTN_HOVER = "#8A0722"     # Darker Red for Hover
COLOR_TEXT_BLACK = "#333333"    # Dark Grey Text
COLOR_TEXT_WHITE = "white"      # White Text
COLOR_DROPDOWN_BG = "#FFFFFF"   # White Dropdown Background
COLOR_BORDER = "#E0E0E0"        # Light Grey Border for Cards

# --- RESOURCE HELPER ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- REFINED SPLITTER ENGINE (Isolation Check) ---
def detect_split_structure(img, threshold=100):
    w, h = img.size
    gray = img.convert("L")
    pixels = gray.load()

    start_y = int(h * 0.25)
    end_y = int(h * 0.75)
    
    candidate_y = -1
    best_score = 0
    
    for y in range(start_y, end_y):
        dark_pixel_count = 0
        for x in range(0, w, 5):
            if pixels[x, y] < threshold:
                dark_pixel_count += 1
        
        dark_percent = dark_pixel_count / (w / 5)
        
        if dark_percent > 0.45:
            is_isolated = True
            for offset in [-10, 10]: 
                check_y = y + offset
                if 0 <= check_y < h:
                    adj_dark_count = 0
                    for ax in range(0, w, 10): 
                         if pixels[ax, check_y] < threshold:
                             adj_dark_count += 1
                    
                    adj_percent = adj_dark_count / (w / 10)
                    if adj_percent > 0.15: 
                        is_isolated = False
                        break
            
            if is_isolated:
                dist_from_center = abs(y - (h // 2))
                score = 10000 - dist_from_center 
                if score > best_score:
                    best_score = score
                    candidate_y = y

    if candidate_y != -1:
        return [(0, 0, w, candidate_y - 2), (0, candidate_y + 2, w, h)]
    else:
        return [(0, 0, w, h)]

# --- 1. SMART PAGE SELECTOR ---
class VisualPageSelector(ctk.CTkToplevel):
    def __init__(self, parent, pdf_path, poppler_path):
        super().__init__(parent)
        self.title("Select Parts to Extract")
        self.geometry("1100x750")
        
        self.temp_dir = tempfile.mkdtemp()
        self.pdf_path = pdf_path
        self.poppler_path = poppler_path
        
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.after(200, lambda: self.iconbitmap(icon_path))
        
        self.transient(parent)
        self.grab_set()
        self.after(200, lambda: self.focus())
        self.configure(fg_color=COLOR_MAIN_BG)

        self.selected_ids = set()
        self.card_refs = {}
        self.item_data = {} 
        self.result = None
        
        # Header (Blue)
        top = ctk.CTkFrame(self, fg_color=COLOR_HEADER_BG, corner_radius=0)
        top.pack(fill="x")
        
        title_frame = ctk.CTkFrame(top, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(title_frame, text="Select Items to Extract", font=("Roboto Medium", 22), text_color="white").pack(side="left")
        
        btn_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        btn_frame.pack(side="right")
        
        # Red Accent Buttons
        ctk.CTkButton(btn_frame, text="Select All", width=120, fg_color=COLOR_ACCENT, text_color="white", hover_color=COLOR_BTN_HOVER, command=self.select_all).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Deselect All", width=120, fg_color="transparent", border_width=1, border_color="white", text_color="white", command=self.deselect_all).pack(side="left", padx=5)

        # Gallery
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=COLOR_MAIN_BG)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # Footer
        bot = ctk.CTkFrame(self, fg_color="transparent", height=60)
        bot.pack(fill="x", padx=20, pady=20)
        ctk.CTkButton(bot, text="Cancel", fg_color="transparent", text_color="gray", hover_color="#EEEEEE", command=self.close_safe).pack(side="right", padx=10)
        ctk.CTkButton(bot, text="Confirm Selection", width=150, height=40, font=("Roboto Medium", 14), fg_color=COLOR_ACCENT, text_color="white", hover_color=COLOR_BTN_HOVER, command=self.on_confirm).pack(side="right")

        self.loading_lbl = ctk.CTkLabel(self.scroll, text="Analyzing PDF Structure...\n(Scanning for split lines...)", font=("Roboto", 16), text_color="black")
        self.loading_lbl.pack(pady=150)

        threading.Thread(target=self.thread_load_smart, daemon=True).start()

    def thread_load_smart(self):
        try:
            pages = convert_from_path(self.pdf_path, dpi=72, poppler_path=self.poppler_path, fmt='jpeg')
            display_items = []
            
            for i, p in enumerate(pages):
                page_num = i + 1
                boxes = detect_split_structure(p)
                
                for idx, box in enumerate(boxes):
                    segment = p.crop(box)
                    seg_filename = f"p{page_num}_{idx}.jpg"
                    seg_path = os.path.join(self.temp_dir, seg_filename)
                    segment.save(seg_path, "JPEG")
                    
                    item_id = f"p{page_num}_{idx}"
                    self.item_data[item_id] = {
                        "id": item_id, "page": page_num, "sub_idx": idx + 1,
                        "box": box, "orig_w": p.width, "path": seg_path
                    }
                    display_items.append(self.item_data[item_id])

            self.after(0, lambda: self.build_ui(display_items))

        except Exception as e:
            traceback.print_exc()
            self.after(0, lambda: self.show_error(str(e)))

    def show_error(self, msg):
        self.loading_lbl.configure(text=f"Error: {msg}", text_color="#D32F2F")

    def build_ui(self, items):
        self.loading_lbl.destroy()
        cols = 5
        for i, item in enumerate(items):
            try:
                pil_img = Image.open(item['path'])
                pil_img.thumbnail((120, 160))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
            except: continue

            # Card Style: White with Light Grey Border
            card = ctk.CTkFrame(self.scroll, corner_radius=10, border_width=2, 
                                border_color=COLOR_BORDER, fg_color=COLOR_CARD_BG)
            card.grid(row=i//cols, column=i%cols, padx=10, pady=10)

            btn = ctk.CTkButton(
                card, text="", image=ctk_img, 
                fg_color="transparent", hover_color="#EEEEEE",
                width=130, height=170,
                command=lambda x=item['id']: self.toggle_item(x)
            )
            btn.pack(padx=5, pady=(5,0))
            
            lbl_txt = f"Page {item['page']}"
            count_on_page = len([x for x in items if x['page'] == item['page']])
            if count_on_page > 1:
                lbl_txt += f"-{item['sub_idx']}"
                
            ctk.CTkLabel(card, text=lbl_txt, font=("Roboto", 13, "bold"), text_color=COLOR_TEXT_BLACK).pack(pady=5)
            self.card_refs[item['id']] = card
            
            # Default state: Deselected
            self.toggle_item(item['id'], force_state=False)

    def toggle_item(self, iid, force_state=None):
        card = self.card_refs[iid]
        is_sel = force_state if force_state is not None else (iid not in self.selected_ids)
        if is_sel:
            self.selected_ids.add(iid)
            card.configure(border_color=COLOR_ACCENT) # Red Border when selected
        else:
            self.selected_ids.discard(iid)
            card.configure(border_color=COLOR_BORDER) # Grey Border when deselected

    def select_all(self):
        for iid in self.card_refs: self.toggle_item(iid, force_state=True)
    def deselect_all(self):
        for iid in self.card_refs: self.toggle_item(iid, force_state=False)
    def on_confirm(self):
        if not self.selected_ids: return
        selected = [self.item_data[iid] for iid in self.selected_ids]
        selected.sort(key=lambda x: (x['page'], x['sub_idx']))
        self.result = selected
        self.close_safe()
    def close_safe(self):
        try: shutil.rmtree(self.temp_dir)
        except: pass
        self.destroy()

# --- 2. VISUAL SORT INTERFACE ---
class VisualSortInterface(ctk.CTkToplevel):
    def __init__(self, parent, image_paths):
        super().__init__(parent)
        self.title("Reorder Images")
        self.geometry("1100x800")
        
        self.image_paths = image_paths
        self.result_paths = None
        self.drag_data = {"item_idx": None, "widget": None}
        self.drag_window = None 
        self.card_widgets = [] 
        
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=COLOR_MAIN_BG)
        
        # Header (Blue)
        top = ctk.CTkFrame(self, fg_color=COLOR_HEADER_BG, corner_radius=0)
        top.pack(fill="x")
        
        title_frame = ctk.CTkFrame(top, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(title_frame, text="Arrange Images", font=("Roboto Medium", 22), text_color="white").pack(side="left")
        ctk.CTkLabel(title_frame, text="(Drag to reorder)", font=("Roboto", 14), text_color="#DDDDDD").pack(side="left", padx=10)
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=COLOR_MAIN_BG)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.pack(fill="x", padx=20, pady=20)
        ctk.CTkButton(bot, text="Cancel", fg_color="transparent", text_color="gray", command=self.destroy).pack(side="right")
        ctk.CTkButton(bot, text="Create PDF", width=150, height=40, font=("Roboto Medium", 14), 
                      fg_color=COLOR_ACCENT, text_color="white", hover_color=COLOR_BTN_HOVER, command=self.on_confirm).pack(side="right", padx=10)
        
        self.refresh_grid()

    def get_square_thumb(self, path, size=(120, 120)):
        try:
            img = Image.open(path) 
            img.thumbnail(size)
            bg = Image.new('RGBA', size, (0, 0, 0, 0))
            offset = ((size[0] - img.size[0]) // 2, (size[1] - img.size[1]) // 2)
            bg.paste(img, offset)
            return ctk.CTkImage(light_image=bg, dark_image=bg, size=size)
        except:
            return None

    def refresh_grid(self):
        for w in self.scroll.winfo_children(): w.destroy()
        self.card_widgets = []
        cols = 4 
        
        for i, path in enumerate(self.image_paths):
            f = ctk.CTkFrame(self.scroll, fg_color=COLOR_CARD_BG, width=180, height=240, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
            f.pack_propagate(False) 
            f.grid(row=i//cols, column=i%cols, padx=10, pady=10)
            self.card_widgets.append(f)
            
            top_bar = ctk.CTkFrame(f, fg_color="transparent", height=25)
            top_bar.pack(fill="x", padx=5, pady=(5,0))
            ctk.CTkButton(top_bar, text="X", width=24, height=24, fg_color="#FF5555", hover_color="#990000", text_color="white",
                          command=lambda idx=i: self.remove(idx)).pack(side="right")

            img_container = ctk.CTkLabel(f, text="", cursor="hand2")
            thumb = self.get_square_thumb(path)
            if thumb: img_container.configure(image=thumb)
            else: img_container.configure(text="Error")
            img_container.pack(pady=5, padx=10, expand=True)
            
            img_container.bind("<ButtonPress-1>", lambda event, idx=i: self.on_drag_start(event, idx))
            img_container.bind("<B1-Motion>", self.on_drag_motion)
            img_container.bind("<ButtonRelease-1>", self.on_drag_stop)
            
            ctrl = ctk.CTkFrame(f, fg_color="transparent", height=40)
            ctrl.pack(side="bottom", fill="x", pady=10, padx=5)
            
            if i > 0:
                ctk.CTkButton(ctrl, text="<", width=30, fg_color=COLOR_ACCENT, text_color="white", hover_color=COLOR_BTN_HOVER, 
                              command=lambda idx=i: self.move_left(idx)).pack(side="left")
            
            ctk.CTkLabel(ctrl, text=str(i+1), font=("Roboto", 14, "bold"), text_color=COLOR_TEXT_BLACK).pack(side="left", expand=True)
            
            if i < len(self.image_paths) - 1:
                ctk.CTkButton(ctrl, text=">", width=30, fg_color=COLOR_ACCENT, text_color="white", hover_color=COLOR_BTN_HOVER, 
                              command=lambda idx=i: self.move_right(idx)).pack(side="right")

    def on_drag_start(self, event, idx):
        self.drag_data["item_idx"] = idx
        self.configure(cursor="fleur")
        self.drag_window = ctk.CTkToplevel(self)
        self.drag_window.overrideredirect(True)
        self.drag_window.attributes("-topmost", True)
        self.drag_window.attributes("-alpha", 0.7) 
        
        path = self.image_paths[idx]
        thumb = self.get_square_thumb(path, size=(100, 100))
        lbl = ctk.CTkLabel(self.drag_window, text="", image=thumb)
        lbl.pack()
        x, y = event.x_root, event.y_root
        self.drag_window.geometry(f"+{x+15}+{y+15}")

    def on_drag_motion(self, event):
        if self.drag_window:
            x, y = event.x_root, event.y_root
            self.drag_window.geometry(f"+{x+15}+{y+15}")

    def on_drag_stop(self, event):
        if self.drag_window:
            self.drag_window.destroy()
            self.drag_window = None
        self.configure(cursor="")
        
        src_idx = self.drag_data["item_idx"]
        if src_idx is None: return

        x_root = self.winfo_pointerx()
        y_root = self.winfo_pointery()
        
        closest_idx = -1
        min_dist = float('inf')
        
        for i, card in enumerate(self.card_widgets):
            try:
                cx = card.winfo_rootx() + (card.winfo_width() // 2)
                cy = card.winfo_rooty() + (card.winfo_height() // 2)
                dist = math.hypot(x_root - cx, y_root - cy)
                
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            except: continue
            
        if closest_idx == -1: return

        target_card = self.card_widgets[closest_idx]
        card_center_x = target_card.winfo_rootx() + (target_card.winfo_width() // 2)
        
        insert_at = closest_idx
        if x_root > card_center_x: insert_at = closest_idx + 1

        if src_idx != insert_at:
            item = self.image_paths.pop(src_idx)
            if insert_at > src_idx: insert_at -= 1
            if insert_at < 0: insert_at = 0
            if insert_at > len(self.image_paths): insert_at = len(self.image_paths)
            self.image_paths.insert(insert_at, item)
            self.refresh_grid()
        self.drag_data["item_idx"] = None

    def move_left(self, i):
        self.image_paths[i], self.image_paths[i-1] = self.image_paths[i-1], self.image_paths[i]
        self.refresh_grid()
    def move_right(self, i):
        self.image_paths[i], self.image_paths[i+1] = self.image_paths[i+1], self.image_paths[i]
        self.refresh_grid()
    def remove(self, i):
        self.image_paths.pop(i)
        self.refresh_grid()
    def on_confirm(self):
        self.result_paths = self.image_paths
        self.destroy()

# --- 3. MAIN APP ---
BaseClass = TkinterDnD.DnDWrapper if DND_AVAIL else object

class ModernApp(ctk.CTk, BaseClass):
    def __init__(self):
        super().__init__()
        self.title("PDF and Image Converter")
        self.geometry("800x750")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_MAIN_BG)
        
        if DND_AVAIL:
            self.TkdndVersion = TkinterDnD._require(self)
        
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        self.grid_columnconfigure(0, weight=1)

        # Header (Blue)
        header = ctk.CTkFrame(self, corner_radius=0, height=80, fg_color=COLOR_HEADER_BG)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="PDF and Image Converter", font=("Roboto Medium", 26), text_color="white").pack(pady=25, padx=30, anchor="w")

        # Container
        main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=30, pady=20)

        # 1. PDF -> Image (DROP ZONE 1)
        self.card_p2i = self.create_card(main_frame, "PDF to Image", "Convert To", "fmt_var", ["PNG", "JPEG", "TIFF", "BMP"], "OPEN PDF...", self.flow_p2i)
        
        # 2. Image -> PDF (DROP ZONE 2)
        # Filters include .heic and .heif
        self.card_i2p = self.create_card(main_frame, "Image to PDF", "Output Format", "dummy_pdf", ["PDF"], "SELECT IMAGES TO MERGE...", self.flow_i2p, is_pdf_mode=True)

        # 3. Image Converter (DROP ZONE 3)
        # Filters include .heic and .heif
        self.card_i2i = self.create_card(main_frame, "Image Converter", "Convert To", "fmt_var_i2i", ["JPEG", "PNG", "TIFF", "BMP", "WEBP"], "SELECT IMAGES...", self.flow_i2i)

        # Footer
        if DND_AVAIL:
            self.dnd_lbl = ctk.CTkLabel(self, text="[Drag Files onto the specific card above]", text_color="gray60")
            self.dnd_lbl.pack(pady=5)
            self.card_p2i.drop_target_register(DND_FILES)
            self.card_p2i.dnd_bind('<<Drop>>', self.on_drop_p2i)
            self.card_i2p.drop_target_register(DND_FILES)
            self.card_i2p.dnd_bind('<<Drop>>', self.on_drop_i2p)
            self.card_i2i.drop_target_register(DND_FILES)
            self.card_i2i.dnd_bind('<<Drop>>', self.on_drop_i2i)

        self.status = ctk.CTkLabel(self, text="Ready", text_color="gray60")
        self.status.pack(side="bottom", pady=10)

    def create_card(self, parent, title, sub_label, dropdown_var_name, dropdown_vals, btn_text, cmd, is_pdf_mode=False):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        card.pack(fill="x", pady=10, ipady=10)

        ctk.CTkLabel(card, text=title, font=("Roboto Medium", 18), text_color=COLOR_TEXT_BLACK).pack(anchor="w", padx=20, pady=(15, 5))

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=(0, 15))

        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text=sub_label, font=("Roboto", 12), text_color="gray40").pack(anchor="w")
        
        if is_pdf_mode:
            ctk.CTkButton(left, text="PDF", width=80, fg_color="#EEEEEE", text_color="gray", state="disabled").pack(pady=(2,0))
        else:
            var = ctk.StringVar(value=dropdown_vals[0])
            setattr(self, dropdown_var_name, var)
            
            # --- SWITCHED TO COMBOBOX FOR BORDER SUPPORT ---
            ctk.CTkComboBox(left, variable=var, values=dropdown_vals, width=110, state="readonly",
                            fg_color=COLOR_DROPDOWN_BG, border_width=2, border_color=COLOR_HEADER_BG, # Blue Border
                            button_color=COLOR_HEADER_BG, button_hover_color="#004080", text_color=COLOR_TEXT_BLACK).pack(pady=(2,0))

        ctk.CTkButton(content, text=btn_text, height=40, font=("Roboto Medium", 13),
                      fg_color=COLOR_ACCENT, text_color="white", hover_color=COLOR_BTN_HOVER,
                      command=cmd).pack(side="left", padx=(20, 0), fill="x", expand=True, anchor="s")
        return card

    # --- SPECIFIC DROP HANDLERS ---
    def on_drop_p2i(self, event):
        files = self.tk.splitlist(event.data)
        if files and files[0].lower().endswith(".pdf"):
            self.process_p2i_path(files[0])
        else:
            messagebox.showerror("Error", "Please drop a PDF file here.")

    def on_drop_i2p(self, event):
        files = self.tk.splitlist(event.data)
        imgs = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.heic', '.heif'))]
        if imgs:
            self.process_i2p_paths(imgs)
        else:
            messagebox.showerror("Error", "Please drop image files here.")

    def on_drop_i2i(self, event):
        files = self.tk.splitlist(event.data)
        imgs = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp', '.heic', '.heif'))]
        if imgs:
            self.process_i2i_paths(imgs)
        else:
            messagebox.showerror("Error", "Please drop image files here.")

    # --- UTILS & FLOWS ---
    def get_poppler(self):
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
            p = os.path.join(base, 'poppler_bin')
            if os.path.exists(os.path.join(p, 'pdftoppm.exe')): return p
        local = os.path.join(os.getcwd(), 'poppler', 'Library', 'bin')
        if os.path.exists(os.path.join(local, 'pdftoppm.exe')): return local
        local2 = os.path.join(os.getcwd(), 'poppler', 'bin')
        if os.path.exists(os.path.join(local2, 'pdftoppm.exe')): return local2
        return ""

    def set_state(self, busy, msg=""):
        self.status.configure(text=f"● {msg}" if busy else "Ready", text_color=COLOR_ACCENT if busy else "gray60")

    def flow_p2i(self):
        pdf = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if pdf: self.process_p2i_path(pdf)

    def process_p2i_path(self, pdf):
        pop = self.get_poppler()
        if not pop:
            messagebox.showerror("Error", "Poppler not found.")
            return
        gal = VisualPageSelector(self, pdf, pop)
        self.wait_window(gal)
        if not gal.result: return

        fmt = self.fmt_var.get()
        target_file = filedialog.asksaveasfilename(
            title="Save Base Name",
            initialfile=os.path.splitext(os.path.basename(pdf))[0], 
            defaultextension="." + fmt.lower(),
            filetypes=[(fmt, "*." + fmt.lower())]
        )
        if not target_file: return
        
        out_dir = os.path.dirname(target_file)
        base_name = os.path.splitext(os.path.basename(target_file))[0]
        self.set_state(True, "Extracting...")
        self.update() 
        threading.Thread(target=self.work_p2i, args=(pdf, out_dir, base_name, gal.result, pop, fmt), daemon=True).start()

    def work_p2i(self, pdf, out_dir, base_name, items, pop, fmt):
        try:
            ext = "jpg" if fmt == "JPEG" else fmt.lower()
            pages_map = {}
            for item in items:
                p = item['page']
                if p not in pages_map: pages_map[p] = []
                pages_map[p].append(item)

            for p_num, p_items in pages_map.items():
                high_res_imgs = convert_from_path(pdf, poppler_path=pop, dpi=300, first_page=p_num, last_page=p_num)
                if not high_res_imgs: continue
                
                full_page_img = high_res_imgs[0]
                low_w = p_items[0]['orig_w']
                high_w = full_page_img.width
                scale = high_w / low_w
                
                for item in p_items:
                    lx, ly, ux, uy = item['box']
                    crop_box = (int(lx * scale), int(ly * scale), int(ux * scale), int(uy * scale))
                    final_img = full_page_img.crop(crop_box)
                    if fmt == "JPEG" and final_img.mode != "RGB": final_img = final_img.convert("RGB")
                    
                    suffix = f"_p{p_num}"
                    if len(p_items) > 1: suffix += f"_{item['sub_idx']}"
                    
                    final_img.save(os.path.join(out_dir, f"{base_name}{suffix}.{ext}"), fmt)

            self.after(0, lambda: messagebox.showinfo("Success", "Extraction Complete!"))
            self.after(0, lambda: self.set_state(False))
        except Exception as e:
            traceback.print_exc()
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.set_state(False))

    def flow_i2p(self):
        imgs = filedialog.askopenfilenames(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.heic;*.heif")])
        if imgs: self.process_i2p_paths(list(imgs))

    def process_i2p_paths(self, imgs):
        sorter = VisualSortInterface(self, imgs)
        self.wait_window(sorter)
        if not sorter.result_paths: return
        save = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not save: return
        self.set_state(True, "Merging...")
        self.update()
        threading.Thread(target=self.work_i2p, args=(sorter.result_paths, save), daemon=True).start()

    def work_i2p(self, imgs, save_path):
        try:
            image_list = []
            for img_path in imgs:
                img = Image.open(img_path) 
                if img.mode != "RGB": img = img.convert("RGB")
                image_list.append(img)
            
            if image_list:
                first = image_list[0]
                rest = image_list[1:]
                first.save(save_path, "PDF", resolution=100.0, save_all=True, append_images=rest)

            self.after(0, lambda: messagebox.showinfo("Success", "PDF Created!"))
            self.after(0, lambda: self.set_state(False))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.set_state(False))

    def flow_i2i(self):
        imgs = filedialog.askopenfilenames(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.webp;*.heic;*.heif")])
        if imgs: self.process_i2i_paths(list(imgs))

    def process_i2i_paths(self, imgs):
        out_dir = filedialog.askdirectory(title="Select Output Folder")
        if not out_dir: return
        fmt = self.fmt_var_i2i.get()
        self.set_state(True, f"Converting to {fmt}...")
        self.update()
        threading.Thread(target=self.work_i2i, args=(imgs, out_dir, fmt), daemon=True).start()

    def work_i2i(self, imgs, out_dir, fmt):
        try:
            ext = "jpg" if fmt == "JPEG" else fmt.lower()
            for img_path in imgs:
                try:
                    with Image.open(img_path) as im:
                        base = os.path.splitext(os.path.basename(img_path))[0]
                        if fmt == "JPEG" and im.mode in ("RGBA", "P"): im = im.convert("RGB")
                        im.save(os.path.join(out_dir, f"{base}.{ext}"), fmt)
                except: pass
            self.after(0, lambda: messagebox.showinfo("Success", "Batch Conversion Complete!"))
            self.after(0, lambda: self.set_state(False))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.set_state(False))

if __name__ == "__main__":
    app = ModernApp()
    app.mainloop()