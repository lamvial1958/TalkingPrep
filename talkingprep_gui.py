#!/usr/bin/env python3
"""Janela local simples (tkinter) para o TalkingPrep.

Ponto de entrada amigável para quem prefere não usar o terminal: escolha os
arquivos, clique em "Processar" e veja o resultado na própria janela ao final.
Roda o mesmo pipeline da CLI (talkingprep.py) por baixo -- nenhum servidor,
nenhum processo continua rodando depois que a janela é fechada.

Uso: python talkingprep_gui.py  (ou dê dois cliques no atalho do desktop)
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from talkingprep.cli import _slugify, process_track  # noqa: E402
from talkingprep.audio_processing import check_ffmpeg_available  # noqa: E402
from talkingprep.cli import load_wav_metadata_seconds  # noqa: E402
from talkingprep.duet_report import build_duet_report, check_duration_match  # noqa: E402
from talkingprep.errors import TalkingPrepError  # noqa: E402


class QueueWriter:
    """Redireciona print() do pipeline para a fila lida pela janela."""

    def __init__(self, q: "queue.Queue"):
        self._q = q

    def write(self, text: str) -> None:
        if text.strip():
            self._q.put(("log", text.strip()))

    def flush(self) -> None:
        pass


@dataclass
class JobOutcome:
    ok: bool
    summary_lines: list[str]
    output_dir: Path | None
    report_paths: list[Path]
    error_message: str | None = None


class TalkingPrepApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TalkingPrep")
        self.root.geometry("760x640")
        self.root.minsize(680, 560)

        self._queue: "queue.Queue" = queue.Queue()
        self._worker: threading.Thread | None = None
        self._last_outcome: JobOutcome | None = None

        self._build_widgets()
        self.root.after(100, self._poll_queue)

    # -- construção da interface -------------------------------------------------

    def _build_widgets(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="x", padx=10, pady=(10, 0))

        self.single_tab = ttk.Frame(notebook)
        self.duet_tab = ttk.Frame(notebook)
        notebook.add(self.single_tab, text="Faixa única")
        notebook.add(self.duet_tab, text="Modo Dueto")
        self.notebook = notebook

        self._build_single_tab(self.single_tab)
        self._build_duet_tab(self.duet_tab)

        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill="x", padx=10, pady=8)

        self.process_btn = ttk.Button(
            action_frame, text="Processar", command=self._on_process_clicked
        )
        self.process_btn.pack(side="left")

        self.progress = ttk.Progressbar(action_frame, mode="indeterminate")
        self.progress.pack(side="left", fill="x", expand=True, padx=10)

        log_frame = ttk.LabelFrame(self.root, text="Acompanhamento")
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

        result_frame = ttk.LabelFrame(self.root, text="Resultado")
        result_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.result_text = scrolledtext.ScrolledText(result_frame, height=10, state="disabled", wrap="word")
        self.result_text.pack(fill="both", expand=True, padx=6, pady=(6, 4))

        result_buttons = ttk.Frame(result_frame)
        result_buttons.pack(fill="x", padx=6, pady=(0, 6))
        self.open_folder_btn = ttk.Button(
            result_buttons, text="Abrir pasta de saída", command=self._open_output_folder, state="disabled"
        )
        self.open_folder_btn.pack(side="left")
        self.open_report_btn = ttk.Button(
            result_buttons, text="Abrir ficha técnica", command=self._open_report, state="disabled"
        )
        self.open_report_btn.pack(side="left", padx=(8, 0))

    def _build_single_tab(self, parent: ttk.Frame) -> None:
        self.audio_path_var = tk.StringVar()
        self.lyrics_path_var = tk.StringVar()
        self.title_var = tk.StringVar()

        self._add_file_row(parent, "Áudio (.wav):", self.audio_path_var, self._browse_audio, row=0)
        self._add_file_row(
            parent, "Letra (.txt/.md, opcional):", self.lyrics_path_var, self._browse_lyrics, row=1
        )
        self._add_text_row(parent, "Título (opcional):", self.title_var, row=2)

    def _build_duet_tab(self, parent: ttk.Frame) -> None:
        self.audio_a_var = tk.StringVar()
        self.lyrics_a_var = tk.StringVar()
        self.audio_b_var = tk.StringVar()
        self.lyrics_b_var = tk.StringVar()
        self.duet_title_var = tk.StringVar()

        ttk.Label(parent, text="Cantor A", font=("", 9, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 0)
        )
        self._add_file_row(parent, "Áudio A (.wav):", self.audio_a_var, self._browse_audio_a, row=1)
        self._add_file_row(parent, "Letra A (opcional):", self.lyrics_a_var, self._browse_lyrics_a, row=2)

        ttk.Separator(parent, orient="horizontal").grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=6
        )

        ttk.Label(parent, text="Cantor B", font=("", 9, "bold")).grid(
            row=4, column=0, columnspan=3, sticky="w", padx=8
        )
        self._add_file_row(parent, "Áudio B (.wav):", self.audio_b_var, self._browse_audio_b, row=5)
        self._add_file_row(parent, "Letra B (opcional):", self.lyrics_b_var, self._browse_lyrics_b, row=6)

        self._add_text_row(parent, "Nome do dueto (opcional):", self.duet_title_var, row=7)

    def _add_file_row(self, parent, label, var, command, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        entry = ttk.Entry(parent, textvariable=var, width=55)
        entry.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(parent, text="Escolher...", command=command).grid(row=row, column=2, padx=8, pady=4)
        parent.columnconfigure(1, weight=1)

    def _add_text_row(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(parent, textvariable=var, width=55).grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=4, pady=4
        )

    # -- seleção de arquivos -------------------------------------------------

    def _browse_audio(self) -> None:
        path = filedialog.askopenfilename(title="Escolha o arquivo de áudio (.wav)", filetypes=[("WAV", "*.wav")])
        if path:
            self.audio_path_var.set(path)

    def _browse_lyrics(self) -> None:
        path = filedialog.askopenfilename(
            title="Escolha o arquivo de letra", filetypes=[("Texto", "*.txt *.md"), ("Todos", "*.*")]
        )
        if path:
            self.lyrics_path_var.set(path)

    def _browse_audio_a(self) -> None:
        path = filedialog.askopenfilename(title="Escolha o áudio do Cantor A (.wav)", filetypes=[("WAV", "*.wav")])
        if path:
            self.audio_a_var.set(path)

    def _browse_lyrics_a(self) -> None:
        path = filedialog.askopenfilename(
            title="Escolha a letra do Cantor A", filetypes=[("Texto", "*.txt *.md"), ("Todos", "*.*")]
        )
        if path:
            self.lyrics_a_var.set(path)

    def _browse_audio_b(self) -> None:
        path = filedialog.askopenfilename(title="Escolha o áudio do Cantor B (.wav)", filetypes=[("WAV", "*.wav")])
        if path:
            self.audio_b_var.set(path)

    def _browse_lyrics_b(self) -> None:
        path = filedialog.askopenfilename(
            title="Escolha a letra do Cantor B", filetypes=[("Texto", "*.txt *.md"), ("Todos", "*.*")]
        )
        if path:
            self.lyrics_b_var.set(path)

    # -- processamento ---------------------------------------------------------

    def _on_process_clicked(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return

        is_duet = self.notebook.index(self.notebook.select()) == 1

        if is_duet:
            if not self.audio_a_var.get() or not self.audio_b_var.get():
                messagebox.showerror(
                    "Campos obrigatórios",
                    "No Modo Dueto, escolha o áudio do Cantor A e o áudio do Cantor B antes de processar.",
                )
                return
        else:
            if not self.audio_path_var.get():
                messagebox.showerror("Campo obrigatório", "Escolha o arquivo de áudio (.wav) antes de processar.")
                return

        self._clear_log()
        self._clear_result()
        self.process_btn.configure(state="disabled")
        self.progress.start(12)

        self._worker = threading.Thread(target=self._run_job, args=(is_duet,), daemon=True)
        self._worker.start()

    def _run_job(self, is_duet: bool) -> None:
        old_stdout = sys.stdout
        sys.stdout = QueueWriter(self._queue)
        try:
            if is_duet:
                outcome = self._process_duet()
            else:
                outcome = self._process_single()
        except TalkingPrepError as exc:
            outcome = JobOutcome(ok=False, summary_lines=[], output_dir=None, report_paths=[], error_message=str(exc))
        except OSError as exc:
            outcome = JobOutcome(
                ok=False,
                summary_lines=[],
                output_dir=None,
                report_paths=[],
                error_message=f"Erro ao escrever arquivos de saída (verifique espaço em disco): {exc}",
            )
        except Exception as exc:  # segurança: nunca travar a janela silenciosamente
            outcome = JobOutcome(
                ok=False, summary_lines=[], output_dir=None, report_paths=[], error_message=f"Erro inesperado: {exc}"
            )
        finally:
            sys.stdout = old_stdout

        self._queue.put(("done", outcome))

    def _process_single(self) -> JobOutcome:
        check_ffmpeg_available()
        audio_path = Path(self.audio_path_var.get())
        lyrics_path = Path(self.lyrics_path_var.get()) if self.lyrics_path_var.get() else None
        title = self.title_var.get().strip() or audio_path.stem

        slug = _slugify(title) or "faixa"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = PROJECT_ROOT / "output" / f"{slug}_{timestamp}"

        result = process_track(
            audio_path=audio_path,
            lyrics_path=lyrics_path,
            title=title,
            output_dir=output_dir,
            silence_threshold=-40.0,
            slug=slug,
        )

        summary = [
            f"Faixa: {result.title}",
            f"Duração: {result.metadata_duration_sec:.2f}s ({result.metadata_duration_sec / 60:.2f} min)",
        ]
        if result.duration_warning:
            summary.append(f"Aviso: {result.duration_warning}")
        if result.short_duration_warning:
            summary.append(f"Aviso: {result.short_duration_warning}")
        if result.lyrics_skipped:
            summary.append("Aviso: sugestão de prompt de avatar gerada sem base na letra.")
        summary.append(f"Pasta de saída: {result.output_dir}")

        report_path = output_dir / f"{slug}_ficha_tecnica.txt"
        return JobOutcome(ok=True, summary_lines=summary, output_dir=output_dir, report_paths=[report_path])

    def _process_duet(self) -> JobOutcome:
        check_ffmpeg_available()
        audio_a_path = Path(self.audio_a_var.get())
        audio_b_path = Path(self.audio_b_var.get())
        lyrics_a_path = Path(self.lyrics_a_var.get()) if self.lyrics_a_var.get() else None
        lyrics_b_path = Path(self.lyrics_b_var.get()) if self.lyrics_b_var.get() else None
        title = self.duet_title_var.get().strip() or "dueto"

        slug = _slugify(title) or "dueto"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parent_dir = PROJECT_ROOT / "output" / f"{slug}_dueto_{timestamp}"
        dir_a = parent_dir / "faixa_a"
        dir_b = parent_dir / "faixa_b"

        duet_note = (
            "Esta faixa faz parte de um Modo Dueto. Veja o arquivo 'ficha_dueto.txt' "
            "na pasta pai para as instruções de montagem do vídeo final."
        )

        result_a = process_track(
            audio_path=audio_a_path,
            lyrics_path=lyrics_a_path,
            title=f"{title} -- Cantor A",
            output_dir=dir_a,
            silence_threshold=-40.0,
            slug=f"{slug}_a",
            log_prefix="  [A] ",
            duet_note=duet_note,
        )
        result_b = process_track(
            audio_path=audio_b_path,
            lyrics_path=lyrics_b_path,
            title=f"{title} -- Cantor B",
            output_dir=dir_b,
            silence_threshold=-40.0,
            slug=f"{slug}_b",
            log_prefix="  [B] ",
            duet_note=duet_note,
        )

        duration_check = check_duration_match(
            duration_a_sec=load_wav_metadata_seconds(result_a.final_vocal_path),
            duration_b_sec=load_wav_metadata_seconds(result_b.final_vocal_path),
        )
        duet_report_text = build_duet_report(
            title=title,
            vocal_filename_a=result_a.final_vocal_path.name,
            vocal_filename_b=result_b.final_vocal_path.name,
            duration_check=duration_check,
        )
        duet_report_path = parent_dir / "ficha_dueto.txt"
        duet_report_path.write_text(duet_report_text, encoding="utf-8")

        summary = [
            f"Dueto: {title}",
            f"Duração Faixa A: {duration_check.duration_a_sec:.2f}s",
            f"Duração Faixa B: {duration_check.duration_b_sec:.2f}s",
        ]
        if duration_check.mismatched:
            summary.append(
                f"AVISO: divergência de duração de {duration_check.diff_sec:.2f}s entre as faixas -- "
                "veja ficha_dueto.txt."
            )
        summary.append(f"Pasta de saída: {parent_dir}")

        report_paths = [
            duet_report_path,
            dir_a / f"{slug}_a_ficha_tecnica.txt",
            dir_b / f"{slug}_b_ficha_tecnica.txt",
        ]
        return JobOutcome(ok=True, summary_lines=summary, output_dir=parent_dir, report_paths=report_paths)

    # -- fila / UI ---------------------------------------------------------------

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "done":
                    self._on_job_done(payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _on_job_done(self, outcome: JobOutcome) -> None:
        self.progress.stop()
        self.process_btn.configure(state="normal")
        self._last_outcome = outcome

        if not outcome.ok:
            messagebox.showerror("Erro ao processar", outcome.error_message or "Erro desconhecido.")
            self._append_log(f"ERRO: {outcome.error_message}")
            return

        self._append_log("Concluído.")
        self._set_result("\n".join(outcome.summary_lines))
        if outcome.output_dir is not None:
            self.open_folder_btn.configure(state="normal")
        if outcome.report_paths:
            self.open_report_btn.configure(state="normal")

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _set_result(self, text: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", text)
        self.result_text.configure(state="disabled")

    def _clear_result(self) -> None:
        self._set_result("")
        self.open_folder_btn.configure(state="disabled")
        self.open_report_btn.configure(state="disabled")

    def _open_output_folder(self) -> None:
        if self._last_outcome and self._last_outcome.output_dir:
            os.startfile(str(self._last_outcome.output_dir))  # Windows

    def _open_report(self) -> None:
        if self._last_outcome and self._last_outcome.report_paths:
            os.startfile(str(self._last_outcome.report_paths[0]))  # Windows


def main() -> None:
    root = tk.Tk()
    TalkingPrepApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
