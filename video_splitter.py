import os
import sys
import re
import math
import subprocess
import threading
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


def bundled_tool(name):
    """Find FFmpeg tools bundled with the app, or fall back to PATH."""
    base_dir = getattr(
        sys, "_MEIPASS",
        os.path.dirname(os.path.abspath(__file__))
    )
    executable = name + ".exe" if os.name == "nt" else name
    candidate = os.path.join(base_dir, executable)
    return candidate if os.path.isfile(candidate) else name


class VideoSplitter:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Splitter")
        self.root.geometry("720x700")
        self.root.minsize(500, 400)

        self.video = ""
        self.folder = ""
        self.running = False
        self.process_handle = None
        self.cancel_event = threading.Event()
        self.duration = 0
        self.preview_image = None

        style = ttk.Style()
        style.theme_use("clam")

        # Contenedor con desplazamiento vertical
        container = ttk.Frame(root)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            container, orient="vertical", command=canvas.yview
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        main = ttk.Frame(canvas, padding=22)
        window_id = canvas.create_window(
            (0, 0), window=main, anchor="nw"
        )

        main.bind(
            "<Configure>",
            lambda event: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(
                window_id, width=event.width
            )
        )

        # Rueda del mouse en Ubuntu y otros sistemas
        canvas.bind_all(
            "<MouseWheel>",
            lambda event: canvas.yview_scroll(
                -1 if event.delta > 0 else 1, "units"
            )
        )
        canvas.bind_all(
            "<Button-4>",
            lambda event: canvas.yview_scroll(-1, "units")
        )
        canvas.bind_all(
            "<Button-5>",
            lambda event: canvas.yview_scroll(1, "units")
        )

        ttk.Label(
            main, text="VIDEO SPLITTER",
            font=("Arial", 24, "bold")
        ).pack(pady=(0, 4))

        ttk.Label(
            main, text="Divide tus videos fácilmente",
            font=("Arial", 10)
        ).pack(pady=(0, 15))

        # Vista previa
        preview_frame = ttk.LabelFrame(
            main, text="Vista previa del video", padding=10
        )
        preview_frame.pack(fill="x", pady=5)

        self.preview = ttk.Label(
            preview_frame,
            text="Selecciona un video para ver su vista previa",
            anchor="center",
            justify="center"
        )
        self.preview.pack(fill="x", pady=8)

        self.duration_label = ttk.Label(
            preview_frame, text="Duración: --:--:--"
        )
        self.duration_label.pack()

        # Seleccionar video
        ttk.Label(
            main, text="1. Seleccionar video",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(12, 3))

        row = ttk.Frame(main)
        row.pack(fill="x", pady=4)

        self.video_label = ttk.Label(
            row, text="Ningún video seleccionado",
            foreground="gray"
        )
        self.video_label.pack(side="left", fill="x", expand=True)

        ttk.Button(
            row, text="Buscar video",
            command=self.select_video
        ).pack(side="right")

        # Carpeta
        ttk.Label(
            main, text="2. Carpeta de destino",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(12, 3))

        row = ttk.Frame(main)
        row.pack(fill="x", pady=4)

        self.folder_label = ttk.Label(
            row, text="Ninguna carpeta seleccionada",
            foreground="gray"
        )
        self.folder_label.pack(side="left", fill="x", expand=True)

        ttk.Button(
            row, text="Buscar carpeta",
            command=self.select_folder
        ).pack(side="right")

        # Nombre
        ttk.Label(
            main, text="3. Nombre de los archivos",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(12, 3))

        self.name = tk.StringVar(value="Mi Video")
        ttk.Entry(main, textvariable=self.name).pack(fill="x", pady=4)

        # Duración de partes
        ttk.Label(
            main, text="4. Duración de cada parte",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(12, 3))

        row = ttk.Frame(main)
        row.pack(anchor="w", pady=4)

        self.minutes = tk.StringVar(value="2")
        self.seconds = tk.StringVar(value="0")

        ttk.Label(row, text="Minutos").pack(side="left")
        ttk.Spinbox(
            row, from_=0, to=999, width=7,
            textvariable=self.minutes,
            command=self.update_estimate
        ).pack(side="left", padx=8)

        ttk.Label(row, text="Segundos").pack(side="left")
        ttk.Spinbox(
            row, from_=0, to=59, width=7,
            textvariable=self.seconds,
            command=self.update_estimate
        ).pack(side="left", padx=8)

        ttk.Button(
            row, text="Calcular",
            command=self.update_estimate
        ).pack(side="left", padx=8)

        self.estimate_label = ttk.Label(
            main, text="Partes estimadas: --"
        )
        self.estimate_label.pack(anchor="w", pady=5)

        ttk.Separator(main).pack(fill="x", pady=12)

        # Progreso
        self.progress = ttk.Progressbar(
            main, maximum=100, mode="determinate"
        )
        self.progress.pack(fill="x", pady=5)

        self.status = ttk.Label(
            main, text="Listo para dividir videos",
            foreground="gray"
        )
        self.status.pack(pady=5)

        # Botones
        row = ttk.Frame(main)
        row.pack(fill="x", pady=12)

        self.button = ttk.Button(
            row, text="DIVIDIR VIDEO",
            command=self.start
        )
        self.button.pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=9)

        self.stop_button = ttk.Button(
            row, text="DETENER",
            command=self.stop, state="disabled"
        )
        self.stop_button.pack(side="left", fill="x", expand=True, padx=(5, 0), ipady=9)

        ttk.Label(
            main, text="Formato de salida: MP4",
            foreground="gray"
        ).pack()

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def select_video(self):
        path = filedialog.askopenfilename(
            title="Seleccionar video",
            filetypes=[
                ("Videos", "*.mp4 *.mkv *.avi *.mov *.webm *.m4v"),
                ("Todos los archivos", "*.*")
            ]
        )

        if not path:
            return

        self.video = path
        self.video_label.config(
            text=os.path.basename(path), foreground="black"
        )
        self.preview.config(text="Cargando vista previa...", image="")
        self.preview_image = None
        self.duration_label.config(text="Calculando duración...")
        self.estimate_label.config(text="Partes estimadas: calculando...")

        threading.Thread(
            target=self.load_video_info,
            args=(path,),
            daemon=True
        ).start()

    def load_video_info(self, path):
        try:
            result = subprocess.run(
                [
                    bundled_tool("ffprobe"), "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    path
                ],
                capture_output=True, text=True, check=True
            )

            duration = float(result.stdout.strip())

            thumbnail = os.path.join(
                tempfile.gettempdir(), "video_splitter_preview.png"
            )

            subprocess.run(
                [
                    bundled_tool("ffmpeg"), "-hide_banner", "-loglevel", "error",
                    "-y", "-ss", str(min(2, duration / 2)),
                    "-i", path, "-frames:v", "1",
                    "-vf", "scale=360:200:force_original_aspect_ratio=decrease",
                    thumbnail
                ],
                capture_output=True, timeout=30
            )

            self.root.after(
                0, self.show_video_info, path, duration, thumbnail
            )

        except Exception as error:
            self.root.after(
                0, self.video_info_error, str(error)
            )

    def show_video_info(self, path, duration, thumbnail):
        if path != self.video:
            return

        self.duration = duration
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)

        self.duration_label.config(
            text=f"Duración: {hours:02}:{minutes:02}:{seconds:02}"
        )

        try:
            if os.path.exists(thumbnail):
                self.preview_image = tk.PhotoImage(file=thumbnail)
                self.preview.config(
                    image=self.preview_image, text=""
                )
        except tk.TclError:
            self.preview.config(text="Vista previa no disponible")

        self.update_estimate()

    def video_info_error(self, error):
        self.preview.config(text="No se pudo cargar la vista previa")
        self.duration_label.config(text="No se pudo leer la duración")
        messagebox.showerror("Error", error)

    def select_folder(self):
        path = filedialog.askdirectory(
            title="Seleccionar carpeta de destino"
        )

        if path:
            self.folder = path
            self.folder_label.config(text=path, foreground="black")

    def get_part_duration(self):
        return int(self.minutes.get()) * 60 + int(self.seconds.get())

    def update_estimate(self):
        if not self.duration:
            return

        try:
            part_duration = self.get_part_duration()
            if part_duration <= 0:
                self.estimate_label.config(text="Duración no válida")
                return

            parts = math.ceil(self.duration / part_duration)
            self.estimate_label.config(
                text=f"Partes estimadas: {parts}"
            )
        except ValueError:
            self.estimate_label.config(text="Introduce una duración válida")

    def start(self):
        if self.running:
            return

        if not self.video or not os.path.isfile(self.video):
            messagebox.showwarning("Atención", "Selecciona un video.")
            return

        if not self.folder or not os.path.isdir(self.folder):
            messagebox.showwarning("Atención", "Selecciona una carpeta.")
            return

        name = re.sub(
            r'[\\/:*?"<>|]', "_", self.name.get().strip()
        ).strip(" .")

        if not name:
            messagebox.showwarning("Atención", "Escribe un nombre.")
            return

        try:
            part_duration = self.get_part_duration()
        except ValueError:
            part_duration = 0

        if part_duration <= 0:
            messagebox.showwarning(
                "Atención", "La duración debe ser mayor que cero."
            )
            return

        if not self.duration:
            messagebox.showwarning(
                "Atención", "Espera a que termine de cargar el video."
            )
            return

        parts = math.ceil(self.duration / part_duration)

        if not messagebox.askyesno(
            "Confirmar división",
            f"Se generarán aproximadamente {parts} partes.\n\n"
            f"Duración de cada parte: {part_duration} segundos.\n\n"
            "¿Deseas continuar?"
        ):
            return

        self.running = True
        self.cancel_event.clear()
        self.button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress["value"] = 0
        self.status.config(text="Preparando video...")

        threading.Thread(
            target=self.process,
            args=(name, part_duration),
            daemon=True
        ).start()

    def process(self, name, part_duration):
        try:
            output = os.path.join(
                self.folder, f"{name} - Parte %03d.mp4"
            )

            command = [
                bundled_tool("ffmpeg"), "-hide_banner", "-y",
                "-i", self.video,
                "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
                "-force_key_frames",
                f"expr:gte(t,n_forced*{part_duration})",
                "-sc_threshold", "0",
                "-c:a", "aac", "-b:a", "192k",
                "-f", "segment",
                "-segment_time", str(part_duration),
                "-segment_time_delta", "0.05",
                "-reset_timestamps", "1",
                "-segment_format", "mp4",
                "-progress", "pipe:1",
                "-nostats", output
            ]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )

            self.process_handle = process

            for line in process.stdout:
                if self.cancel_event.is_set():
                    break

                if line.startswith("out_time_us="):
                    try:
                        elapsed = int(line.split("=")[1]) / 1_000_000
                        percent = min(
                            100, elapsed / self.duration * 100
                        )
                        self.root.after(
                            0, self.update_progress, percent
                        )
                    except ValueError:
                        pass

            result = process.wait()
            self.process_handle = None

            if self.cancel_event.is_set():
                self.root.after(0, self.cancelled)
            elif result != 0:
                raise RuntimeError(
                    "FFmpeg no pudo procesar el video. "
                    "Comprueba el archivo y el espacio disponible."
                )
            else:
                self.root.after(0, self.finished)

        except Exception as error:
            self.process_handle = None
            self.root.after(0, self.failed, str(error))

    def update_progress(self, value):
        self.progress["value"] = value
        self.status.config(
            text=f"Procesando video: {value:.1f}%"
        )

    def stop(self):
        if not self.running:
            return

        self.cancel_event.set()
        self.stop_button.config(state="disabled")
        self.status.config(text="Deteniendo procesamiento...")

        if self.process_handle:
            try:
                self.process_handle.terminate()
            except OSError:
                pass

    def reset_buttons(self):
        self.running = False
        self.process_handle = None
        self.button.config(state="normal")
        self.stop_button.config(state="disabled")

    def finished(self):
        self.reset_buttons()
        self.progress["value"] = 100
        self.status.config(text="¡División completada!")

        messagebox.showinfo(
            "Terminado",
            f"El video se ha dividido correctamente.\n\n"
            f"Carpeta:\n{self.folder}"
        )

        if os.name == "nt":
            os.startfile(self.folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self.folder])
        else:
            subprocess.Popen(["xdg-open", self.folder])

    def cancelled(self):
        self.reset_buttons()
        self.status.config(text="Procesamiento detenido")
        messagebox.showinfo(
            "Detenido",
            "El procesamiento se ha detenido.\n"
            "Los fragmentos ya generados permanecen en la carpeta."
        )

    def failed(self, error):
        self.reset_buttons()
        self.status.config(text="Ocurrió un error.")
        messagebox.showerror("Error", error)

    def close(self):
        if self.running:
            if not messagebox.askyesno(
                "Salir", "Hay un video procesándose. ¿Deseas detenerlo y salir?"
            ):
                return

            self.cancel_event.set()
            if self.process_handle:
                try:
                    self.process_handle.terminate()
                except OSError:
                    pass

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoSplitter(root)
    root.mainloop()
