"""Colored logging and timing utilities for notso-glb."""

import io
import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass


# ANSI color codes
class Colors:
    """ANSI escape codes for terminal colors."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright variants
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


def _supports_color() -> bool:
    """Check if terminal supports color output."""
    if not hasattr(sys.stdout, "isatty"):
        return False
    if not sys.stdout.isatty():
        return False
    return True


_USE_COLOR = _supports_color()


def _c(color: str, text: str) -> str:
    """Apply color to text if supported."""
    if not _USE_COLOR:
        return text
    return f"{color}{text}{Colors.RESET}"


def bold(text: str) -> str:
    """Make text bold."""
    return _c(Colors.BOLD, text)


def dim(text: str) -> str:
    """Make text dim."""
    return _c(Colors.DIM, text)


def red(text: str) -> str:
    """Color text red."""
    return _c(Colors.RED, text)


def green(text: str) -> str:
    """Color text green."""
    return _c(Colors.GREEN, text)


def yellow(text: str) -> str:
    """Color text yellow."""
    return _c(Colors.YELLOW, text)


def blue(text: str) -> str:
    """Color text blue."""
    return _c(Colors.BLUE, text)


def cyan(text: str) -> str:
    """Color text cyan."""
    return _c(Colors.CYAN, text)


def magenta(text: str) -> str:
    """Color text magenta."""
    return _c(Colors.MAGENTA, text)


def bright_green(text: str) -> str:
    """Color text bright green."""
    return _c(Colors.BRIGHT_GREEN, text)


def bright_yellow(text: str) -> str:
    """Color text bright yellow."""
    return _c(Colors.BRIGHT_YELLOW, text)


def bright_red(text: str) -> str:
    """Color text bright red."""
    return _c(Colors.BRIGHT_RED, text)


def bright_cyan(text: str) -> str:
    """Color text bright cyan."""
    return _c(Colors.BRIGHT_CYAN, text)


# Log level formatting
def log_info(msg: str) -> None:
    """Print info message."""
    print(f"  {cyan('INFO')}  {msg}")


def log_ok(msg: str) -> None:
    """Print success message."""
    print(f"    {bright_green('OK')}  {msg}")


def log_warn(msg: str) -> None:
    """Print warning message."""
    print(f"  {bright_yellow('WARN')}  {msg}")


def log_error(msg: str) -> None:
    """Print error message."""
    print(f" {bright_red('ERROR')}  {msg}")


def log_debug(msg: str) -> None:
    """Print debug message (dimmed)."""
    print(f" {dim('DEBUG')}  {dim(msg)}")


def log_step(current: int, total: int, msg: str) -> None:
    """Print step progress message."""
    step_str = f"[{current}/{total}]"
    print(f"\n{cyan(step_str)} {msg}")


def log_detail(msg: str, indent: int = 6) -> None:
    """Print indented detail message."""
    print(f"{' ' * indent}{msg}")


def log_timing(msg: str, seconds: float) -> None:
    """Print timing message with formatted duration."""
    time_str = format_duration(seconds)
    print(f"  {dim('TIME')}  {msg}: {bright_cyan(time_str)}")


# Separators and headers
def print_header(title: str, char: str = "=", width: int = 60) -> None:
    """Print a header with decorative borders."""
    border = char * width
    print(f"\n{cyan(border)}")
    print(f"  {bold(title)}")
    print(f"{cyan(border)}")


def print_section(title: str, char: str = "-", width: int = 60) -> None:
    """Print a section header."""
    border = char * width
    print(f"\n{dim(border)}")
    print(f"  {title}")
    print(f"{dim(border)}")


def print_warning_box(
    title: str, warnings: list[str], severity: str = "WARNING"
) -> None:
    """Print a warning box with colored border."""
    border_char = "!" if severity == "CRITICAL" else "~"
    color_fn = bright_red if severity == "CRITICAL" else bright_yellow
    border = border_char * 60

    print(f"\n{color_fn(border)}")
    print(f"  {color_fn(title)}")
    print(f"{color_fn(border)}")
    for w in warnings:
        print(f"  {w}")
    print(f"{color_fn(border)}")


# Timing utilities
def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.0f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.1f}s"


@dataclass
class TimingResult:
    """Result from a timed operation."""

    elapsed: float
    message: str


@contextmanager
def timed(description: str, print_on_exit: bool = True) -> Iterator[TimingResult]:
    """Context manager for timing operations.

    Usage:
        with timed("Processing meshes") as t:
            do_work()
        # Automatically prints timing on exit

        # Or capture without printing:
        with timed("Processing", print_on_exit=False) as t:
            do_work()
        print(f"Took {t.elapsed}s")
    """
    result = TimingResult(elapsed=0.0, message=description)
    start = time.perf_counter()
    try:
        yield result
    finally:
        result.elapsed = time.perf_counter() - start
        if print_on_exit:
            log_timing(description, result.elapsed)


class StepTimer:
    """Track timing for multiple steps in a pipeline."""

    def __init__(self, total_steps: int) -> None:
        self.total = total_steps
        self.current = 0
        self.timings: list[tuple[str, float]] = []
        self._step_start: float = 0.0
        self._total_start: float = time.perf_counter()

    def step(self, message: str) -> None:
        """Start a new step, recording timing for previous step."""
        now = time.perf_counter()

        # Record previous step timing
        if self.current > 0 and self._step_start > 0:
            elapsed = now - self._step_start
            if self.timings:
                prev_name = self.timings[-1][0]
                self.timings[-1] = (prev_name, elapsed)

        self.current += 1
        self._step_start = now
        self.timings.append((message, 0.0))
        log_step(self.current, self.total, message)

    def finish(self) -> None:
        """Finish timing and record final step."""
        now = time.perf_counter()
        if self._step_start > 0 and self.timings:
            elapsed = now - self._step_start
            prev_name = self.timings[-1][0]
            self.timings[-1] = (prev_name, elapsed)

    def total_elapsed(self) -> float:
        """Get total elapsed time since timer started."""
        return time.perf_counter() - self._total_start

    def print_summary(self) -> None:
        """Print timing summary for all steps."""
        print_section("Timing Summary", char="-", width=50)
        for name, elapsed in self.timings:
            time_str = format_duration(elapsed)
            # Right-align timing
            padding = 40 - len(name)
            print(f"  {name}{' ' * max(1, padding)}{bright_cyan(time_str)}")
        print(f"{dim('-' * 50)}")
        total = self.total_elapsed()
        print(f"  {bold('Total')}{' ' * 33}{bright_green(format_duration(total))}")


# Result formatting
def format_count(count: int, singular: str, plural: str | None = None) -> str:
    """Format count with proper singular/plural form."""
    if plural is None:
        plural = singular + "s"
    word = singular if count == 1 else plural
    return f"{count:,} {word}"


def format_bytes(size: int) -> str:
    """Format byte size in human-readable form."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / 1024 / 1024:.2f} MB"
    else:
        return f"{size / 1024 / 1024 / 1024:.2f} GB"


def format_delta(before: int, after: int, unit: str = "") -> str:
    """Format a before/after change with color."""
    diff = after - before
    if diff == 0:
        return dim("no change")
    elif diff < 0:
        return bright_green(f"-{abs(diff):,}{unit}")
    else:
        return bright_red(f"+{diff:,}{unit}")


@contextmanager
def filter_blender_output() -> Iterator[None]:
    """Filter Blender output: suppress INFO, pass through WARNING/ERROR.

    Captures stdout during Blender operations and:
    - Suppresses INFO and DracoDecoder lines
    - Reformats and displays WARNING/ERROR lines with our colors

    Output is post-processed after the operation completes.
    """
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer
    try:
        yield
    finally:
        sys.stdout = old_stdout
        # Process captured output
        for line in buffer.getvalue().splitlines():
            if "| WARNING:" in line:
                # Extract message after "WARNING: "
                msg = line.split("| WARNING:", 1)[-1].strip()
                log_warn(f"[Blender] {msg}")
            elif "| ERROR:" in line:
                msg = line.split("| ERROR:", 1)[-1].strip()
                log_error(f"[Blender] {msg}")
            # Discard INFO and DracoDecoder lines


@contextmanager
def suppress_stdout() -> Iterator[None]:
    """Completely suppress stdout (redirect to /dev/null)."""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
