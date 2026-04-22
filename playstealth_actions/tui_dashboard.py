"""Interactive TUI Dashboard Module.

Nutzt `rich.live` für ein echtes Terminal-Dashboard. Vollständig entkoppelt:
Liest live aus telemetry.jsonl (tail-Modus) oder aus einer async Queue.
Kein Blocking, kein komplexer Event-Loop-Konflikt.
"""
import asyncio
import json
import time
import os
from pathlib import Path
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.table import Table
from rich.console import Console
from rich.text import Text
from datetime import datetime

# Telemetry-Dateipfad aus Environment oder Default
TELEMETRY_DIR = Path(os.getenv("PLAYSTEALTH_STATE_DIR", ".playstealth_state"))
TELEMETRY_FILE = TELEMETRY_DIR / "telemetry.jsonl"


class TUIDashboard:
    """Live-Dashboard für Survey-Fortschritt und Metriken."""
    
    def __init__(self, session_id: str = "live", max_steps: int = 10):
        self.console = Console()
        self.session_id = session_id
        self.max_steps = max_steps
        self.current_step = 0
        self.successes = 0
        self.traps = 0
        self.errors = 0
        self.logs: list[str] = []
        self.start_time = time.time()

    def _build_layout(self) -> Layout:
        """Erstellt das Dashboard-Layout mit Header, Metrics und Log."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3)
        )
        layout["body"].split_row(
            Layout(name="metrics", ratio=1),
            Layout(name="log", ratio=2)
        )
        return layout

    def _update_metrics(self, layout: Layout):
        """Aktualisiert die Metriken-Anzeige."""
        elapsed = time.time() - self.start_time
        rate = (self.successes / self.current_step * 100) if self.current_step > 0 else 0.0
        
        # Fortschrittsanzeige
        prog = Progress(
            TextColumn("[bold blue]Step {task.completed}/{task.total}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            expand=True
        )
        prog.add_task("survey", total=self.max_steps, completed=self.current_step)

        # Statistik-Tabelle
        stats = Table.grid(padding=1)
        stats.add_column()
        stats.add_column()
        stats.add_row("Session:", f"[cyan]{self.session_id}[/]")
        stats.add_row("Uptime:", f"{elapsed:.0f}s")
        
        success_style = "green" if rate >= 70 else "yellow" if rate >= 40 else "red"
        stats.add_row("Success:", f"[{success_style}]{rate:.0f}%[/]")
        stats.add_row("Traps:", f"[bold yellow]{self.traps}[/]")
        stats.add_row("Errors:", f"[bold red]{self.errors}[/]")

        layout["header"].update(Panel(stats, title="📊 PlayStealth Live", border_style="cyan"))
        layout["metrics"].update(Panel(prog, title="📈 Progress", border_style="blue"))

    def _update_log(self, layout: Layout):
        """Aktualisiert das Event-Log."""
        log_text = Text("\n".join(self.logs[-15:]), style="dim")
        layout["log"].update(Panel(log_text, title="📜 Event Log", border_style="green"))

    def _update_footer(self, layout: Layout):
        """Aktualisiert die Footer-Leiste."""
        layout["footer"].update(Panel(
            "[bold]q[/] quit | [bold]r[/] reset view | Auto-refresh: 4Hz",
            style="dim", border_style="white"
        ))

    def push_event(self, evt: dict):
        """Verarbeitet ein Telemetry-Event und aktualisiert den Status."""
        ts = datetime.now().strftime("%H:%M:%S")
        evt_type = evt.get("evt", evt.get("type", "?"))
        
        if evt_type == "step_start":
            self.current_step = evt.get("step", self.current_step)
            self.logs.append(f"[{ts}] [blue]▶ Step {self.current_step}[/]")
        
        elif evt_type == "step_end":
            if evt.get("ok"):
                self.successes += 1
            dur = evt.get("dur_ms", 0)
            icon = "✓" if evt.get("ok") else "✗"
            color = "green" if evt.get("ok") else "red"
            self.logs.append(f"[{ts}] [{color}]{icon} Step {self.current_step} ({dur:.0f}ms)[/]")
        
        elif "trap" in evt_type or evt.get("trap"):
            self.traps += 1
            trap_type = evt.get("trap", evt.get("trap_type", "unknown"))
            self.logs.append(f"[{ts}] [bold yellow]⚠ Trap: {trap_type}[/]")
        
        elif evt.get("err"):
            self.errors += 1
            self.logs.append(f"[{ts}] [bold red]❌ {evt.get('err')}[/]")

    def run_live(self):
        """Startet die Live-Anzeige (blockierend, sollte in Thread laufen)."""
        layout = self._build_layout()
        with Live(layout, console=self.console, refresh_per_second=4, screen=True) as live:
            try:
                while True:
                    self._update_metrics(layout)
                    self._update_log(layout)
                    self._update_footer(layout)
                    time.sleep(0.25)
            except KeyboardInterrupt:
                pass

    async def tail_telemetry(self):
        """Liest telemetry.jsonl in Echtzeit und pushed Events ins Dashboard."""
        # Warten bis Telemetry-Datei existiert
        if not TELEMETRY_FILE.exists():
            self.console.print(f"[yellow]⏳ Waiting for {TELEMETRY_FILE}...[/]")
            while not TELEMETRY_FILE.exists():
                await asyncio.sleep(0.5)
        
        # Datei im Tail-Modus lesen
        with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
            f.seek(0, 2)  # Zum Ende springen
            while True:
                line = f.readline()
                if line:
                    try:
                        evt = json.loads(line.strip())
                        self.push_event(evt)
                    except json.JSONDecodeError:
                        pass
                else:
                    await asyncio.sleep(0.2)


async def run_dashboard(session_id: str = "live", max_steps: int = 10):
    """Bequeme Funktion zum Starten des Dashboards."""
    dash = TUIDashboard(session_id=session_id, max_steps=max_steps)
    
    # Dashboard in separatem Thread laufen lassen, während Telemetry getailt wird
    import threading
    thread = threading.Thread(target=dash.run_live, daemon=True)
    thread.start()
    
    await dash.tail_telemetry()
